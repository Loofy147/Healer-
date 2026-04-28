#include "libfsc.h"
#include <string.h>
#include <immintrin.h>
#include <stdlib.h>
#include <stdio.h>

#ifdef _OPENMP
#include <omp.h>
#endif

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

static inline void fsc_syndromes_4way(const uint8_t* block, size_t n, __int128_t* s) {
    s[0] = 0; s[1] = 0; s[2] = 0; s[3] = 0;
    __m256i v_s0 = _mm256_setzero_si256(), v_s1 = _mm256_setzero_si256();
    __m256i v_s2 = _mm256_setzero_si256(), v_s3 = _mm256_setzero_si256();
    __m256i v_w = _mm256_set_epi32(8, 7, 6, 5, 4, 3, 2, 1);
    __m256i v_8 = _mm256_set1_epi32(8);
    size_t i = 0, iter = 0;
    for (; i + 7 < n; i += 8) {
        __m128i d8 = _mm_loadu_si64((const __m128i*)(block + i));
        __m256i d32 = _mm256_cvtepu8_epi32(d8);
        __m256i d_lo = _mm256_cvtepu32_epi64(_mm256_extracti128_si256(d32, 0));
        __m256i d_hi = _mm256_cvtepu32_epi64(_mm256_extracti128_si256(d32, 1));
        __m256i w_lo = _mm256_cvtepu32_epi64(_mm256_extracti128_si256(v_w, 0));
        __m256i w_hi = _mm256_cvtepu32_epi64(_mm256_extracti128_si256(v_w, 1));
        v_s0 = _mm256_add_epi64(v_s0, _mm256_add_epi64(d_lo, d_hi));
        __m256i p1_lo = _mm256_mul_epu32(d_lo, w_lo), p1_hi = _mm256_mul_epu32(d_hi, w_hi);
        v_s1 = _mm256_add_epi64(v_s1, _mm256_add_epi64(p1_lo, p1_hi));
        __m256i w2_lo = _mm256_mul_epu32(w_lo, w_lo), w2_hi = _mm256_mul_epu32(w_hi, w_hi);
        __m256i p2_lo = _mm256_add_epi64(_mm256_mul_epu32(d_lo, w2_lo), _mm256_slli_epi64(_mm256_mul_epu32(d_lo, _mm256_srli_epi64(w2_lo, 32)), 32));
        __m256i p2_hi = _mm256_add_epi64(_mm256_mul_epu32(d_hi, w2_hi), _mm256_slli_epi64(_mm256_mul_epu32(d_hi, _mm256_srli_epi64(w2_hi, 32)), 32));
        v_s2 = _mm256_add_epi64(v_s2, _mm256_add_epi64(p2_lo, p2_hi));
        __m256i w3_lo = _mm256_add_epi64(_mm256_mul_epu32(w2_lo, w_lo), _mm256_slli_epi64(_mm256_mul_epu32(_mm256_srli_epi64(w2_lo, 32), w_lo), 32));
        __m256i w3_hi = _mm256_add_epi64(_mm256_mul_epu32(w2_hi, w_hi), _mm256_slli_epi64(_mm256_mul_epu32(_mm256_srli_epi64(w2_hi, 32), w_hi), 32));
        __m256i p3_lo = _mm256_add_epi64(_mm256_mul_epu32(d_lo, w3_lo), _mm256_slli_epi64(_mm256_mul_epu32(d_lo, _mm256_srli_epi64(w3_lo, 32)), 32));
        __m256i p3_hi = _mm256_add_epi64(_mm256_mul_epu32(d_hi, w3_hi), _mm256_slli_epi64(_mm256_mul_epu32(d_hi, _mm256_srli_epi64(w3_hi, 32)), 32));
        v_s3 = _mm256_add_epi64(v_s3, _mm256_add_epi64(p3_lo, p3_hi));
        v_w = _mm256_add_epi32(v_w, v_8);
        if (++iter >= 256) {
            uint64_t r[16];
            _mm256_storeu_si256((__m256i*)&r[0], v_s0); _mm256_storeu_si256((__m256i*)&r[4], v_s1);
            _mm256_storeu_si256((__m256i*)&r[8], v_s2); _mm256_storeu_si256((__m256i*)&r[12], v_s3);
            s[0] += (__int128_t)r[0]+r[1]+r[2]+r[3]; s[1] += (__int128_t)r[4]+r[5]+r[6]+r[7];
            s[2] += (__int128_t)r[8]+r[9]+r[10]+r[11]; s[3] += (__int128_t)r[12]+r[13]+r[14]+r[15];
            v_s0 = v_s1 = v_s2 = v_s3 = _mm256_setzero_si256(); iter = 0;
        }
    }
    uint64_t r[16];
    _mm256_storeu_si256((__m256i*)&r[0], v_s0); _mm256_storeu_si256((__m256i*)&r[4], v_s1);
    _mm256_storeu_si256((__m256i*)&r[8], v_s2); _mm256_storeu_si256((__m256i*)&r[12], v_s3);
    s[0] += (__int128_t)r[0]+r[1]+r[2]+r[3]; s[1] += (__int128_t)r[4]+r[5]+r[6]+r[7];
    s[2] += (__int128_t)r[8]+r[9]+r[10]+r[11]; s[3] += (__int128_t)r[12]+r[13]+r[14]+r[15];
    for (; i < n; i++) {
        __int128_t v = block[i], w = i + 1;
        s[0] += v; s[1] += v * w; s[2] += v * w * w; s[3] += v * w * w * w;
    }
}

