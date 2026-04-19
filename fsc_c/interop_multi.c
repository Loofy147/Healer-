#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <arpa/inet.h>
#include "fsc_light.h"

int main() {
    FILE* f = fopen("interop_multi.fsc", "rb");
    if (!f) return 1;

    char magic[4]; fread(magic, 4, 1, f);
    uint8_t version; fread(&version, 1, 1, f);
    uint16_t n_data_be; fread(&n_data_be, 2, 1, f);
    uint16_t n_data = ntohs(n_data_be);
    uint8_t n_cons; fread(&n_cons, 1, 1, f);
    uint8_t n_stored; fread(&n_stored, 1, 1, f);
    uint32_t n_recs_be; fread(&n_recs_be, 4, 1, f);
    uint32_t n_recs = ntohl(n_recs_be);

    printf("Interop Header: DataFields %d, Constraints %d\n", n_data, n_cons);

    // Skip field definitions
    fseek(f, n_data * 17, SEEK_CUR);

    int64_t* targets = malloc(n_cons * sizeof(int64_t));
    int64_t* moduli = malloc(n_cons * sizeof(int64_t));
    int8_t* s_indices = malloc(n_cons);
    int8_t* all_weights = malloc(n_cons * n_data);

    for (int i = 0; i < n_cons; i++) {
        uint8_t ctype; fread(&ctype, 1, 1, f);
        int64_t target_be; fread(&target_be, 8, 1, f);
        fread(&s_indices[i], 1, 1, f);
        int64_t modulus_be; fread(&modulus_be, 8, 1, f);
        fread(&all_weights[i * n_data], n_data, 1, f);

        // Swap bytes
        int64_t t = 0; uint8_t* p = (uint8_t*)&target_be;
        for(int j=0; j<8; j++) t = (t << 8) | p[j];
        targets[i] = t;

        int64_t m = 0; p = (uint8_t*)&modulus_be;
        for(int j=0; j<8; j++) m = (m << 8) | p[j];
        moduli[i] = m;
    }

    // Read first record
    int64_t* record = malloc((n_data + n_stored) * 8);
    fread(record, (n_data + n_stored) * 8, 1, f);
    for(int i=0; i < (n_data + n_stored); i++) {
        int64_t val = 0; uint8_t* rp = (uint8_t*)&record[i];
        for(int j=0; j<8; j++) val = (val << 8) | rp[j];
        record[i] = val;
    }

    printf("Original Record: [%ld, %ld, %ld]\n", record[0], record[1], record[2]);

    // Update targets from stored invariants if s_idx != -1
    for (int i = 0; i < n_cons; i++) {
        if (s_indices[i] != -1) {
            targets[i] = record[s_indices[i]];
        }
    }

    // Corrupt 2 fields (k=2)
    printf("\n[CORRUPTION] Corrupting record[0] and record[1] (simultaneous)...\n");
    record[0] = 999;
    record[1] = 888;

    int corrupted_indices[] = {0, 1};
    int ok = fsc_recover_multi(record, all_weights, n_data, targets, moduli, n_cons, corrupted_indices);

    if (ok) {
        printf("Healed Record:   [%ld, %ld, %ld]\n", record[0], record[1], record[2]);
        if (record[0] == 10 && record[1] == 20) {
            printf("MULTI-FAULT INTEROP SUCCESS!\n");
        } else {
            printf("MULTI-FAULT INTEROP FAILED (Wrong values).\n");
        }
    } else {
        printf("MULTI-FAULT INTEROP FAILED (Solver failed).\n");
    }

    free(targets); free(moduli); free(s_indices); free(all_weights); free(record);
    fclose(f);
    return 0;
}
