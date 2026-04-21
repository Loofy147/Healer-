/**
 * FSC: Forward Sector Correction
 * Copyright (C) 2024 FSC Core Team. All Rights Reserved.
 *
 * PUBLIC LICENSE: GNU Affero General Public License (AGPLv3)
 * COMMERCIAL LICENSE: Required for proprietary/enterprise use.
 *
 * PATENT PENDING: Industrial applications of these algebraic primitives
 * for database pages, kernel block devices, and network protocols.
 */

#include "libfsc.h"

int64_t fsc_mod_inverse(int64_t a, int64_t m) {
    if (m <= 1) return 0;
    __int128_t m0 = m, t, q;
    __int128_t x0 = 0, x1 = 1;
    __int128_t aa = a % m;
    if (aa < 0) aa += m;
    while (aa > 1) {
        if (m0 == 0) return 0;
        q = aa / m0;
        t = m0; m0 = aa % m0; aa = t;
        t = x0; x0 = x1 - q * x0; x1 = t;
    }
    if (x1 < 0) x1 += m;
    return (int64_t)x1;
}

int64_t fsc_calculate_sum8(const uint8_t* restrict data, const int32_t* restrict weights, size_t n, int64_t modulus) {
    if (weights) {
        int64_t sum = 0;
        size_t i = 0;
        // Unroll 4x
        for (; i + 3 < n; i += 4) {
            sum += (int64_t)data[i] * weights[i];
            sum += (int64_t)data[i+1] * weights[i+1];
            sum += (int64_t)data[i+2] * weights[i+2];
            sum += (int64_t)data[i+3] * weights[i+3];
        }
        for (; i < n; i++) {
            sum += (int64_t)data[i] * weights[i];
        }
        if (modulus > 0) {
            sum %= modulus;
            if (sum < 0) sum += modulus;
        }
        return sum;
    } else {
        uint64_t sum = 0;
        size_t i = 0;
        for (; i + 3 < n; i += 4) {
            sum += data[i];
            sum += data[i+1];
            sum += data[i+2];
            sum += data[i+3];
        }
        for (; i < n; i++) {
            sum += data[i];
        }
        if (modulus > 0) {
            return (int64_t)(sum % (uint64_t)modulus);
        }
        return (int64_t)sum;
    }
}

uint8_t fsc_heal_single8(const uint8_t* restrict data, const int32_t* restrict weights, size_t n,
                        int64_t target, int64_t modulus, size_t corrupted_idx) {
    if (corrupted_idx >= n) return 0;
    int64_t sum_others = 0;
    if (weights) {
        for (size_t i = 0; i < n; i++) {
            if (i == corrupted_idx) continue;
            sum_others += (int64_t)data[i] * weights[i];
        }
    } else {
        uint64_t sum = 0;
        for (size_t i = 0; i < n; i++) {
            if (i == corrupted_idx) continue;
            sum += data[i];
        }
        sum_others = (int64_t)sum;
    }

    if (modulus > 0) {
        sum_others %= modulus;
        if (sum_others < 0) sum_others += modulus;
        int64_t rhs = (target - sum_others) % modulus;
        if (rhs < 0) rhs += modulus;
        int64_t w_j = weights ? (int32_t)weights[corrupted_idx] : 1;
        int64_t inv_w = fsc_mod_inverse((int64_t)(w_j % modulus), modulus);
        __int128_t res = (__int128_t)rhs * inv_w;
        return (uint8_t)((res % modulus) % 256);
    } else {
        int64_t w_j = weights ? (int64_t)weights[corrupted_idx] : 1;
        return (uint8_t)((target - sum_others) / w_j);
    }
}

int64_t fsc_calculate_sum64(const int64_t* restrict data, const int32_t* restrict weights, size_t n, int64_t modulus) {
    __int128_t sum = 0;
    if (weights) {
        for (size_t i = 0; i < n; i++) {
            sum += (__int128_t)data[i] * weights[i];
        }
    } else {
        for (size_t i = 0; i < n; i++) {
            sum += data[i];
        }
    }
    if (modulus > 0) {
        sum %= modulus;
        if (sum < 0) sum += modulus;
    }
    return (int64_t)sum;
}