int fsc_block_seal(uint8_t* block, size_t block_size, int64_t block_id, int64_t modulus) {
    size_t d_len = block_size - 3;
    __int128_t s[4]; fsc_syndromes_4way(block, d_len, s);
    int64_t b_salt = block_id + 1;
    int64_t t[3] = { b_salt % modulus, (b_salt * 7) % modulus, (b_salt * 13) % modulus };
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
    for (int c = 0; c < 3; c++) {
        int piv = c; while (piv < 3 && M[piv][c] == 0) piv++;
        if (piv == 3) return 0;
        for (int k = c; k <= 3; k++) { __int128_t tmp = M[c][k]; M[c][k] = M[piv][k]; M[piv][k] = tmp; }
        int64_t inv = fsc_mod_inverse((int64_t)M[c][c], modulus);
        for (int k = c; k <= 3; k++) M[c][k] = (M[c][k] * inv) % modulus;
        for (int row = 0; row < 3; row++) {
            if (row != c && M[row][c] != 0) {
                __int128_t f = M[row][c];
                for (int k = c; k <= 3; k++) M[row][k] = (M[row][k] - f * M[c][k] % modulus + modulus) % modulus;
            }
        }
    }
    for (int ki = 0; ki < 3; ki++) block[d_len + ki] = (uint8_t)(M[ki][3] % 256);
    return 1;
}

