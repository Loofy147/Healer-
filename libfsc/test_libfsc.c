#include <stdio.h>
#include <assert.h>
#include <string.h>
#include "libfsc.h"

int main() {
    printf("Testing libfsc (Bare-metal reference)...\n");

    uint8_t mem[16] = "Hello FSC World";
    int32_t w1[15], w2[15];
    for(int i=0; i<15; i++) { w1[i] = 1; w2[i] = i+1; }

    FSCBuffer b = {mem, 15, 251, 0, w1, w2, 0};
    fsc_buffer_seal(&b);
    printf("Buffer Sealed. Targets: T1=%ld, T2=%ld\n", b.target, b.target2);

    // Corrupt 'W' (index 10)
    uint8_t original_val = mem[10];
    mem[10] = '?'; // 63
    printf("Corrupted buffer: %s\n", mem);
    assert(fsc_buffer_verify(&b) == 0);

    int healed_idx = fsc_buffer_heal(&b);
    printf("Healed index: %d. New Buffer: %s\n", healed_idx, mem);

    assert(healed_idx == 10);
    assert(mem[10] == original_val);
    assert(fsc_buffer_verify(&b) == 1);

    // Test 2: Multi-Fault (k=2)
    int64_t data[] = {10, 20, 30};
    int32_t weights[] = {1, 1, 1,  1, 2, 3};
    int64_t targets[] = {60, 140};
    int64_t moduli[] = {251, 251};
    size_t corrupted[] = {0, 1};

    data[0] = 999; data[1] = 888;
    int res = fsc_heal_multi64(data, weights, 3, targets, moduli, 2, corrupted);
    assert(res == FSC_SUCCESS);
    assert(data[0] == 10 && data[1] == 20);
    printf("Multi-fault 64-bit recovery Passed.\n");

    printf("All libfsc tests passed!\n");
    return 0;
}
