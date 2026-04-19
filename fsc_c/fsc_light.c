#include "fsc_light.h"
#include <stdlib.h>
#include <string.h>

int64_t fsc_calculate_sum(const int64_t* data, const int8_t* weights, int n, int64_t modulus) {
    int64_t sum = 0;
    for (int i = 0; i < n; i++) {
        int64_t val = data[i];
        int64_t w = (int64_t)weights[i];
        if (modulus > 0) {
            int64_t v_mod = val % modulus;
            if (v_mod < 0) v_mod += modulus;
            int64_t w_mod = w % modulus;
            if (w_mod < 0) w_mod += modulus;

            int64_t term = (v_mod * w_mod) % modulus;
            sum = (sum + term) % modulus;
        } else {
            sum += val * w;
        }
    }
    if (modulus > 0 && sum < 0) sum += modulus;
    return sum;
}

int64_t fsc_mod_inverse(int64_t a, int64_t m) {
    int64_t m0 = m, t, q;
    int64_t x0 = 0, x1 = 1;
    if (m <= 1) return 0;
    a %= m;
    if (a < 0) a += m;
    while (a > 1) {
        if (m == 0) break;
        q = a / m;
        t = m; m = a % m; a = t;
        t = x0; x0 = x1 - q * x0; x1 = t;
    }
    if (x1 < 0) x1 += m0;
    return x1;
}

int64_t fsc_recover_field(const int64_t* data, const int8_t* weights, int n, int64_t target, int64_t modulus, int corrupted_idx) {
    int64_t sum_others = 0;
    for (int i = 0; i < n; i++) {
        if (i == corrupted_idx) continue;
        if (modulus > 0) {
            int64_t v_mod = data[i] % modulus;
            if (v_mod < 0) v_mod += modulus;
            int64_t w_mod = (int64_t)weights[i] % modulus;
            if (w_mod < 0) w_mod += modulus;
            int64_t term = (v_mod * w_mod) % modulus;
            sum_others = (sum_others + term) % modulus;
        } else {
            sum_others += data[i] * (int64_t)weights[i];
        }
    }

    if (modulus > 0) {
        if (sum_others < 0) sum_others += modulus;
        int64_t rhs = (target - sum_others) % modulus;
        if (rhs < 0) rhs += modulus;
        int64_t w_j = (int64_t)weights[corrupted_idx] % modulus;
        if (w_j < 0) w_j += modulus;
        if (w_j == 1) return rhs;
        int64_t inv_w = fsc_mod_inverse(w_j, modulus);
        int64_t recovered = (rhs * inv_w) % modulus;
        if (recovered < 0) recovered += modulus;
        return recovered;
    } else {
        return (target - sum_others) / (int64_t)weights[corrupted_idx];
    }
}

int fsc_solve_linear_system(const int64_t* A, const int64_t* b, int n, int64_t p, int64_t* results) {
    // Augmented matrix [M | b]
    int64_t* M = (int64_t*)malloc(n * (n + 1) * sizeof(int64_t));
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            int64_t val = A[i * n + j] % p;
            if (val < 0) val += p;
            M[i * (n + 1) + j] = val;
        }
        int64_t val_b = b[i] % p;
        if (val_b < 0) val_b += p;
        M[i * (n + 1) + n] = val_b;
    }

    for (int col = 0; col < n; col++) {
        int pivot = -1;
        for (int r = col; r < n; r++) {
            if (M[r * (n + 1) + col] != 0) {
                pivot = r;
                break;
            }
        }
        if (pivot == -1) { free(M); return 0; }

        // Swap rows
        if (pivot != col) {
            for (int j = 0; j <= n; j++) {
                int64_t tmp = M[col * (n + 1) + j];
                M[col * (n + 1) + j] = M[pivot * (n + 1) + j];
                M[pivot * (n + 1) + j] = tmp;
            }
        }

        int64_t inv_piv = fsc_mod_inverse(M[col * (n + 1) + col], p);
        for (int j = col; j <= n; j++) {
            M[col * (n + 1) + j] = (M[col * (n + 1) + j] * inv_piv) % p;
        }

        for (int row = 0; row < n; row++) {
            if (row != col && M[row * (n + 1) + col] != 0) {
                int64_t factor = M[row * (n + 1) + col];
                for (int j = col; j <= n; j++) {
                    M[row * (n + 1) + j] = (M[row * (n + 1) + j] - (factor * M[col * (n + 1) + j]) % p) % p;
                    if (M[row * (n + 1) + j] < 0) M[row * (n + 1) + j] += p;
                }
            }
        }
    }

    for (int i = 0; i < n; i++) {
        results[i] = M[i * (n + 1) + n];
    }

    free(M);
    return 1;
}

int64_t fsc_calculate_fiber_target(int64_t position, int64_t modulus) {
    if (modulus == 0) return position;
    int64_t res = position % modulus;
    if (res < 0) res += modulus;
    return res;
}

int fsc_recover_multi(int64_t* data, const int8_t* weights, int n_data,
                     const int64_t* targets, const int64_t* moduli,
                     int n_cons, const int* corrupted_indices) {
    // We assume all constraints use the same modulus for simplicity in linear solving.
    // If they differ, the system is much more complex (CRT based).
    int64_t p = moduli[0];

    // b_i = target_i - sum(w_ij * v_j for j not in corrupted_indices)
    int64_t* b = (int64_t*)malloc(n_cons * sizeof(int64_t));
    int64_t* A = (int64_t*)malloc(n_cons * n_cons * sizeof(int64_t));

    for (int i = 0; i < n_cons; i++) {
        int64_t sum_others = 0;
        for (int j = 0; j < n_data; j++) {
            int is_corrupted = 0;
            for (int k = 0; k < n_cons; k++) {
                if (corrupted_indices[k] == j) { is_corrupted = 1; break; }
            }
            if (is_corrupted) continue;

            int64_t v_mod = data[j] % p; if (v_mod < 0) v_mod += p;
            int64_t w_mod = (int64_t)weights[i * n_data + j] % p; if (w_mod < 0) w_mod += p;
            sum_others = (sum_others + (v_mod * w_mod)) % p;
        }
        int64_t rhs = (targets[i] - sum_others) % p;
        if (rhs < 0) rhs += p;
        b[i] = rhs;

        for (int k = 0; k < n_cons; k++) {
            int64_t w_mod = (int64_t)weights[i * n_data + corrupted_indices[k]] % p;
            if (w_mod < 0) w_mod += p;
            A[i * n_cons + k] = w_mod;
        }
    }

    int64_t* results = (int64_t*)malloc(n_cons * sizeof(int64_t));
    int success = fsc_solve_linear_system(A, b, n_cons, p, results);

    if (success) {
        for (int k = 0; k < n_cons; k++) {
            data[corrupted_indices[k]] = results[k];
        }
    }

    free(b); free(A); free(results);
    return success;
}