int fsc_volume_encode8(uint8_t* volume_data, size_t n_blocks, size_t block_size, size_t k_parity, int64_t modulus) {
    size_t n_data = n_blocks - k_parity, d_len = block_size - 3;
    #pragma omp parallel for
    for (size_t i = 0; i < n_data; i++) fsc_block_seal(volume_data + (i * block_size), block_size, (int64_t)i, modulus);
    uint32_t* weights = (uint32_t*)malloc(k_parity * n_data * sizeof(uint32_t));
    for (size_t i = 0; i < n_data; i++) {
        uint32_t w = 1;
        for (size_t j = 0; j < k_parity; j++) {
            weights[j * n_data + i] = w;
            w = (uint32_t)(((__int128_t)w * (i + 1)) % modulus);
        }
    }
    #pragma omp parallel
    {
        uint32_t* t_acc = (uint32_t*)calloc(k_parity * 64, sizeof(uint32_t));
        #pragma omp for schedule(dynamic)
        for (size_t c_base = 0; c_base < d_len; c_base += 64) {
            size_t stripe = (c_base + 64 > d_len) ? d_len - c_base : 64;
            memset(t_acc, 0, k_parity * 64 * sizeof(uint32_t));
            for (size_t i = 0; i < n_data; i++) {
                const uint8_t* d_ptr = volume_data + (i * block_size) + c_base;
                for (size_t j = 0; j < k_parity; j++) {
                    uint32_t w = weights[j * n_data + i];
                    __m256i v_w = _mm256_set1_epi32((int)w);
                    uint32_t* p_acc = t_acc + (j * 64);
                    size_t c = 0;
                    for (; c + 7 < stripe; c += 8) {
                        __m128i d8 = _mm_loadu_si64((const __m128i*)(d_ptr + c));
                        __m256i d32 = _mm256_cvtepu8_epi32(d8);
                        __m256i v_acc = _mm256_loadu_si256((__m256i*)&p_acc[c]);
                        _mm256_storeu_si256((__m256i*)&p_acc[c], _mm256_add_epi32(v_acc, _mm256_mullo_epi32(d32, v_w)));
                    }
                    for (; c < stripe; c++) p_acc[c] += (uint32_t)d_ptr[c] * w;
                }
            }
            for (size_t j = 0; j < k_parity; j++) {
                uint8_t* p_ptr = volume_data + ((n_data + j) * block_size) + c_base;
                uint32_t* p_acc = t_acc + (j * 64);
                for (size_t c = 0; c < stripe; c++) p_ptr[c] = (uint8_t)(p_acc[c] % modulus);
            }
        }
        free(t_acc);
    }
    free(weights);
    #pragma omp parallel for
    for (size_t j = 0; j < k_parity; j++) fsc_block_seal(volume_data + ((n_data + j) * block_size), block_size, (int64_t)(n_data + j), modulus);
    return 1;
}

int fsc_volume_write8(uint8_t* volume_data, size_t n_blocks, size_t block_size, size_t k_parity, int64_t modulus, const uint8_t* user_data, size_t user_data_len) {
    size_t n_data = n_blocks - k_parity, d_len = block_size - 3;
    #pragma omp parallel for
    for (size_t i = 0; i < n_data; i++) {
        size_t off = i * d_len;
        uint8_t* b = volume_data + (i * block_size);
        if (off < user_data_len) {
            size_t len = (user_data_len - off < d_len) ? (user_data_len - off) : d_len;
            memcpy(b, user_data + off, len); if (len < d_len) memset(b + len, 0, d_len - len);
        } else memset(b, 0, d_len);
    }
    return fsc_volume_encode8(volume_data, n_blocks, block_size, k_parity, modulus);
}

