/*
FSC: Forward Sector Correction - Native Core (v7.32)
Copyright (C) 2024 FSC Core Team. All Rights Reserved.
*/

#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <immintrin.h>
#include <omp.h>

#define FSC_SUCCESS 1
#define FSC_ERR_INVALID -2
#define FSC_ERR_BOUNDS -1
#define FSC_ERR_SINGULAR 0
#define FSC_MAX_K 16

int64_t fsc_mod_pow(int64_t base, int64_t exp, int64_t m) {
    int64_t res = 1; base %= m;
    while (exp > 0) {
        if (exp % 2 == 1) res = (__int128_t)res * base % m;
        base = (__int128_t)base * base % m;
        exp /= 2;
    }
    return res;
}

int64_t fsc_mod_inverse(int64_t a, int64_t m) {
    if (m <= 1) return -1;
    a = (a % m + m) % m;
    if (a == 0) return -1;
    int64_t t = 0, newt = 1;
    int64_t r = m, newr = a;
    while (newr != 0) {
        int64_t q = r / newr;
        int64_t tmp = t; t = newt; newt = tmp - q * newt;
        tmp = r; r = newr; newr = tmp - q * newr;
    }
    if (r > 1) return -1;
    if (t < 0) t += m;
    return t;
}

void fsc_syndromes_4way(const uint8_t* data, size_t n, __int128_t* s, int64_t modulus) {
    s[0] = s[1] = s[2] = s[3] = 0;
    if (modulus <= 1) return;
    size_t i = 0;
    __m256i v_s0 = _mm256_setzero_si256();
    __m256i v_s1 = _mm256_setzero_si256();
    __m256i v_s2 = _mm256_setzero_si256();
    __m256i v_zero = _mm256_setzero_si256();
    for (; i + 31 < n; i += 32) {
        __m256i v_data = _mm256_loadu_si256((const __m256i*)(data + i));
        v_s0 = _mm256_add_epi64(v_s0, _mm256_sad_epu8(v_data, v_zero));
        for (int c = 0; c < 4; c++) {
            __m128i v_d8 = _mm_loadl_epi64((const __m128i*)(data + i + c*8));
            __m256i v_d32 = _mm256_cvtepu8_epi32(v_d8);
            uint32_t bw = (uint32_t)(i + c*8 + 1);
            __m256i v_w = _mm256_setr_epi32(bw, bw+1, bw+2, bw+3, bw+4, bw+5, bw+6, bw+7);
            __m256i v_p1 = _mm256_mullo_epi32(v_d32, v_w);
            v_s1 = _mm256_add_epi64(v_s1, _mm256_cvtepu32_epi64(_mm256_extracti128_si256(v_p1, 0)));
            v_s1 = _mm256_add_epi64(v_s1, _mm256_cvtepu32_epi64(_mm256_extracti128_si256(v_p1, 1)));
            __m256i v_w2 = _mm256_mullo_epi32(v_w, v_w);
            __m256i v_p2 = _mm256_mullo_epi32(v_d32, v_w2);
            v_s2 = _mm256_add_epi64(v_s2, _mm256_cvtepu32_epi64(_mm256_extracti128_si256(v_p2, 0)));
            v_s2 = _mm256_add_epi64(v_s2, _mm256_cvtepu32_epi64(_mm256_extracti128_si256(v_p2, 1)));
        }
        if ((i & 0xFFF) == 0xFE0) {
            uint64_t a_tmp[4];
            _mm256_storeu_si256((__m256i*)a_tmp, v_s1); s[1] += (__int128_t)a_tmp[0]+a_tmp[1]+a_tmp[2]+a_tmp[3];
            _mm256_storeu_si256((__m256i*)a_tmp, v_s2); s[2] += (__int128_t)a_tmp[0]+a_tmp[1]+a_tmp[2]+a_tmp[3];
            v_s1 = _mm256_setzero_si256(); v_s2 = _mm256_setzero_si256();
            s[1] %= modulus; s[2] %= modulus;
        }
    }
    uint64_t a_tmp[4];
    _mm256_storeu_si256((__m256i*)a_tmp, v_s0); s[0] = (__int128_t)a_tmp[0]+a_tmp[1]+a_tmp[2]+a_tmp[3];
    _mm256_storeu_si256((__m256i*)a_tmp, v_s1); s[1] += (__int128_t)a_tmp[0]+a_tmp[1]+a_tmp[2]+a_tmp[3];
    _mm256_storeu_si256((__m256i*)a_tmp, v_s2); s[2] += (__int128_t)a_tmp[0]+a_tmp[1]+a_tmp[2]+a_tmp[3];
    for (; i < n; i++) {
        uint64_t val = data[i]; uint64_t w = i + 1;
        s[0] += val; s[1] += (__int128_t)val * w; s[2] += (__int128_t)val * w * w;
    }
    s[0] %= modulus; s[1] %= modulus; s[2] %= modulus;
}

