#ifndef FSC_LIGHT_H
#define FSC_LIGHT_H

#include <stdint.h>

/**
 * fsc_calculate_sum: Calculates the weighted modular sum of a data array.
 */
int64_t fsc_calculate_sum(const int64_t* data, const int8_t* weights, int n, int64_t modulus);

/**
 * fsc_mod_inverse: Calculates (a^-1) mod m using Extended Euclidean Algorithm.
 */
int64_t fsc_mod_inverse(int64_t a, int64_t m);

/**
 * fsc_recover_field: Recovers a single corrupted field.
 */
int64_t fsc_recover_field(const int64_t* data, const int8_t* weights, int n, int64_t target, int64_t modulus, int corrupted_idx);

#endif