int fsc_heal_erasure8(uint8_t* volume_data, size_t n_blocks, size_t block_size, size_t k_parity, size_t n_lost, const size_t* bad_indices, int64_t modulus) {
    if (n_lost == 0) return 1;
    size_t n_data = n_blocks - k_parity, d_len = block_size - 3;

    // Pre-calculate all weights for efficiency
    uint32_t* weights = (uint32_t*)malloc(k_parity * n_data * sizeof(uint32_t));
    for (size_t i = 0; i < n_data; i++) {
        uint32_t w = 1;
        for (size_t j = 0; j < k_parity; j++) {
            weights[j * n_data + i] = w;
            w = (uint32_t)(((__int128_t)w * (i+1)) % modulus);
        }
    }

    __int128_t A_inv[FSC_MAX_K][FSC_MAX_K], SysM[FSC_MAX_K][FSC_MAX_K * 2];
    for (size_t j = 0; j < n_lost; j++) {
        for (size_t ki = 0; ki < n_lost; ki++) {
            size_t bi = bad_indices[ki];
            if (bi < n_data) SysM[j][ki] = weights[j * n_data + bi];
            else SysM[j][ki] = (bi - n_data == j) ? modulus - 1 : 0;
        }
        for (size_t ki = 0; ki < n_lost; ki++) SysM[j][n_lost + ki] = (j == ki) ? 1 : 0;
    }
    for (size_t c = 0; c < n_lost; c++) {
        size_t piv = c; while (piv < n_lost && SysM[piv][c] == 0) piv++;
        if (piv == n_lost) { free(weights); return 0; }
        for (size_t k = c; k < n_lost * 2; k++) { __int128_t tmp = SysM[c][k]; SysM[c][k] = SysM[piv][k]; SysM[piv][k] = tmp; }
        int64_t inv = fsc_mod_inverse((int64_t)SysM[c][c], modulus);
        for (size_t k = c; k < n_lost * 2; k++) SysM[c][k] = (SysM[c][k] * inv) % modulus;
        for (size_t row = 0; row < n_lost; row++) {
            if (row != c && SysM[row][c] != 0) {
                __int128_t f = SysM[row][c];
                for (size_t k = c; k < n_lost * 2; k++) SysM[row][k] = (SysM[row][k] - f * SysM[c][k] % modulus + modulus) % modulus;
            }
        }
    }
    for (size_t i = 0; i < n_lost; i++) for (size_t j = 0; j < n_lost; j++) A_inv[i][j] = SysM[i][n_lost + j];

    // Multi-threaded recovery solve
    #pragma omp parallel for
    for (size_t b_idx = 0; b_idx < d_len; b_idx++) {
        __int128_t syn[FSC_MAX_K];
        for (size_t j = 0; j < n_lost; j++) {
            __int128_t s_good = 0;
            for (size_t bi = 0; bi < n_data; bi++) {
                int bad = 0; for (size_t ki = 0; ki < n_lost; ki++) if (bad_indices[ki] == bi) { bad = 1; break; }
                if (bad) continue;
                s_good = (s_good + (__int128_t)volume_data[bi * block_size + b_idx] * weights[j * n_data + bi]) % modulus;
            }
            size_t p_idx = n_data + j; int p_bad = 0; for (size_t ki = 0; ki < n_lost; ki++) if (bad_indices[ki] == p_idx) { p_bad = 1; break; }
            __int128_t rhs = p_bad ? (-s_good) : ((__int128_t)volume_data[p_idx * block_size + b_idx] - s_good);
            syn[j] = (rhs % modulus + modulus) % modulus;
        }
        for (size_t ki = 0; ki < n_lost; ki++) {
            __int128_t res = 0; for (size_t j = 0; j < n_lost; j++) res = (res + A_inv[ki][j] * syn[j]) % modulus;
            volume_data[bad_indices[ki] * block_size + b_idx] = (uint8_t)(res % 256);
        }
    }
    free(weights);
    for (size_t ki = 0; ki < n_lost; ki++) fsc_block_seal(volume_data + (bad_indices[ki] * block_size), block_size, (int64_t)bad_indices[ki], modulus);
    return 1;
}