int64_t fsc_calculate_sum8(const uint8_t* data, const int32_t* weights, size_t n, int64_t modulus) {
    if (modulus <= 1) return 0;
    __int128_t sum = 0;
    size_t i = 0;
    if (!weights) {
        __m256i v_sum = _mm256_setzero_si256();
        for (; i + 31 < n; i += 32) {
            __m256i v_data = _mm256_loadu_si256((const __m256i*)(data + i));
            v_sum = _mm256_add_epi64(v_sum, _mm256_sad_epu8(v_data, _mm256_setzero_si256()));
        }
        uint64_t s_arr[4]; _mm256_storeu_si256((__m256i*)s_arr, v_sum);
        sum = (__int128_t)s_arr[0] + s_arr[1] + s_arr[2] + s_arr[3];
    } else {
        for (; i < n; i++) sum += (__int128_t)data[i] * weights[i];
    }
    return (int64_t)(sum % modulus);
}

uint8_t fsc_heal_single8(const uint8_t* data, const int32_t* weights, size_t n, int64_t target, int64_t modulus, size_t corrupted_idx) {
    int64_t actual = fsc_calculate_sum8(data, weights, n, modulus);
    int64_t weight = weights ? weights[corrupted_idx] % modulus : 1;
    int64_t inv_w = fsc_mod_inverse(weight, modulus);
    if (inv_w == -1) return data[corrupted_idx];
    int64_t delta = (target - actual + modulus) % modulus;
    int64_t res = (data[corrupted_idx] + (__int128_t)delta * inv_w) % modulus;
    return (uint8_t)((res < 0) ? res + modulus : res);
}

int fsc_block_seal(uint8_t* block, size_t block_size, int64_t block_id, int64_t modulus) {
    size_t d_len = block_size - 3;
    int64_t b_salt = block_id + 1;
    __int128_t s[4];
    fsc_syndromes_4way(block, d_len, s, modulus);
    int64_t t1 = b_salt % modulus, t2 = (b_salt * 7) % modulus, t3 = (b_salt * 13) % modulus;
    int64_t b1 = (t1 - (int64_t)s[0] + modulus) % modulus;
    int64_t b2 = (t2 - (int64_t)s[1] + modulus) % modulus;
    int64_t b3 = (t3 - (int64_t)s[2] + modulus) % modulus;
    int64_t n1 = block_size - 2, n2 = block_size - 1, n3 = block_size;
    int64_t a11 = 1, a12 = 1, a13 = 1;
    int64_t a21 = n1 % modulus, a22 = n2 % modulus, a23 = n3 % modulus;
    int64_t a31 = (a21 * a21) % modulus, a32 = (a22 * a22) % modulus, a33 = (a23 * a23) % modulus;
    int64_t det = (a11 * (a22 * a33 % modulus - a23 * a32 % modulus + modulus) % modulus -
                   a12 * (a21 * a33 % modulus - a23 * a31 % modulus + modulus) % modulus +
                   a13 * (a21 * a32 % modulus - a22 * a31 % modulus + modulus) % modulus + modulus) % modulus;
    int64_t inv_det = fsc_mod_inverse(det, modulus);
    if (inv_det == -1) return FSC_ERR_SINGULAR;
    block[block_size - 3] = (uint8_t)(((a22 * a33 - a23 * a32) % modulus * b1 % modulus +
                                      (a13 * a32 - a12 * a33) % modulus * b2 % modulus +
                                      (a12 * a23 - a13 * a22) % modulus * b3 % modulus + 3 * modulus) % modulus * inv_det % modulus);
    block[block_size - 2] = (uint8_t)(((a23 * a31 - a21 * a33) % modulus * b1 % modulus +
                                      (a11 * a33 - a13 * a31) % modulus * b2 % modulus +
                                      (a13 * a21 - a11 * a23) % modulus * b3 % modulus + 3 * modulus) % modulus * inv_det % modulus);
    block[block_size - 1] = (uint8_t)(((a21 * a32 - a22 * a31) % modulus * b1 % modulus +
                                      (a12 * a31 - a11 * a32) % modulus * b2 % modulus +
                                      (a11 * a22 - a12 * a21) % modulus * b3 % modulus + 3 * modulus) % modulus * inv_det % modulus);
    return FSC_SUCCESS;
}

