/**
 * FSC: Forward Sector Correction
 * Optimized Native Core v7.2
 */

#include "libfsc.h"
#include <string.h>
#include <immintrin.h>
#include <stdlib.h>

int64_t fsc_mod_inverse(int64_t a, int64_t m) {
    if (m <= 1) return 0;
    int64_t m0 = m, t, q, x0 = 0, x1 = 1;
    if (a < 0) a = (a % m) + m;
    a %= m;
    if (a == 0) return 0;
    while (a > 1) {
        if (m == 0) return 0;
        q = a / m; t = m; m = a % m; a = t;
        t = x0; x0 = x1 - q * x0; x1 = t;
    }
    return (x1 < 0) ? x1 + m0 : x1;
}

/**
 * Optimized syndrome calculation using AVX2.
 */
static inline void fsc_calculate_syndromes_avx2(const uint8_t* block, size_t n, __int128_t* s) {
    __m256i v_s0 = _mm256_setzero_si256();
    __m256i v_s1 = _mm256_setzero_si256();
    __m256i v_s2 = _mm256_setzero_si256();

    size_t i = 0;
    for (; i <= n - 8; i += 8) {
        __m128i v_8 = _mm_loadu_si64((const __m128i*)(block + i));
        __m256i v_32 = _mm256_cvtepu8_epi32(v_8);

        uint32_t w_base = (uint32_t)(i + 1);
        __m256i v_w = _mm256_set_epi32(w_base+7, w_base+6, w_base+5, w_base+4, w_base+3, w_base+2, w_base+1, w_base);
        __m256i v_w2 = _mm256_mullo_epi32(v_w, v_w);

        v_s0 = _mm256_add_epi64(v_s0, _mm256_cvtepu32_epi64(_mm256_extracti128_si256(v_32, 0)));
        v_s0 = _mm256_add_epi64(v_s0, _mm256_cvtepu32_epi64(_mm256_extracti128_si256(v_32, 1)));

        __m256i p1 = _mm256_mullo_epi32(v_32, v_w);
        v_s1 = _mm256_add_epi64(v_s1, _mm256_cvtepu32_epi64(_mm256_extracti128_si256(p1, 0)));
        v_s1 = _mm256_add_epi64(v_s1, _mm256_cvtepu32_epi64(_mm256_extracti128_si256(p1, 1)));

        __m256i p2 = _mm256_mullo_epi32(v_32, v_w2);
        v_s2 = _mm256_add_epi64(v_s2, _mm256_cvtepu32_epi64(_mm256_extracti128_si256(p2, 0)));
        v_s2 = _mm256_add_epi64(v_s2, _mm256_cvtepu32_epi64(_mm256_extracti128_si256(p2, 1)));
    }

    uint64_t r0[4], r1[4], r2[4];
    _mm256_storeu_si256((__m256i*)r0, v_s0);
    _mm256_storeu_si256((__m256i*)r1, v_s1);
    _mm256_storeu_si256((__m256i*)r2, v_s2);

    s[0] = 0; s[1] = 0; s[2] = 0;
    for (int k = 0; k < 4; k++) { s[0] += r0[k]; s[1] += r1[k]; s[2] += r2[k]; }
    for (; i < n; i++) {
        uint64_t v = block[i], w = i + 1;
        s[0] += v; s[1] += v * w; s[2] += v * w * w;
    }
}

int64_t fsc_calculate_sum8_avx2(const uint8_t* data, const int32_t* weights, size_t n, int64_t modulus) {
    if (weights || modulus != 251) return fsc_calculate_sum8(data, weights, n, modulus);
    __int128_t s[3]; fsc_calculate_syndromes_avx2(data, n, s);
    return (int64_t)(s[0] % modulus);
}

int64_t fsc_calculate_sum8(const uint8_t* data, const int32_t* weights, size_t n, int64_t modulus) {
    if (!weights && modulus == 251 && n >= 32) return fsc_calculate_sum8_avx2(data, weights, n, modulus);
    __int128_t sum = 0;
    if (weights) for (size_t i = 0; i < n; i++) sum += (__int128_t)data[i] * weights[i];
    else for (size_t i = 0; i < n; i++) sum += data[i];
    return (modulus > 0) ? (int64_t)((sum % modulus + modulus) % modulus) : (int64_t)sum;
}

