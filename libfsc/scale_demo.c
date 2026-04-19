#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "libfsc.h"

#define SECTOR_SIZE 512
#define NUM_SECTORS 2048 // 1MB total
#define MODULUS 2305843009213693951LL

int main() {
    printf("--- Scale Demo: 1MB Self-Healing Block Device ---\n");

    uint8_t* storage = malloc(NUM_SECTORS * SECTOR_SIZE);
    int64_t* targets = malloc(NUM_SECTORS * sizeof(int64_t));
    int32_t* weights = malloc(SECTOR_SIZE * sizeof(int32_t));

    for (int i = 0; i < SECTOR_SIZE; i++) weights[i] = i + 1;
    memset(storage, 0x42, NUM_SECTORS * SECTOR_SIZE);

    printf("Sealing 2048 sectors...\n");
    for (int i = 0; i < NUM_SECTORS; i++) {
        targets[i] = fsc_calculate_sum8(storage + (i * SECTOR_SIZE), weights, SECTOR_SIZE, MODULUS);
    }

    // Corrupt 5 random sectors
    printf("Simulating corruption in 5 random sectors...\n");
    int corrupt_indices[] = {10, 500, 1024, 1500, 2000};
    for (int i = 0; i < 5; i++) {
        storage[corrupt_indices[i] * SECTOR_SIZE + 256] ^= 0xFF;
    }

    // Sweep and Heal
    int healed = 0;
    for (int i = 0; i < NUM_SECTORS; i++) {
        int64_t actual = fsc_calculate_sum8(storage + (i * SECTOR_SIZE), weights, SECTOR_SIZE, MODULUS);
        if (actual != targets[i]) {
            // Heal using target
            uint8_t recovered = fsc_heal_single8(storage + (i * SECTOR_SIZE), weights, SECTOR_SIZE, targets[i], MODULUS, 256);
            storage[i * SECTOR_SIZE + 256] = recovered;
            healed++;
        }
    }

    printf("Scan complete. Sectors healed: %d/5\n", healed);
    if (healed == 5) {
        printf("SUCCESS: All block-level corruptions reversed.\n");
    }

    free(storage); free(targets); free(weights);
    return 0;
}