int64_t fsc_calculate_sum8_avx2(const uint8_t* data, const int32_t* weights, size_t n, int64_t modulus) {
    if (!weights && modulus == 251 && n >= 32) {
        __int128_t s[4]; fsc_syndromes_4way(data, n, s);
        return (int64_t)(s[0] % modulus);
    }
    __int128_t sum = 0;
    if (weights) {
        // Bolt Optimization: AVX2 vectorized weighted sum
        size_t i = 0;
        __m256i v_sum = _mm256_setzero_si256();
        for (; i + 7 < n; i += 8) {
            __m128i d8 = _mm_loadu_si64((const __m128i*)(data + i));
            __m256i d32 = _mm256_cvtepu8_epi32(d8);
            __m256i w32 = _mm256_loadu_si256((const __m256i*)(weights + i));

            // Multiply 32-bit to 64-bit and accumulate
            __m256i p_even = _mm256_mul_epi32(d32, w32);
            __m256i d32_odd = _mm256_srli_si256(d32, 4);
            __m256i w32_odd = _mm256_srli_si256(w32, 4);
            __m256i p_odd = _mm256_mul_epi32(d32_odd, w32_odd);

            v_sum = _mm256_add_epi64(v_sum, _mm256_add_epi64(p_even, p_odd));

            if ((i & 0x7FF) == 0x7F8) {
                uint64_t r[4]; _mm256_storeu_si256((__m256i*)r, v_sum);
                sum += (__int128_t)r[0] + r[1] + r[2] + r[3];
                v_sum = _mm256_setzero_si256();
            }
        }
        uint64_t r[4]; _mm256_storeu_si256((__m256i*)r, v_sum);
        sum += (__int128_t)r[0] + r[1] + r[2] + r[3];
        for (; i < n; i++) sum += (__int128_t)data[i] * weights[i];
    } else {
        // Bolt Optimization: AVX2 vectorized unweighted sum using _mm256_sad_epu8
        size_t i = 0;
        __m256i v_sum = _mm256_setzero_si256();
        __m256i v_zero = _mm256_setzero_si256();
        for (; i + 31 < n; i += 32) {
            __m256i d = _mm256_loadu_si256((const __m256i*)(data + i));
            v_sum = _mm256_add_epi64(v_sum, _mm256_sad_epu8(d, v_zero));
            if ((i & 0xFFFF) == 0xFFE0) {
                uint64_t r[4]; _mm256_storeu_si256((__m256i*)r, v_sum);
                sum += (__int128_t)r[0] + r[1] + r[2] + r[3];
                v_sum = _mm256_setzero_si256();
            }
        }
        uint64_t r[4]; _mm256_storeu_si256((__m256i*)r, v_sum);
        sum += (__int128_t)r[0] + r[1] + r[2] + r[3];
        for (; i < n; i++) sum += data[i];
    }
    return (modulus > 0) ? (int64_t)((sum % modulus + modulus) % modulus) : (int64_t)sum;
}

int64_t fsc_calculate_sum8(const uint8_t* data, const int32_t* weights, size_t n, int64_t modulus) {
    return fsc_calculate_sum8_avx2(data, weights, n, modulus);
}

uint8_t fsc_heal_single8(const uint8_t* data, const int32_t* weights, size_t n, int64_t target, int64_t modulus, size_t corrupted_idx) {
    // Bolt Optimization: Use vectorized sum and O(1) residual
    int64_t actual = fsc_calculate_sum8(data, weights, n, modulus);
    int64_t weight = weights ? weights[corrupted_idx] % modulus : 1;
    int64_t inv_w = fsc_mod_inverse(weight, modulus);
    int64_t delta = (target - actual + modulus) % modulus;
    return (uint8_t)((data[corrupted_idx] + (__int128_t)delta * inv_w) % modulus);
}

size_t fsc_batch_verify_model5(const uint8_t* data, size_t n_blocks, size_t block_size, int64_t modulus, size_t* corrupted_indices) {
    size_t count = 0;
    #pragma omp parallel
    {
        #pragma omp for
        for (size_t b = 0; b < n_blocks; b++) {
            const uint8_t* block = data + (b * block_size);
            __int128_t s[4]; fsc_syndromes_4way(block, block_size, s);
            int64_t b_salt = (int64_t)b + 1;
            if ((s[0]%modulus) != (b_salt%modulus) || (s[1]%modulus) != ((b_salt*7)%modulus) || (s[2]%modulus) != ((b_salt*13)%modulus)) {
                #pragma omp critical
                { if (corrupted_indices) corrupted_indices[count++] = b; }
            }
        }
    }
    return count;
}