int fsc_block_verify(const uint8_t* block, size_t block_size, int64_t block_id, int64_t modulus) {
    __int128_t s[4]; fsc_syndromes_4way(block, block_size, s, modulus);
    int64_t b_salt = block_id + 1;
    return (s[0] == b_salt % modulus && s[1] == (b_salt * 7) % modulus && s[2] == (b_salt * 13) % modulus);
}

size_t fsc_batch_verify_model5(const uint8_t* data, size_t n_blocks, size_t block_size, int64_t modulus, size_t* corrupted_indices) {
    size_t count = 0;
    #pragma omp parallel
    {
        size_t local_indices[1024]; size_t local_count = 0;
        #pragma omp for nowait
        for (size_t i = 0; i < n_blocks; i++) {
            if (!fsc_block_verify(data + i * block_size, block_size, (int64_t)i, modulus)) {
                local_indices[local_count++] = i;
                if (local_count >= 1024) {
                    #pragma omp critical
                    { for (size_t j = 0; j < local_count; j++) corrupted_indices[count++] = local_indices[j]; }
                    local_count = 0;
                }
            }
        }
        #pragma omp critical
        { for (size_t j = 0; j < local_count; j++) corrupted_indices[count++] = local_indices[j]; }
    }
    return count;
}

int fsc_volume_encode8(uint8_t* buffer, size_t n_blocks, size_t block_size, size_t k_parity, int64_t modulus) {
    size_t n_data = n_blocks - k_parity; size_t d_len = block_size - 3;
    for (size_t j = 0; j < k_parity; j++) memset(buffer + (n_data + j) * block_size, 0, d_len);
    #pragma omp parallel for
    for (size_t p = 0; p < d_len; p++) {
        __int128_t acc[FSC_MAX_K]; for (size_t j = 0; j < k_parity; j++) acc[j] = 0;
        for (size_t i = 0; i < n_data; i++) {
            uint8_t v = buffer[i * block_size + p]; if (v == 0) continue;
            for (size_t j = 0; j < k_parity; j++) acc[j] += (__int128_t)v * fsc_mod_pow(i + 1, j, modulus);
        }
        for (size_t j = 0; j < k_parity; j++) buffer[(n_data + j) * block_size + p] = (uint8_t)(acc[j] % modulus);
    }
    for (size_t j = 0; j < k_parity; j++) fsc_block_seal(buffer + (n_data + j) * block_size, block_size, (int64_t)(n_data + j), modulus);
    return FSC_SUCCESS;
}

int fsc_volume_write8(uint8_t* volume_data, size_t n_blocks, size_t block_size, size_t k_parity, int64_t modulus, const uint8_t* user_data, size_t user_data_len) {
    size_t n_data = n_blocks - k_parity; size_t d_len = block_size - 3;
    size_t total_capacity = n_data * d_len;
    size_t to_copy = user_data_len < total_capacity ? user_data_len : total_capacity;
    memset(volume_data, 0, n_blocks * block_size);
    for (size_t i = 0; i < n_data; i++) {
        size_t offset = i * d_len; if (offset >= to_copy) break;
        size_t chunk = (to_copy - offset) < d_len ? (to_copy - offset) : d_len;
        memcpy(volume_data + i * block_size, user_data + offset, chunk);
        fsc_block_seal(volume_data + i * block_size, block_size, (int64_t)i, modulus);
    }
    return fsc_volume_encode8(volume_data, n_blocks, block_size, k_parity, modulus);
}