uint8_t fsc_heal_single8(const uint8_t* data, const int32_t* weights, size_t n, int64_t target, int64_t modulus, size_t corrupted_idx) {
    __int128_t s = 0;
    for (size_t i = 0; i < n; i++) if (i != corrupted_idx) s += (__int128_t)data[i] * (weights ? weights[i] : 1);
    s %= modulus;
    int64_t rhs = (target - (int64_t)s + modulus) % modulus;
    int64_t w = weights ? weights[corrupted_idx] % modulus : 1;
    return (uint8_t)(((__int128_t)rhs * fsc_mod_inverse(w, modulus)) % modulus);
}

int64_t fsc_calculate_sum64(const int64_t* data, const int32_t* weights, size_t n, int64_t modulus) {
    __int128_t sum = 0;
    for (size_t i = 0; i < n; i++) sum += (__int128_t)data[i] * (weights ? weights[i] : 1);
    return (int64_t)((sum % modulus + modulus) % modulus);
}

int64_t fsc_heal_single64(const int64_t* data, const int32_t* weights, size_t n, int64_t target, int64_t modulus, size_t corrupted_idx) {
    __int128_t s = 0;
    for (size_t i = 0; i < n; i++) if (i != corrupted_idx) s += (__int128_t)data[i] * (weights ? weights[i] : 1);
    s %= modulus;
    int64_t rhs = (target - (int64_t)s + modulus) % modulus;
    int64_t w = weights ? weights[corrupted_idx] % modulus : 1;
    return (int64_t)(((__int128_t)rhs * fsc_mod_inverse(w, modulus)) % modulus);
}

int fsc_heal_multi64(int64_t* data, const int32_t* weights, size_t n_data, const int64_t* targets, const int64_t* moduli, size_t k, const size_t* corrupted_indices) {
    if (k == 0 || k > FSC_MAX_K) return FSC_ERR_BOUNDS;
    int64_t p = moduli[0]; __int128_t M[FSC_MAX_K][FSC_MAX_K + 1];
    for (size_t i = 0; i < k; i++) {
        __int128_t s = 0;
        for (size_t j = 0; j < n_data; j++) {
            int bad = 0; for (size_t ki = 0; ki < k; ki++) if (corrupted_indices[ki] == j) { bad = 1; break; }
            if (bad) continue;
            __int128_t v = data[j] % p; if (v < 0) v += p;
            __int128_t w = weights ? weights[i * n_data + j] % p : 1; if (w < 0) w += p;
            s = (s + v * w) % p;
        }
        M[i][k] = (targets[i] - s + p) % p;
        for (size_t ki = 0; ki < k; ki++) {
            __int128_t w = weights ? weights[i * n_data + corrupted_indices[ki]] % p : 1;
            if (w < 0) w += p; M[i][ki] = w;
        }
    }
    for (size_t col = 0; col < k; col++) {
        size_t piv = col; while (piv < k && M[piv][col] == 0) piv++;
        if (piv == k) return FSC_ERR_SINGULAR;
        for (size_t j = col; j <= k; j++) { __int128_t t = M[col][j]; M[col][j] = M[piv][j]; M[piv][j] = t; }
        int64_t inv = fsc_mod_inverse((int64_t)M[col][col], p);
        for (size_t j = col; j <= k; j++) M[col][j] = (M[col][j] * inv) % p;
        for (size_t row = 0; row < k; row++) {
            if (row != col && M[row][col] != 0) {
                __int128_t f = M[row][col];
                for (size_t j = col; j <= k; j++) M[row][j] = (M[row][j] - f * M[col][j] % p + p) % p;
            }
        }
    }
    for (size_t ki = 0; ki < k; ki++) data[corrupted_indices[ki]] = (int64_t)M[ki][k];
    return FSC_SUCCESS;
}