int64_t fsc_heal_single64(const int64_t* restrict data, const int32_t* restrict weights, size_t n,
                         int64_t target, int64_t modulus, size_t corrupted_idx) {
    if (corrupted_idx >= n) return 0;
    __int128_t sum_others = 0;
    if (weights) {
        for (size_t i = 0; i < n; i++) {
            if (i == corrupted_idx) continue;
            sum_others += (__int128_t)data[i] * weights[i];
        }
    } else {
        for (size_t i = 0; i < n; i++) {
            if (i == corrupted_idx) continue;
            sum_others += data[i];
        }
    }

    if (modulus > 0) {
        sum_others %= modulus;
        if (sum_others < 0) sum_others += modulus;
        int64_t rhs = (target - (int64_t)sum_others) % modulus;
        if (rhs < 0) rhs += modulus;
        int64_t w_j = weights ? (int32_t)weights[corrupted_idx] : 1;
        int64_t inv_w = fsc_mod_inverse((int64_t)(w_j % modulus), modulus);
        __int128_t res = (__int128_t)rhs * inv_w;
        return (int64_t)(res % modulus);
    } else {
        int64_t w_j = weights ? (int64_t)weights[corrupted_idx] : 1;
        return (target - (int64_t)sum_others) / w_j;
    }
}

int fsc_heal_multi64(int64_t* restrict data, const int32_t* restrict weights, size_t n_data,
                    const int64_t* restrict targets, const int64_t* restrict moduli,
                    size_t k, const size_t* restrict corrupted_indices) {
    if (k == 0 || k > FSC_MAX_K) return FSC_ERR_BOUNDS;
    for (size_t ki = 0; ki < k; ki++) {
        if (corrupted_indices[ki] >= n_data) return FSC_ERR_BOUNDS;
    }
    int64_t p = moduli[0];
    if (p <= 0) return FSC_ERR_INVALID;
    __int128_t M[FSC_MAX_K][FSC_MAX_K + 1];

    for (size_t i = 0; i < k; i++) {
        __int128_t sum_others = 0;
        for (size_t j = 0; j < n_data; j++) {
            int is_corrupted = 0;
            for (size_t ki = 0; ki < k; ki++) if (corrupted_indices[ki] == j) { is_corrupted = 1; break; }
            if (is_corrupted) continue;
            __int128_t v = data[j] % p; if (v < 0) v += p;
            __int128_t w = weights ? (int32_t)weights[i * n_data + j] % p : 1; if (w < 0) w += p;
            sum_others = (sum_others + (v * w)) % p;
        }
        __int128_t rhs = (targets[i] - sum_others) % p;
        if (rhs < 0) rhs += p;
        M[i][k] = rhs;
        for (size_t ki = 0; ki < k; ki++) {
            __int128_t w = weights ? (int32_t)weights[i * n_data + corrupted_indices[ki]] % p : 1;
            if (w < 0) w += p;
            M[i][ki] = w;
        }
    }

    for (size_t col = 0; col < k; col++) {
        size_t pivot = col;
        while (pivot < k && M[pivot][col] == 0) pivot++;
        if (pivot == k) return FSC_ERR_SINGULAR;
        if (pivot != col) {
            for (size_t j = col; j <= k; j++) {
                __int128_t tmp = M[col][j]; M[col][j] = M[pivot][j]; M[pivot][j] = tmp;
            }
        }
        int64_t inv_piv = fsc_mod_inverse((int64_t)M[col][col], p);
        for (size_t j = col; j <= k; j++) M[col][j] = (M[col][j] * inv_piv) % p;
        for (size_t row = 0; row < k; row++) {
            if (row != col && M[row][col] != 0) {
                __int128_t factor = M[row][col];
                for (size_t j = col; j <= k; j++) {
                    M[row][j] = (M[row][j] - (factor * M[col][j]) % p) % p;
                    if (M[row][j] < 0) M[row][j] += p;
                }
            }
        }
    }
    for (size_t ki = 0; ki < k; ki++) data[corrupted_indices[ki]] = (int64_t)M[ki][k];
    return FSC_SUCCESS;
}

void fsc_buffer_seal(FSCBuffer* b) {
    b->target = fsc_calculate_sum8(b->buffer, b->weights, b->len, b->modulus);
    if (b->weights2) {
        b->target2 = fsc_calculate_sum8(b->buffer, b->weights2, b->len, b->modulus);
    }
}

int fsc_buffer_verify(FSCBuffer* b) {
    if (fsc_calculate_sum8(b->buffer, b->weights, b->len, b->modulus) != b->target) return 0;
    if (b->weights2 && fsc_calculate_sum8(b->buffer, b->weights2, b->len, b->modulus) != b->target2) return 0;
    return 1;
}