int fsc_solve_modular(int64_t* A, int64_t* B, size_t n, int64_t m, size_t rhs_cols) {
    for (size_t i = 0; i < n; i++) {
        size_t pivot = i; while (pivot < n && A[pivot * n + i] == 0) pivot++;
        if (pivot == n) return FSC_ERR_SINGULAR;
        if (pivot != i) {
            for (size_t j = i; j < n; j++) { int64_t tmp = A[i * n + j]; A[i * n + j] = A[pivot * n + j]; A[pivot * n + j] = tmp; }
            for (size_t p = 0; p < rhs_cols; p++) { int64_t tmp = B[i * rhs_cols + p]; B[i * rhs_cols + p] = B[pivot * rhs_cols + p]; B[pivot * rhs_cols + p] = tmp; }
        }
        int64_t inv = fsc_mod_inverse(A[i * n + i], m);
        for (size_t j = i; j < n; j++) A[i * n + j] = (A[i * n + j] * inv) % m;
        for (size_t p = 0; p < rhs_cols; p++) B[i * rhs_cols + p] = (B[i * rhs_cols + p] * inv) % m;
        for (size_t k = 0; k < n; k++) {
            if (k != i) {
                int64_t factor = A[k * n + i];
                for (size_t j = i; j < n; j++) A[k * n + j] = (A[k * n + j] - (factor * A[i * n + j] % m) + m) % m;
                for (size_t p = 0; p < rhs_cols; p++) B[k * rhs_cols + p] = (B[k * rhs_cols + p] - (factor * B[i * rhs_cols + p] % m) + m) % m;
            }
        }
    }
    return FSC_SUCCESS;
}

int fsc_heal_multi8(uint8_t* data, const int32_t* weights, size_t n_data, const int64_t* targets, const int64_t* moduli, size_t k, const size_t* corrupted_indices) {
    if (k == 0) return FSC_SUCCESS; if (k > FSC_MAX_K) return FSC_ERR_INVALID;
    int64_t m = moduli[0]; int64_t A[FSC_MAX_K * FSC_MAX_K], B[FSC_MAX_K];
    for (size_t j = 0; j < k; j++) {
        __int128_t actual = 0;
        for (size_t i = 0; i < n_data; i++) actual += (__int128_t)data[i] * (weights ? weights[j * n_data + i] : 1);
        B[j] = (targets[j] - (int64_t)(actual % moduli[j]) + moduli[j]) % moduli[j];
        for (size_t i = 0; i < k; i++) A[j * k + i] = weights ? weights[j * n_data + corrupted_indices[i]] : 1;
    }
    int res = fsc_solve_modular(A, B, k, m, 1);
    if (res == FSC_SUCCESS) for (size_t i = 0; i < k; i++) data[corrupted_indices[i]] = (uint8_t)((data[corrupted_indices[i]] + B[i]) % 256);
    return res;
}

int fsc_heal_multi64(int64_t* data, const int32_t* weights, size_t n_data, const int64_t* targets, const int64_t* moduli, size_t k, const size_t* corrupted_indices) {
    if (k == 0) return FSC_SUCCESS; if (k > FSC_MAX_K) return FSC_ERR_INVALID;
    int64_t m = moduli[0]; int64_t A[FSC_MAX_K * FSC_MAX_K], B[FSC_MAX_K];
    for (size_t j = 0; j < k; j++) {
        __int128_t actual = 0;
        for (size_t i = 0; i < n_data; i++) actual += (__int128_t)data[i] * (weights ? weights[j * n_data + i] : 1);
        B[j] = (targets[j] - (int64_t)(actual % moduli[j]) + moduli[j]) % moduli[j];
        for (size_t i = 0; i < k; i++) A[j * k + i] = weights ? weights[j * n_data + corrupted_indices[i]] : 1;
    }
    int res = fsc_solve_modular(A, B, k, m, 1);
    if (res == FSC_SUCCESS) for (size_t i = 0; i < k; i++) data[corrupted_indices[i]] = (data[corrupted_indices[i]] + B[i]) % m;
    return res;
}