int fsc_heal_multi8(uint8_t* data, const int32_t* weights, size_t n_data, const int64_t* targets, const int64_t* moduli, size_t k, const size_t* corrupted_indices) {
    if (k == 0 || k > FSC_MAX_K) return FSC_ERR_BOUNDS;
    int64_t p = moduli[0]; __int128_t M[FSC_MAX_K][FSC_MAX_K + 1];
    for (size_t i = 0; i < k; i++) {
        __int128_t s = 0;
        for (size_t j = 0; j < n_data; j++) {
            int bad = 0; for (size_t ki = 0; ki < k; ki++) if (corrupted_indices[ki] == j) { bad = 1; break; }
            if (bad) continue;
            __int128_t v = data[j] % p;
            __int128_t w = weights ? weights[i * n_data + j] % p : 1; if (w < 0) w += p;
            s = (s + v * w) % p;
        }
        M[i][k] = (targets[i] - s + p) % p;
        for (size_t ki = 0; ki < k; ki++) {
            __int128_t w = weights ? weights[i * n_data + corrupted_indices[ki]] % p : 1;
            if (w < 0) w += p; M[i][ki] = w;
        }
    }
    for (size_t col = 0; col < k; col++) {
        size_t piv = col; while (piv < k && M[piv][col] == 0) piv++;
        if (piv == k) return FSC_ERR_SINGULAR;
        for (size_t j = col; j <= k; j++) { __int128_t t = M[col][j]; M[col][j] = M[piv][j]; M[piv][j] = t; }
        int64_t inv = fsc_mod_inverse((int64_t)M[col][col], p);
        for (size_t j = col; j <= k; j++) M[col][j] = (M[col][j] * inv) % p;
        for (size_t row = 0; row < k; row++) {
            if (row != col && M[row][col] != 0) {
                __int128_t f = M[row][col];
                for (size_t j = col; j <= k; j++) M[row][j] = (M[row][j] - f * M[col][j] % p + p) % p;
            }
        }
    }
    for (size_t ki = 0; ki < k; ki++) data[corrupted_indices[ki]] = (uint8_t)(M[ki][k] % 256);
    return FSC_SUCCESS;
}

size_t fsc_batch_verify_model5(const uint8_t* data, size_t n_blocks, size_t block_size, int64_t modulus, size_t* corrupted_indices) {
    size_t count = 0;
    for (size_t b = 0; b < n_blocks; b++) {
        const uint8_t* block = data + (b * block_size);
        __int128_t s[3];
        if (modulus == 251) fsc_calculate_syndromes_avx2(block, block_size, s);
        else {
            s[0] = s[1] = s[2] = 0;
            for (size_t i = 0; i < block_size; i++) {
                __int128_t v = block[i], w = i + 1;
                s[0] += v; s[1] += v * w; s[2] += v * w * w;
            }
        }
        s[0] %= modulus; s[1] %= modulus; s[2] %= modulus;
        if (s[0] != (b % modulus) || s[1] != ((b * 7) % modulus) || s[2] != ((b * 13) % modulus)) {
            if (corrupted_indices) corrupted_indices[count] = b;
            count++;
        }
    }
    return count;
}

int fsc_block_seal(uint8_t* block, size_t block_size, int64_t block_id, int64_t modulus) {
    size_t d_len = block_size - 3;
    __int128_t s[3];
    if (modulus == 251) fsc_calculate_syndromes_avx2(block, d_len, s);
    else {
        s[0] = s[1] = s[2] = 0;
        for (size_t i = 0; i < d_len; i++) {
            __int128_t v = block[i], w = i + 1;
            s[0] += v; s[1] += v * w; s[2] += v * w * w;
        }
    }
    int64_t t[3] = { block_id % modulus, (block_id * 7) % modulus, (block_id * 13) % modulus };
    __int128_t rhs[3]; for (int i = 0; i < 3; i++) rhs[i] = (t[i] - (s[i] % modulus) + modulus) % modulus;
    __int128_t M[3][4];
    for (int i = 0; i < 3; i++) {
        M[i][3] = rhs[i];
        for (int ki = 0; ki < 3; ki++) {
            size_t w_idx = block_size - 2 + ki;
            __int128_t w = 1; for (int p = 0; p < i; p++) w = (w * w_idx) % modulus;
            M[i][ki] = w;
        }
    }
    for (int col = 0; col < 3; col++) {
        int piv = col; while (piv < 3 && M[piv][col] == 0) piv++;
        if (piv == 3) return FSC_ERR_SINGULAR;
        for (int k = col; k <= 3; k++) { __int128_t t = M[col][k]; M[col][k] = M[piv][k]; M[piv][k] = t; }
        int64_t inv = fsc_mod_inverse((int64_t)M[col][col], modulus);
        for (int k = col; k <= 3; k++) M[col][k] = (M[col][k] * inv) % modulus;
        for (int row = 0; row < 3; row++) {
            if (row != col && M[row][col] != 0) {
                __int128_t f = M[row][col];
                for (int k = col; k <= 3; k++) M[row][k] = (M[row][k] - f * M[col][k] % modulus + modulus) % modulus;
            }
        }
    }
    for (int ki = 0; ki < 3; ki++) block[d_len + ki] = (uint8_t)(M[ki][3] % 256);
    return FSC_SUCCESS;
}