int fsc_buffer_heal(FSCBuffer* b) {
    int64_t actual1 = fsc_calculate_sum8(b->buffer, b->weights, b->len, b->modulus);
    if (actual1 == b->target) {
        if (!b->weights2 || fsc_calculate_sum8(b->buffer, b->weights2, b->len, b->modulus) == b->target2) {
            return -2;
        }
    }

    __int128_t s1 = (b->target - actual1) % b->modulus;
    if (s1 < 0) s1 += b->modulus;

    if (b->weights2) {
        int64_t actual2 = fsc_calculate_sum8(b->buffer, b->weights2, b->len, b->modulus);
        __int128_t s2 = (b->target2 - actual2) % b->modulus;
        if (s2 < 0) s2 += b->modulus;

        for (size_t i = 0; i < b->len; i++) {
            int64_t w1 = b->weights ? (int32_t)b->weights[i] % b->modulus : 1;
            int64_t w2 = (int32_t)b->weights2[i] % b->modulus;
            if (w1 < 0) w1 += b->modulus;
            if (w2 < 0) w2 += b->modulus;

            int64_t inv_w1 = fsc_mod_inverse(w1, b->modulus);
            if (inv_w1 == 0 && w1 != 1) continue;

            __int128_t delta = (__int128_t)s1 * inv_w1;
            if (((delta % b->modulus) * w2) % b->modulus == s2) {
                uint8_t original = b->buffer[i];
                b->buffer[i] = (uint8_t)(((__int128_t)original + (delta % b->modulus)) % b->modulus);
                if (fsc_buffer_verify(b)) return (int)i;
                b->buffer[i] = original;
            }
        }
    } else {
        for (size_t i = 0; i < b->len; i++) {
            uint8_t original = b->buffer[i];
            uint8_t recovered = fsc_heal_single8(b->buffer, b->weights, b->len, b->target, b->modulus, i);
            if (recovered != original) {
                b->buffer[i] = recovered;
                if (fsc_buffer_verify(b)) return (int)i;
                b->buffer[i] = original;
            }
        }
    }
    return -1;
}

#include <stdio.h>

void fsc_audit_log(const char* event_type, int index, int64_t magnitude) {
#if FSC_COMMERCIAL_BUILD
    printf("[COMMERCIAL-AUDIT] EVENT: %s | OFFSET: %d | MAGNITUDE: %ld\n",
           event_type, index, magnitude);
    // In a real enterprise build, this would write to a secure tamper-proof ledger.
#else
    // Core version: No-op to preserve performance and binary size.
    (void)event_type; (void)index; (void)magnitude;
#endif
}

int fsc_heal_multi8(uint8_t* restrict data, const int32_t* restrict weights, size_t n_data,
                   const int64_t* restrict targets, const int64_t* restrict moduli,
                   size_t k, const size_t* restrict corrupted_indices) {
    if (k == 0 || k > FSC_MAX_K) return FSC_ERR_BOUNDS;
    for (size_t ki = 0; ki < k; ki++) {
        if (corrupted_indices[ki] >= n_data) return FSC_ERR_BOUNDS;
    }
    int64_t p = moduli[0];
    if (p <= 0) return FSC_ERR_INVALID;
    __int128_t M[FSC_MAX_K][FSC_MAX_K + 1];

    for (size_t i = 0; i < k; i++) {
        __int128_t sum_others = 0;
        for (size_t j = 0; j < n_data; j++) {
            int is_corrupted = 0;
            for (size_t ki = 0; ki < k; ki++) if (corrupted_indices[ki] == j) { is_corrupted = 1; break; }
            if (is_corrupted) continue;
            __int128_t v = data[j] % p;
            __int128_t w = weights ? (int32_t)weights[i * n_data + j] % p : 1; if (w < 0) w += p;
            sum_others = (sum_others + (v * w)) % p;
        }
        __int128_t rhs = (targets[i] - sum_others) % p;
        if (rhs < 0) rhs += p;
        M[i][k] = rhs;
        for (size_t ki = 0; ki < k; ki++) {
            __int128_t w = weights ? (int32_t)weights[i * n_data + corrupted_indices[ki]] % p : 1;
            if (w < 0) w += p;
            M[i][ki] = w;
        }
    }

    for (size_t col = 0; col < k; col++) {
        size_t pivot = col;
        while (pivot < k && M[pivot][col] == 0) pivot++;
        if (pivot == k) return FSC_ERR_SINGULAR;
        if (pivot != col) {
            for (size_t j = col; j <= k; j++) {
                __int128_t tmp = M[col][j]; M[col][j] = M[pivot][j]; M[pivot][j] = tmp;
            }
        }
        int64_t inv_piv = fsc_mod_inverse((int64_t)M[col][col], p);
        for (size_t j = col; j <= k; j++) M[col][j] = (M[col][j] * inv_piv) % p;
        for (size_t row = 0; row < k; row++) {
            if (row != col && M[row][col] != 0) {
                __int128_t factor = M[row][col];
                for (size_t j = col; j <= k; j++) {
                    M[row][j] = (M[row][j] - (factor * M[col][j]) % p) % p;
                    if (M[row][j] < 0) M[row][j] += p;
                }
            }
        }
    }
    for (size_t ki = 0; ki < k; ki++) data[corrupted_indices[ki]] = (uint8_t)(M[ki][k] % 256);
    return FSC_SUCCESS;
}
