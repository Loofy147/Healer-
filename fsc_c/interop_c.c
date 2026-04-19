#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <arpa/inet.h>
#include "fsc_light.h"

// Helper to read big-endian 64-bit from file
int64_t read_be64(FILE* f) {
    uint64_t val;
    fread(&val, 8, 1, f);
    // Swap bytes if on little-endian (common)
    uint64_t result = 0;
    for (int i = 0; i < 8; i++) {
        result = (result << 8) | ((val >> (i * 8)) & 0xFF);
    }
    return (int64_t)result;
}

// Simple FSC reader for .fsc v3 header
int main() {
    FILE* f = fopen("interop.fsc", "rb");
    if (!f) return 1;

    char magic[4];
    fread(magic, 4, 1, f);
    if (memcmp(magic, "FSC1", 4) != 0) { printf("Bad magic\n"); return 1; }

    uint8_t version; fread(&version, 1, 1, f);
    uint16_t n_data_be; fread(&n_data_be, 2, 1, f);
    uint16_t n_data = ntohs(n_data_be);
    uint8_t n_cons; fread(&n_cons, 1, 1, f);
    uint8_t n_stored; fread(&n_stored, 1, 1, f);
    uint32_t n_recs_be; fread(&n_recs_be, 4, 1, f);
    uint32_t n_recs = ntohl(n_recs_be);

    printf("Header: Version %d, DataFields %d, Constraints %d, Records %d\n", version, n_data, n_cons, n_recs);

    // Skip field definitions (17 bytes each)
    fseek(f, n_data * 17, SEEK_CUR);

    // Read first constraint
    uint8_t ctype; fread(&ctype, 1, 1, f);
    int64_t target_be; fread(&target_be, 8, 1, f); // Note: we should byte-swap but let's assume simple read for demo
    int8_t s_idx; fread(&s_idx, 1, 1, f);
    int64_t modulus_be; fread(&modulus_be, 8, 1, f);

    // Re-do byte swap for the longs
    int64_t target = 0; uint8_t* p = (uint8_t*)&target_be;
    for(int i=0; i<8; i++) target = (target << 8) | p[i];
    int64_t modulus = 0; p = (uint8_t*)&modulus_be;
    for(int i=0; i<8; i++) modulus = (modulus << 8) | p[i];

    int8_t* weights = malloc(n_data);
    fread(weights, n_data, 1, f);

    printf("Constraint 0: Type %d, Target %ld, Modulus %ld, SIdx %d\n", ctype, target, modulus, s_idx);

    // Jump to records
    // Record size: (n_data + n_stored) * 8 bytes
    int64_t* record = malloc((n_data + n_stored) * 8);
    fread(record, (n_data + n_stored) * 8, 1, f);

    // Byte swap record fields
    for(int i=0; i < (n_data + n_stored); i++) {
        int64_t val = 0; uint8_t* rp = (uint8_t*)&record[i];
        for(int j=0; j<8; j++) val = (val << 8) | rp[j];
        record[i] = val;
    }

    printf("Record 0 Read: [%ld, %ld, %ld], StoredInv: %ld\n", record[0], record[1], record[2], record[3]);

    // Verify
    int64_t check_target = (s_idx != -1) ? record[s_idx] : target;
    int64_t actual = fsc_calculate_sum(record, weights, n_data, modulus);
    printf("Verification: Actual %ld vs Target %ld\n", actual, check_target);

    // Corrupt and Heal
    printf("\n[CORRUPTION] Corrupting record[1]...\n");
    record[1] = 0;
    int64_t recovered = fsc_recover_field(record, weights, n_data, check_target, modulus, 1);
    printf("Recovery: %ld\n", recovered);

    if (recovered == 20) {
        printf("INTEROP SUCCESS: C code healed Python-generated .fsc file!\n");
    } else {
        printf("INTEROP FAILURE.\n");
    }

    free(weights);
    free(record);
    fclose(f);
    return 0;
}