int fsc_volume_encode8(uint8_t* volume_data, size_t n_blocks, size_t block_size, size_t k_parity, int64_t modulus) {
    size_t n_data = n_blocks - k_parity, d_len = block_size - 3;
    for (size_t i = 0; i < n_data; i++) fsc_block_seal(volume_data + (i * block_size), block_size, i, modulus);
    uint32_t* accum = (uint32_t*)malloc(d_len * sizeof(uint32_t));
    if (!accum) return FSC_ERR_INVALID;
    for (size_t j = 0; j < k_parity; j++) {
        size_t p_idx = n_data + j; memset(accum, 0, d_len * sizeof(uint32_t));
        for (size_t i = 0; i < n_data; i++) {
            __int128_t w = 1; for (size_t p = 0; p < j; p++) w = (w * (i + 1)) % modulus;
            uint32_t iw = (uint32_t)w; const uint8_t* d_block = volume_data + (i * block_size);
            size_t c = 0; __m256i v_iw = _mm256_set1_epi16((short)iw);
            for (; c <= d_len - 16; c += 16) {
                __m128i v_8 = _mm_loadu_si128((const __m128i*)(d_block + c));
                __m256i v_16 = _mm256_cvtepu8_epi16(v_8);
                __m256i v_prod = _mm256_mullo_epi16(v_16, v_iw);
                __m256i v_prod_lo = _mm256_cvtepu16_epi32(_mm256_extracti128_si256(v_prod, 0));
                __m256i v_prod_hi = _mm256_cvtepu16_epi32(_mm256_extracti128_si256(v_prod, 1));
                __m256i v_acc_lo = _mm256_loadu_si256((__m256i*)(accum + c));
                __m256i v_acc_hi = _mm256_loadu_si256((__m256i*)(accum + c + 8));
                _mm256_storeu_si256((__m256i*)(accum + c), _mm256_add_epi32(v_acc_lo, v_prod_lo));
                _mm256_storeu_si256((__m256i*)(accum + c + 8), _mm256_add_epi32(v_acc_hi, v_prod_hi));
            }
            for (; c < d_len; c++) accum[c] += (uint32_t)d_block[c] * iw;
        }
        uint8_t* p_block = volume_data + (p_idx * block_size);
        for (size_t c = 0; c < d_len; c++) p_block[c] = (uint8_t)(accum[c] % modulus);
        fsc_block_seal(p_block, block_size, p_idx, modulus);
    }
    free(accum); return FSC_SUCCESS;
}

