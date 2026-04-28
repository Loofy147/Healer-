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
#include <string.h>

#include <immintrin.h>
/**
 * Extended Euclidean Algorithm for modular inverse.
 */
int64_t fsc_mod_inverse(int64_t a, int64_t m) {
    if (m == 1) return 0;
    int64_t m0 = m, t, q;
    int64_t x0 = 0, x1 = 1;

    if (a < 0) a = (a % m) + m;
    a %= m;

    while (a > 1) {
        if (m == 0) return 0;
        q = a / m;
        t = m;
        m = a % m;
        a = t;
        t = x0;
        x0 = x1 - q * x0;
        x1 = t;
    }
    if (x1 < 0) x1 += m0;
    return x1;
}

int64_t fsc_calculate_sum8(const uint8_t* restrict data, const int32_t* restrict weights, size_t n, int64_t modulus) {
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

uint8_t fsc_heal_single8(const uint8_t* restrict data, const int32_t* restrict weights, size_t n,
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
        return (uint8_t)(res % modulus);
    } else {
        int64_t w_j = weights ? (int64_t)weights[corrupted_idx] : 1;
        return (uint8_t)((target - (int64_t)sum_others) / w_j);
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

size_t fsc_batch_verify_model5(const uint8_t* restrict data, size_t n_blocks, size_t block_size,
                              int64_t modulus, size_t* restrict corrupted_indices) {
    size_t count = 0;
    for (size_t b = 0; b < n_blocks; b++) {
        const uint8_t* block = data + (b * block_size);
        __int128_t s1 = 0, s2 = 0, s3 = 0;

        for (size_t i = 0; i < block_size; i++) {
            __int128_t v = block[i];
            __int128_t w1 = (int64_t)(i + 1);
            s1 += v;
            s2 += v * w1;
            s3 += v * w1 * w1;
        }

        s1 %= modulus;
        s2 %= modulus;
        s3 %= modulus;

        int64_t t1 = (int64_t)(b % modulus);
        int64_t t2 = (int64_t)((b * 7) % modulus);
        int64_t t3 = (int64_t)((b * 13) % modulus);

        if ((int64_t)s1 != t1 || (int64_t)s2 != t2 || (int64_t)s3 != t3) {
            if (corrupted_indices) corrupted_indices[count] = b;
            count++;
        }
    }
    return count;
}

/**
 * fsc_block_seal: Calculates the 3 internal Model 5 parity bytes.
 */
int fsc_block_seal(uint8_t* block, size_t block_size, int64_t block_id, int64_t modulus) {
    size_t n = block_size;
    size_t d_len = n - 3;
    int64_t t[3] = { block_id % modulus, (block_id * 7) % modulus, (block_id * 13) % modulus };

    __int128_t s[3] = {0, 0, 0};
    for (size_t i = 0; i < d_len; i++) {
        __int128_t v = block[i];
        __int128_t w = (i + 1);
        s[0] += v;
        s[1] += v * w;
        s[2] += v * w * w;
    }

    __int128_t rhs[3];
    for(int i=0; i<3; i++) {
        rhs[i] = (t[i] - (s[i] % modulus)) % modulus;
        if (rhs[i] < 0) rhs[i] += modulus;
    }

    __int128_t M[3][4];
    for (int i = 0; i < 3; i++) {
        M[i][3] = rhs[i];
        for (int ki = 0; ki < 3; ki++) {
            size_t w_idx = n - 2 + ki;
            __int128_t weight = 1;
            for (int p = 0; p < i; p++) weight = (weight * w_idx) % modulus;
            M[i][ki] = weight;
        }
    }

    for (int col = 0; col < 3; col++) {
        int pivot = col;
        while (pivot < 3 && M[pivot][col] == 0) pivot++;
        if (pivot == 3) return FSC_ERR_SINGULAR;
        if (pivot != col) {
            for (int k = col; k <= 3; k++) {
                __int128_t tmp = M[col][k]; M[col][k] = M[pivot][k]; M[pivot][k] = tmp;
            }
        }
        int64_t inv_piv = fsc_mod_inverse((int64_t)M[col][col], modulus);
        for (int k = col; k <= 3; k++) M[col][k] = (M[col][k] * inv_piv) % modulus;
        for (int row = 0; row < 3; row++) {
            if (row != col && M[row][col] != 0) {
                __int128_t factor = M[row][col];
                for (int k = col; k <= 3; k++) {
                    M[row][k] = (M[row][k] - (factor * M[col][k]) % modulus) % modulus;
                    if (M[row][k] < 0) M[row][k] += modulus;
                }
            }
        }
    }
    for (int ki = 0; ki < 3; ki++) block[n - 3 + ki] = (uint8_t)(M[ki][3] % 256);
    return FSC_SUCCESS;
}

/**
 * fsc_heal_erasure8: Optimized Multi-block recovery using pre-inverted system matrix.
 */
int fsc_heal_erasure8(uint8_t* restrict volume_data, size_t n_blocks, size_t block_size,
                     size_t k_parity, size_t n_lost, const size_t* restrict bad_indices,
                     int64_t modulus) {
    if (n_lost == 0) return FSC_SUCCESS;
    if (n_lost > k_parity || n_lost > FSC_MAX_K) return FSC_ERR_BOUNDS;

    size_t n_data_blocks = n_blocks - k_parity;
    size_t chunk_size = block_size - 3;
    __int128_t A_inv[FSC_MAX_K][FSC_MAX_K];
    __int128_t M[FSC_MAX_K][FSC_MAX_K + 1];

    // 1. Build the system matrix A and invert it
    // A[j][ki] = (bad_indices[ki] + 1)^j if bad_indices[ki] < n_data_blocks
    // else A[j][ki] = -1 if (bad_indices[ki] - n_data_blocks == j) else 0
    for (size_t j = 0; j < n_lost; j++) {
        for (size_t ki = 0; ki < n_lost; ki++) {
            size_t bi = bad_indices[ki];
            if (bi < n_data_blocks) {
                __int128_t weight = 1;
                for (size_t p = 0; p < j; p++) weight = (weight * (bi + 1)) % modulus;
                M[j][ki] = weight;
            } else {
                M[j][ki] = (bi - n_data_blocks == j) ? -1 : 0;
                if (M[j][ki] < 0) M[j][ki] += modulus;
            }
        }
        // Identity on the right for inversion
        for (size_t ki = 0; ki < n_lost; ki++) M[j][n_lost + ki] = (j == ki) ? 1 : 0;
    }

    // Gaussian with multiple RHS (Identity)
    size_t system_size = n_lost;
    for (size_t col = 0; col < system_size; col++) {
        size_t pivot = col;
        while (pivot < system_size && M[pivot][col] == 0) pivot++;
        if (pivot == system_size) return FSC_ERR_SINGULAR;
        if (pivot != col) {
            for (size_t k = col; k < system_size + system_size; k++) {
                __int128_t tmp = M[col][k]; M[col][k] = M[pivot][k]; M[pivot][k] = tmp;
            }
        }
        int64_t inv_piv = fsc_mod_inverse((int64_t)M[col][col], modulus);
        for (size_t k = col; k < system_size + system_size; k++) M[col][k] = (M[col][k] * inv_piv) % modulus;
        for (size_t row = 0; row < system_size; row++) {
            if (row != col && M[row][col] != 0) {
                __int128_t factor = M[row][col];
                for (size_t k = col; k < system_size + system_size; k++) {
                    M[row][k] = (M[row][k] - (factor * M[col][k]) % modulus) % modulus;
                    if (M[row][k] < 0) M[row][k] += modulus;
                }
            }
        }
    }
    // Store inverted matrix
    for (size_t i = 0; i < n_lost; i++) {
        for (size_t j = 0; j < n_lost; j++) {
            A_inv[i][j] = M[i][n_lost + j];
        }
    }

    // 2. Vectorized solve for each byte offset
    for (size_t col = 0; col < chunk_size; col++) {
        __int128_t syndromes[FSC_MAX_K];
        for (size_t j = 0; j < n_lost; j++) {
            __int128_t sum_good = 0;
            for (size_t bi = 0; bi < n_data_blocks; bi++) {
                int is_bad = 0;
                for (size_t ki = 0; ki < n_lost; ki++) if (bad_indices[ki] == bi) { is_bad = 1; break; }
                if (is_bad) continue;

                uint8_t val = volume_data[bi * block_size + col];
                __int128_t weight = 1;
                for (size_t p = 0; p < j; p++) weight = (weight * (bi + 1)) % modulus;
                sum_good = (sum_good + (__int128_t)val * weight) % modulus;
            }

            size_t p_idx = n_data_blocks + j;
            int is_parity_bad = 0;
            for (size_t ki = 0; ki < n_lost; ki++) if (bad_indices[ki] == p_idx) { is_parity_bad = 1; break; }

            __int128_t rhs = 0;
            if (!is_parity_bad) {
                uint8_t p_val = volume_data[p_idx * block_size + col];
                rhs = (p_val - sum_good) % modulus;
            } else {
                rhs = (-sum_good) % modulus;
            }
            if (rhs < 0) rhs += modulus;
            syndromes[j] = rhs;
        }

        // x = A_inv * syndromes
        for (size_t ki = 0; ki < n_lost; ki++) {
            __int128_t res = 0;
            for (size_t j = 0; j < n_lost; j++) {
                res = (res + A_inv[ki][j] * syndromes[j]) % modulus;
            }
            volume_data[bad_indices[ki] * block_size + col] = (uint8_t)(res % 256);
        }
    }

    // 3. Reseal internal Model 5 parity
    for (size_t ki = 0; ki < n_lost; ki++) {
        size_t bi = bad_indices[ki];
        fsc_block_seal(volume_data + (bi * block_size), block_size, (int64_t)bi, modulus);
    }

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
#else
    (void)event_type; (void)index; (void)magnitude;
#endif
}

/**
 * fsc_calculate_sum8_avx2: AVX2-optimized modular sum.
 */
int64_t fsc_calculate_sum8_avx2(const uint8_t* data, const int32_t* weights, size_t n, int64_t modulus) {
    if (weights || modulus != 251 || n % 32 != 0) {
        return fsc_calculate_sum8(data, weights, n, modulus);
    }

    __m256i sum_vec = _mm256_setzero_si256();
    for (size_t i = 0; i < n; i += 32) {
        __m256i v = _mm256_loadu_si256((const __m256i*)(data + i));
        // Unpack and sum
        __m256i low = _mm256_unpacklo_epi8(v, _mm256_setzero_si256());
        __m256i high = _mm256_unpackhi_epi8(v, _mm256_setzero_si256());

        __m256i low_16 = _mm256_unpacklo_epi16(low, _mm256_setzero_si256());
        __m256i high_16 = _mm256_unpackhi_epi16(low, _mm256_setzero_si256());
        sum_vec = _mm256_add_epi32(sum_vec, low_16);
        sum_vec = _mm256_add_epi32(sum_vec, high_16);

        low_16 = _mm256_unpacklo_epi16(high, _mm256_setzero_si256());
        high_16 = _mm256_unpackhi_epi16(high, _mm256_setzero_si256());
        sum_vec = _mm256_add_epi32(sum_vec, low_16);
        sum_vec = _mm256_add_epi32(sum_vec, high_16);
    }

    int32_t sums[8];
    _mm256_storeu_si256((__m256i*)sums, sum_vec);
    int64_t total = 0;
    for (int i = 0; i < 8; i++) total += sums[i];
    return total % modulus;
}

/**
 * fsc_volume_encode8: Native full-volume encoding (RAID + Internal Seal).
 */
int fsc_volume_encode8(uint8_t* volume_data, size_t n_blocks, size_t block_size, size_t k_parity, int64_t modulus) {
    size_t n_data_blocks = n_blocks - k_parity;
    size_t d_len = block_size - 3;

    // 1. Seal all data blocks
    for (size_t i = 0; i < n_data_blocks; i++) {
        fsc_block_seal(volume_data + (i * block_size), block_size, (int64_t)i, modulus);
    }

    // 2. Generate RAID parity
    for (size_t col = 0; col < d_len; col++) {
        for (size_t j = 0; j < k_parity; j++) {
            __int128_t parity_val = 0;
            for (size_t i = 0; i < n_data_blocks; i++) {
                uint8_t val = volume_data[i * block_size + col];
                __int128_t weight = 1;
                for (size_t p = 0; p < j; p++) weight = (weight * (i + 1)) % modulus;
                parity_val = (parity_val + (__int128_t)val * weight) % modulus;
            }
            size_t p_idx = n_data_blocks + j;
            volume_data[p_idx * block_size + col] = (uint8_t)(parity_val % 256);
        }
    }

    // 3. Seal parity blocks
    for (size_t j = 0; j < k_parity; j++) {
        size_t p_idx = n_data_blocks + j;
        fsc_block_seal(volume_data + (p_idx * block_size), block_size, (int64_t)p_idx, modulus);
    }

    return FSC_SUCCESS;
}