int64_t fsc_calculate_sum64(const int64_t* data, const int32_t* weights, size_t n, int64_t modulus) {
    // Bolt Optimization: AVX2 vectorized sum64
    __int128_t sum = 0;
    size_t i = 0;
    __m256i v_sum = _mm256_setzero_si256();
    for (; i + 3 < n; i += 4) {
        __m256i d = _mm256_loadu_si256((const __m256i*)(data + i));
        if (weights) {
            __m256i w32 = _mm256_loadu_si256((const __m256i*)(weights + i));
            __m256i w64_lo = _mm256_cvtepi32_epi64(_mm256_extracti128_si256(w32, 0));
            __m256i w64_hi = _mm256_cvtepi32_epi64(_mm256_extracti128_si256(w32, 1)); // This is actually for 8 elements, we only need 4
            // Correcting: load 4 weights
            __m128i w128 = _mm_loadu_si128((const __m128i*)(weights + i));
            __m256i w64 = _mm256_cvtepi32_epi64(w128);

            // mul_epi32 only does even lanes, need manual interleaving or mullo/mulhi
            // For int64 multiplication in AVX2, we don't have a single instruction for full 64x64 -> 128
            // But we know weights are 32-bit.
            __m256i p_lo = _mm256_mul_epu32(d, w64);
            __m256i d_hi = _mm256_srli_si256(d, 4);
            __m256i w_hi = _mm256_srli_si256(w64, 4);
            __m256i p_hi = _mm256_mul_epu32(d_hi, w_hi);
            // This is complex. Let's stick to scalar for weights in sum64 for now unless it's a hot path.
            // Actually, sum64 unweighted is easy.
            for (size_t j = 0; j < 4; j++) sum += (__int128_t)data[i+j] * (weights ? weights[i+j] : 1);
        } else {
            v_sum = _mm256_add_epi64(v_sum, d);
            if ((i & 0x7FC) == 0x7FC) {
                uint64_t r[4]; _mm256_storeu_si256((__m256i*)r, v_sum);
                sum += (__int128_t)r[0] + r[1] + r[2] + r[3];
                v_sum = _mm256_setzero_si256();
            }
        }
    }
    if (!weights) {
        uint64_t r[4]; _mm256_storeu_si256((__m256i*)r, v_sum);
        sum += (__int128_t)r[0] + r[1] + r[2] + r[3];
    }
    for (; i < n; i++) sum += (__int128_t)data[i] * (weights ? weights[i] : 1);
    return (int64_t)((sum % modulus + modulus) % modulus);
}

int64_t fsc_heal_single64(const int64_t* data, const int32_t* weights, size_t n, int64_t target, int64_t modulus, size_t corrupted_idx) {
    int64_t actual = fsc_calculate_sum64(data, weights, n, modulus);
    int64_t weight = weights ? weights[corrupted_idx] % modulus : 1;
    int64_t inv_w = fsc_mod_inverse(weight, modulus);
    int64_t delta = (target - actual + modulus) % modulus;
    int64_t res = (data[corrupted_idx] + (__int128_t)delta * inv_w) % modulus;
    return (res < 0) ? res + modulus : res;
}

int fsc_heal_multi64(int64_t* data, const int32_t* weights, size_t n_data, const int64_t* targets, const int64_t* moduli, size_t k, const size_t* corrupted_indices) {
    int64_t p = moduli[0]; __int128_t M[FSC_MAX_K][FSC_MAX_K + 1];
    // Bolt Optimization: Pre-calculate sums using optimized path and remove internal loop branch
    __int128_t* actual_sums = malloc(k * sizeof(__int128_t));
    for (size_t i = 0; i < k; i++) {
        actual_sums[i] = fsc_calculate_sum64(data, weights ? weights + (i * n_data) : NULL, n_data, p);
        __int128_t s = actual_sums[i];
        for (size_t ki = 0; ki < k; ki++) {
            size_t ci = corrupted_indices[ki];
            __int128_t w = weights ? weights[i * n_data + ci] % p : 1;
            if (w < 0) w += p;
            s = (s - (data[ci] % p * w) % p + p) % p;
            M[i][ki] = w;
        }
        M[i][k] = (targets[i] - s + p) % p;
    }
    free(actual_sums);
    for (size_t c = 0; c < k; c++) {
        size_t piv = c; while (piv < k && M[piv][c] == 0) piv++;
        if (piv == k) return 0;
        for (size_t j = c; j <= k; j++) { __int128_t t_v = M[c][j]; M[c][j] = M[piv][j]; M[piv][j] = t_v; }
        int64_t inv = fsc_mod_inverse((int64_t)M[c][c], p);
        for (size_t j = c; j <= k; j++) M[c][j] = (M[c][j] * inv) % p;
        for (size_t row = 0; row < k; row++) {
            if (row != c && M[row][c] != 0) {
                __int128_t f = M[row][c];
                for (size_t j = c; j <= k; j++) M[row][j] = (M[row][j] - f * M[c][j] % p + p) % p;
            }
        }
    }
    for (size_t ki = 0; ki < k; ki++) data[corrupted_indices[ki]] = (int64_t)M[ki][k];
    return 1;
}