int fsc_heal_erasure8(uint8_t* volume_data, size_t n_blocks, size_t block_size, size_t k_parity, size_t n_lost, const size_t* bad_indices, int64_t modulus) {
    if (n_lost == 0) return FSC_SUCCESS;
    size_t n_data = n_blocks - k_parity, d_len = block_size - 3;
    __int128_t A_inv[FSC_MAX_K][FSC_MAX_K], M[FSC_MAX_K][FSC_MAX_K * 2];
    for (size_t j = 0; j < n_lost; j++) {
        for (size_t ki = 0; ki < n_lost; ki++) {
            size_t bi = bad_indices[ki];
            if (bi < n_data) {
                __int128_t w = 1; for (size_t p = 0; p < j; p++) w = (w * (bi + 1)) % modulus;
                M[j][ki] = w;
            } else M[j][ki] = (bi - n_data == j) ? modulus - 1 : 0;
        }
        for (size_t ki = 0; ki < n_lost; ki++) M[j][n_lost + ki] = (j == ki) ? 1 : 0;
    }
    for (size_t col = 0; col < n_lost; col++) {
        size_t piv = col; while (piv < n_lost && M[piv][col] == 0) piv++;
        if (piv == n_lost) return FSC_ERR_SINGULAR;
        for (size_t j = col; j < n_lost * 2; j++) { __int128_t t = M[col][j]; M[col][j] = M[piv][j]; M[piv][j] = t; }
        int64_t inv = fsc_mod_inverse((int64_t)M[col][col], modulus);
        for (size_t j = col; j < n_lost * 2; j++) M[col][j] = (M[col][j] * inv) % modulus;
        for (size_t row = 0; row < n_lost; row++) {
            if (row != col && M[row][col] != 0) {
                __int128_t f = M[row][col];
                for (size_t j = col; j < n_lost * 2; j++) M[row][j] = (M[row][j] - f * M[col][j] % modulus + modulus) % modulus;
            }
        }
    }
    for (size_t i = 0; i < n_lost; i++) for (size_t j = 0; j < n_lost; j++) A_inv[i][j] = M[i][n_lost + j];
    for (size_t col = 0; col < d_len; col++) {
        __int128_t syn[FSC_MAX_K];
        for (size_t j = 0; j < n_lost; j++) {
            __int128_t s_good = 0;
            for (size_t bi = 0; bi < n_data; bi++) {
                int bad = 0; for (size_t ki = 0; ki < n_lost; ki++) if (bad_indices[ki] == bi) { bad = 1; break; }
                if (bad) continue;
                __int128_t w = 1; for (size_t p = 0; p < j; p++) w = (w * (bi + 1)) % modulus;
                s_good = (s_good + (__int128_t)volume_data[bi * block_size + col] * w) % modulus;
            }
            size_t p_idx = n_data + j; int p_bad = 0; for (size_t ki = 0; ki < n_lost; ki++) if (bad_indices[ki] == p_idx) { p_bad = 1; break; }
            __int128_t rhs = p_bad ? (-s_good) : ((__int128_t)volume_data[p_idx * block_size + col] - s_good);
            syn[j] = (rhs % modulus + modulus) % modulus;
        }
        for (size_t ki = 0; ki < n_lost; ki++) {
            __int128_t res = 0; for (size_t j = 0; j < n_lost; j++) res = (res + A_inv[ki][j] * syn[j]) % modulus;
            volume_data[bad_indices[ki] * block_size + col] = (uint8_t)(res % 256);
        }
    }
    for (size_t ki = 0; ki < n_lost; ki++) fsc_block_seal(volume_data + (bad_indices[ki] * block_size), block_size, bad_indices[ki], modulus);
    return FSC_SUCCESS;
}

void fsc_buffer_seal(FSCBuffer* b) {
    b->target = fsc_calculate_sum8(b->buffer, b->weights, b->len, b->modulus);
    if (b->weights2) b->target2 = fsc_calculate_sum8(b->buffer, b->weights2, b->len, b->modulus);
}

int fsc_buffer_verify(FSCBuffer* b) {
    if (fsc_calculate_sum8(b->buffer, b->weights, b->len, b->modulus) != b->target) return 0;
    if (b->weights2 && fsc_calculate_sum8(b->buffer, b->weights2, b->len, b->modulus) != b->target2) return 0;
    return 1;
}

int fsc_buffer_heal(FSCBuffer* b) {
    int64_t actual1 = fsc_calculate_sum8(b->buffer, b->weights, b->len, b->modulus);
    if (actual1 == b->target) return -2;
    __int128_t s1 = (b->target - actual1 + b->modulus) % b->modulus;
    if (b->weights2) {
        int64_t actual2 = fsc_calculate_sum8(b->buffer, b->weights2, b->len, b->modulus);
        __int128_t s2 = (b->target2 - actual2 + b->modulus) % b->modulus;
        for (size_t i = 0; i < b->len; i++) {
            int64_t w1 = b->weights ? b->weights[i] % b->modulus : 1, w2 = b->weights2[i] % b->modulus;
            int64_t inv_w1 = fsc_mod_inverse(w1, b->modulus); __int128_t delta = (s1 * inv_w1) % b->modulus;
            if ((delta * w2) % b->modulus == s2) {
                uint8_t orig = b->buffer[i]; b->buffer[i] = (uint8_t)((orig + delta) % b->modulus);
                if (fsc_buffer_verify(b)) return (int)i;
                b->buffer[i] = orig;
            }
        }
    } else {
        for (size_t i = 0; i < b->len; i++) {
            uint8_t rec = fsc_heal_single8(b->buffer, b->weights, b->len, b->target, b->modulus, i);
            uint8_t orig = b->buffer[i]; b->buffer[i] = rec;
            if (fsc_buffer_verify(b)) return (int)i;
            b->buffer[i] = orig;
        }
    }
    return -1;
}

void fsc_audit_log(const char* event_type, int index, int64_t magnitude) {
#if FSC_COMMERCIAL_BUILD
    printf("[COMMERCIAL-AUDIT] %s | %d | %ld\n", event_type, index, magnitude);
#endif
}
