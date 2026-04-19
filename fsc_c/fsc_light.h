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

/**
 * fsc_solve_linear_system: Solves Ax = b over GF(p).
 * results: output vector of size n
 * Returns 1 on success, 0 if singular.
 */
int fsc_solve_linear_system(const int64_t* A, const int64_t* b, int n, int64_t p, int64_t* results);

/**
 * fsc_calculate_fiber_target: Derives target from position (Model 4).
 */
int64_t fsc_calculate_fiber_target(int64_t position, int64_t modulus);

/**
 * fsc_recover_multi: Recovers multiple corrupted fields.
 * data: array containing corrupted values.
 * weights: 2D array of weights (num_constraints * num_fields).
 * n_data: number of fields in data.
 * targets: array of expected invariant values for each constraint.
 * moduli: array of moduli for each constraint.
 * n_cons: number of constraints (and number of expected corruptions).
 * corrupted_indices: indices of fields that are corrupted.
 */
int fsc_recover_multi(int64_t* data, const int8_t* weights, int n_data,
                     const int64_t* targets, const int64_t* moduli,
                     int n_cons, const int* corrupted_indices);

#endif
