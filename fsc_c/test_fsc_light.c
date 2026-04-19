#include <stdio.h>
#include <assert.h>
#include "fsc_light.h"

int main() {
    printf("Testing FSC Light...\n");

    // Test 1: Simple sum (no modulus)
    int64_t data1[] = {10, 20, 30};
    int8_t weights1[] = {1, 1, 1};
    int64_t target1 = fsc_calculate_sum(data1, weights1, 3, 0);
    assert(target1 == 60);

    // Corrupt data[1]
    data1[1] = 999;
    int64_t recovered1 = fsc_recover_field(data1, weights1, 3, target1, 0, 1);
    assert(recovered1 == 20);
    printf("Test 1 (Integer Sum) Passed\n");

    // Test 2: Modular Weighted Sum
    int64_t data2[] = {100, 200, 300};
    int8_t weights2[] = {1, 2, 3}; // 100 + 400 + 900 = 1400
    int64_t modulus = 251;
    // 1400 % 251: 1400 / 251 = 5, 251*5 = 1255, 1400 - 1255 = 145
    int64_t target2 = fsc_calculate_sum(data2, weights2, 3, modulus);
    assert(target2 == 145);

    // Corrupt data[2]
    data2[2] = 0;
    int64_t recovered2 = fsc_recover_field(data2, weights2, 3, target2, modulus, 2);
    assert(recovered2 == 300 % modulus); // Recovery is mod p
    printf("Test 2 (Modular Weighted Sum) Passed\n");

    // Test 3: Modular Inverse
    assert(fsc_mod_inverse(3, 7) == 5); // 3*5 = 15 = 1 mod 7
    assert(fsc_mod_inverse(10, 17) == 12); // 10*12 = 120 = 7*17 + 1 = 119 + 1
    printf("Test 3 (Modular Inverse) Passed\n");

    printf("All FSC Light internal tests passed!\n");
    return 0;
}