int fsc_heal_erasure8(uint8_t* buffer, size_t n_blocks, size_t block_size, size_t k_parity, size_t n_bad, const size_t* bad_indices, int64_t modulus) {
    if (n_bad == 0) return FSC_SUCCESS; if (n_bad > k_parity || n_bad > FSC_MAX_K) return FSC_ERR_INVALID;
    size_t n_data = n_blocks - k_parity, d_len = block_size - 3;
    size_t n_bad_data = 0; size_t bad_data_indices[FSC_MAX_K];
    for (size_t i = 0; i < n_bad; i++) if (bad_indices[i] < n_data) bad_data_indices[n_bad_data++] = bad_indices[i];
    if (n_bad_data == 0) return fsc_volume_encode8(buffer, n_blocks, block_size, k_parity, modulus);
    size_t avail_parity_indices[FSC_MAX_K]; size_t n_avail_parity = 0;
    for (size_t j = 0; j < k_parity; j++) {
        int lost = 0; for (size_t k = 0; k < n_bad; k++) if (bad_indices[k] == n_data + j) { lost = 1; break; }
        if (!lost) avail_parity_indices[n_avail_parity++] = j;
    }
    if (n_avail_parity < n_bad_data) return FSC_ERR_INVALID;
    int64_t A[FSC_MAX_K * FSC_MAX_K]; int64_t* B = (int64_t*)malloc(n_bad_data * d_len * sizeof(int64_t));
    memset(B, 0, n_bad_data * d_len * sizeof(int64_t));
    for (size_t j_idx = 0; j_idx < n_bad_data; j_idx++) {
        size_t j = avail_parity_indices[j_idx];
        for (size_t k = 0; k < n_bad_data; k++) A[j_idx * n_bad_data + k] = fsc_mod_pow(bad_data_indices[k] + 1, j, modulus);
        uint8_t* p_block = buffer + (n_data + j) * block_size;
        for (size_t p = 0; p < d_len; p++) B[j_idx * d_len + p] = p_block[p];
        for (size_t i = 0; i < n_data; i++) {
            int lost = 0; for (size_t k = 0; k < n_bad_data; k++) if (bad_data_indices[k] == i) { lost = 1; break; }
            if (lost) continue;
            int64_t w = fsc_mod_pow(i + 1, j, modulus); uint8_t* d_block = buffer + i * block_size;
            for (size_t p = 0; p < d_len; p++) B[j_idx * d_len + p] = (B[j_idx * d_len + p] - (int64_t)d_block[p] * w % modulus + modulus) % modulus;
        }
    }
    int res = fsc_solve_modular(A, B, n_bad_data, modulus, d_len);
    if (res == FSC_SUCCESS) {
        for (size_t k = 0; k < n_bad_data; k++) {
            size_t bi = bad_data_indices[k]; uint8_t* b = buffer + bi * block_size;
            for (size_t p = 0; p < d_len; p++) b[p] = (uint8_t)(B[k * d_len + p] % modulus);
            fsc_block_seal(b, block_size, (int64_t)bi, modulus);
        }
    }
    free(B);
    if (res != FSC_SUCCESS) return res;
    return fsc_volume_encode8(buffer, n_blocks, block_size, k_parity, modulus);
}

void fsc_poly_mul_avx2(const int64_t* a, const int64_t* b, int64_t* res, size_t n, int64_t q) {
    if (q <= 1) return;
    #pragma omp parallel for
    for (size_t i = 0; i < n; i++) {
        __int128_t acc = 0;
        for (size_t j = 0; j < n; j++) {
            if (i >= j) acc += (__int128_t)a[j] * b[i - j];
            else acc -= (__int128_t)a[j] * b[i - j + n];
        }
        int64_t r = (int64_t)(acc % q); res[i] = (r < 0) ? r + q : r;
    }
}
void fsc_audit_log(const char* e, int i, int64_t m) {}
int fsc_silicon_verify_gate(const uint8_t* d, const uint8_t* w, size_t n, int64_t t, int64_t m) {
    if (m <= 1) return 1; __int128_t s = 0;
    for (size_t i = 0; i < n; i++) s += (__int128_t)d[i] * w[i];
    return (int64_t)(s % m) == t;
}
int64_t fsc_calculate_sum64(const int64_t* d, const int32_t* w, size_t n, int64_t m) {
    if (m <= 1) return 0; __int128_t s = 0;
    for (size_t i = 0; i < n; i++) s += (__int128_t)d[i] * (w ? w[i] : 1);
    return (int64_t)(s % m);
}
int fsc_heal_single64(const int64_t* d, const int32_t* w, size_t n, int64_t t, int64_t m, size_t c) {
    int64_t a = fsc_calculate_sum64(d, w, n, m); int64_t weight = w ? w[c] % m : 1;
    int64_t inv_w = fsc_mod_inverse(weight, m); if (inv_w == -1) return d[c];
    int64_t delta = (t - a + m) % m; int64_t r = (d[c] + (__int128_t)delta * inv_w) % m;
    return (r < 0) ? r + m : r;
}