int fsc_heal_multi8(uint8_t* data, const int32_t* weights, size_t n_data, const int64_t* targets, const int64_t* moduli, size_t k, const size_t* corrupted_indices) {
    int64_t p = moduli[0]; __int128_t M[FSC_MAX_K][FSC_MAX_K + 1];
    // Bolt Optimization: Pre-calculate sums using optimized path and remove internal loop branch
    __int128_t* actual_sums = malloc(k * sizeof(__int128_t));
    for (size_t i = 0; i < k; i++) {
        actual_sums[i] = fsc_calculate_sum8(data, weights ? weights + (i * n_data) : NULL, n_data, p);
        __int128_t s = actual_sums[i];
        for (size_t ki = 0; ki < k; ki++) {
            size_t ci = corrupted_indices[ki];
            __int128_t w = weights ? weights[i * n_data + ci] % p : 1;
            if (w < 0) w += p;
            s = (s - (data[ci] * w) % p + p) % p;
            M[i][ki] = w;
        }
        M[i][k] = (targets[i] - s + p) % p;
    }
    free(actual_sums);
    for (size_t c = 0; c < k; c++) {
        size_t piv = c; while (piv < k && M[piv][c] == 0) piv++;
        if (piv == k) return 0;
        for (size_t j = c; j <= k; j++) { __int128_t t_v = M[c][j]; M[c][j] = M[piv][j]; M[piv][j] = t_v; }
        int64_t inv = fsc_mod_inverse((int64_t)M[c][c], p);
        for (size_t j = c; j <= k; j++) M[c][j] = (M[c][j] * inv) % p;
        for (size_t row = 0; row < k; row++) {
            if (row != c && M[row][c] != 0) {
                __int128_t f = M[row][c];
                for (size_t j = c; j <= k; j++) M[row][j] = (M[row][j] - f * M[c][j] % p + p) % p;
            }
        }
    }
    for (size_t ki = 0; ki < k; ki++) data[corrupted_indices[ki]] = (uint8_t)(M[ki][k] % 256);
    return 1;
}

void fsc_buffer_seal(FSCBuffer* b) { b->target = fsc_calculate_sum8(b->buffer, b->weights, b->len, b->modulus); }
int fsc_buffer_verify(FSCBuffer* b) { return fsc_calculate_sum8(b->buffer, b->weights, b->len, b->modulus) == b->target; }
int fsc_buffer_heal(FSCBuffer* b) {
    int64_t actual = fsc_calculate_sum8(b->buffer, b->weights, b->len, b->modulus);
    if (actual == b->target) return -2;
    __int128_t s = (b->target - actual + b->modulus) % b->modulus;
    for (size_t i = 0; i < b->len; i++) {
        int64_t w = b->weights ? b->weights[i] % b->modulus : 1;
        int64_t inv_w = fsc_mod_inverse(w, b->modulus); __int128_t delta = (s * inv_w) % b->modulus;
        uint8_t orig = b->buffer[i]; b->buffer[i] = (uint8_t)((orig + delta) % b->modulus);
        if (fsc_buffer_verify(b)) return (int)i;
        b->buffer[i] = orig;
    }
    return -1;
}

void fsc_audit_log(const char* event_type, int index, int64_t magnitude) {}
int fsc_silicon_verify_gate(const uint8_t* data, const uint8_t* rom_weights, size_t n, int64_t target, int64_t modulus) {
    __int128_t sum = 0;
    #pragma omp parallel for reduction(+:sum)
    for (size_t i = 0; i < n; i++) sum += (__int128_t)data[i] * rom_weights[i];
    return (int64_t)(sum % modulus) == target;
}
