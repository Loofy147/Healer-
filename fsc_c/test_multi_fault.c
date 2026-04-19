#include <stdio.h>
#include <assert.h>
#include "fsc_light.h"

void test_recover_multi() {
    printf("Testing fsc_recover_multi...\n");
    int64_t p = 251;
    // 2 data fields, 2 constraints
    // C1: 1*x + 1*y = 5 mod 251
    // C2: 1*x + 2*y = 7 mod 251
    // data = [3, 2]
    int64_t data[] = {99, 88}; // corrupted
    int8_t weights[] = {1, 1, 1, 2};
    int64_t targets[] = {5, 7};
    int64_t moduli[] = {251, 251};
    int corrupted_indices[] = {0, 1};

    int ok = fsc_recover_multi(data, weights, 2, targets, moduli, 2, corrupted_indices);
    assert(ok == 1);
    printf("Recovered x=%ld, y=%ld\n", data[0], data[1]);
    assert(data[0] == 3);
    assert(data[1] == 2);
    printf("fsc_recover_multi Passed\n");
}

void test_fiber() {
    printf("Testing Fiber (Model 4) logic...\n");
    int64_t modulus = 251;
    int64_t pos = 1234;
    int64_t target = fsc_calculate_fiber_target(pos, modulus);
    // 1234 % 251: 1234 = 4 * 251 + 230
    assert(target == 230);

    int64_t data[] = {100, 130}; // sum = 230
    int8_t weights[] = {1, 1};
    int64_t actual = fsc_calculate_sum(data, weights, 2, modulus);
    assert(actual == target);

    // Corrupt
    data[0] = 0;
    int64_t recovered = fsc_recover_field(data, weights, 2, target, modulus, 0);
    assert(recovered == 100);
    printf("Fiber logic Passed\n");
}

int main() {
    printf("Testing Multi-Fault Solver...\n");

    int64_t p = 251;
    // System:
    // 1*x + 1*y = 5 mod 251
    // 1*x + 2*y = 7 mod 251
    // Solution should be x=3, y=2
    int64_t A[] = {1, 1, 1, 2};
    int64_t b[] = {5, 7};
    int64_t results[2];

    int ok = fsc_solve_linear_system(A, b, 2, p, results);
    assert(ok == 1);
    printf("Solved x=%ld, y=%ld\n", results[0], results[1]);
    assert(results[0] == 3);
    assert(results[1] == 2);

    // Test 3x3
    int64_t A3[] = {
        1, 0, 0,
        0, 1, 0,
        0, 0, 1
    };
    int64_t b3[] = {10, 20, 30};
    int64_t res3[3];
    assert(fsc_solve_linear_system(A3, b3, 3, p, res3) == 1);
    assert(res3[0] == 10 && res3[1] == 20 && res3[2] == 30);

    printf("Multi-Fault Solver Passed\n");

    test_recover_multi();
    test_fiber();

    printf("All Multi-Fault and Fiber tests passed!\n");
    return 0;
}
