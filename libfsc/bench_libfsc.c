#include <stdio.h>
#include <stdint.h>
#include <time.h>
#include <stdlib.h>
#include "libfsc.h"

#define PAGE_SIZE 4096
#define ITERS 100000

int main() {
    uint8_t* page = malloc(PAGE_SIZE);
    for (int i = 0; i < PAGE_SIZE; i++) page[i] = (uint8_t)(i % 256);

    int32_t* w1 = malloc(PAGE_SIZE * sizeof(int32_t));
    int32_t* w2 = malloc(PAGE_SIZE * sizeof(int32_t));
    for (int i = 0; i < PAGE_SIZE; i++) {
        w1[i] = 1;
        w2[i] = (int32_t)(i + 1);
    }

    FSCBuffer b = {page, PAGE_SIZE, 2305843009213693951LL, 0, w1, w2, 0};
    fsc_buffer_seal(&b);

    printf("Benchmarking libfsc on %d byte page (%d iterations) [WITH WEIGHTS]...\n", PAGE_SIZE, ITERS);

    clock_t start = clock();
    for (int i = 0; i < ITERS; i++) {
        fsc_buffer_verify(&b);
    }
    clock_t end = clock();
    double time_verify = (double)(end - start) / CLOCKS_PER_SEC;
    double throughput = (double)PAGE_SIZE * ITERS / time_verify / (1024 * 1024 * 1024);

    printf("Verification: %.3f GB/s\n", throughput);

    // Bench Healing Latency
    uint8_t orig = page[2048];
    page[2048] ^= 0x01;
    start = clock();
    int h_idx = fsc_buffer_heal(&b);
    end = clock();
    double time_heal = (double)(end - start) / CLOCKS_PER_SEC;
    printf("Healing Latency: %.3f microseconds (idx=%d)\n", time_heal * 1e6, h_idx);

    if (page[2048] == orig) {
        printf("Healing successful.\n");
    }

    free(page); free(w1); free(w2);
    return 0;
}
