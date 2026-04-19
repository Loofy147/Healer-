#include "fsc_light.h"

int64_t fsc_calculate_sum(const int64_t* data, const int8_t* weights, int n, int64_t modulus) {
    int64_t sum = 0;
    for (int i = 0; i < n; i++) {
        int64_t val = data[i];
        int64_t w = weights[i];
        if (modulus > 0) {
            int64_t term = (val % modulus) * (w % modulus);
            sum = (sum + (term % modulus)) % modulus;
            if (sum < 0) sum += modulus;
        } else {
            sum += val * w;
        }
    }
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
            int64_t term = (data[i] % modulus) * (weights[i] % modulus);
            sum_others = (sum_others + (term % modulus)) % modulus;
        } else {
            sum_others += data[i] * weights[i];
        }
    }

    if (modulus > 0) {
        if (sum_others < 0) sum_others += modulus;
        int64_t rhs = (target - sum_others) % modulus;
        if (rhs < 0) rhs += modulus;
        int64_t w_j = weights[corrupted_idx] % modulus;
        if (w_j < 0) w_j += modulus;
        if (w_j == 1) return rhs;
        int64_t inv_w = fsc_mod_inverse(w_j, modulus);
        int64_t recovered = (rhs * inv_w) % modulus;
        if (recovered < 0) recovered += modulus;
        return recovered;
    } else {
        // target = sum_others + w_j * v_j
        // v_j = (target - sum_others) / w_j
        return (target - sum_others) / weights[corrupted_idx];
    }
}
