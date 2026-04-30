/*
FSC: Forward Sector Correction - Native Core (v7.26)
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

typedef struct {
    uint8_t* buffer;
    int32_t* weights;
    size_t len;
    int64_t target;
    int64_t modulus;
} FSCBuffer;

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
    for (size_t i = 0; i < n; i++) {
        __int128_t val = data[i];
        __int128_t w = i + 1;
        s[0] += val;
        s[1] += val * w;
        s[2] += val * w * w;
        if ((i & 0xFF) == 0xFF) {
            s[0] %= modulus; s[1] %= modulus; s[2] %= modulus;
        }
    }
    s[0] %= modulus; s[1] %= modulus; s[2] %= modulus;
}

int64_t fsc_calculate_sum8(const uint8_t* data, const int32_t* weights, size_t n, int64_t modulus) {
    if (modulus <= 1) return 0;
    __int128_t sum = 0;
    if (weights) {
        #pragma omp parallel for reduction(+:sum)
        for (size_t i = 0; i < n; i++) sum += (__int128_t)data[i] * weights[i];
    } else {
        #pragma omp parallel for reduction(+:sum)
        for (size_t i = 0; i < n; i++) sum += data[i];
    }
    return (int64_t)(sum % modulus);
}

uint8_t fsc_heal_single8(const uint8_t* data, const int32_t* weights, size_t n, int64_t target, int64_t modulus, size_t corrupted_idx) {
    int64_t actual = fsc_calculate_sum8(data, weights, n, modulus);
    int64_t weight = weights ? weights[corrupted_idx] % modulus : 1;
    int64_t inv_w = fsc_mod_inverse(weight, modulus);
    if (inv_w == -1) return data[corrupted_idx];
    int64_t delta = (target - actual + modulus) % modulus;
    return (uint8_t)((data[corrupted_idx] + (__int128_t)delta * inv_w) % modulus);
}

int64_t fsc_calculate_sum64(const int64_t* data, const int32_t* weights, size_t n, int64_t modulus) {
    if (modulus <= 1) return 0;
    __int128_t sum = 0;
    for (size_t i = 0; i < n; i++) sum += (__int128_t)data[i] * (weights ? weights[i] : 1);
    return (int64_t)(sum % modulus);
}

int64_t fsc_heal_single64(const int64_t* data, const int32_t* weights, size_t n, int64_t target, int64_t modulus, size_t corrupted_idx) {
    int64_t actual = fsc_calculate_sum64(data, weights, n, modulus);
    int64_t weight = weights ? weights[corrupted_idx] % modulus : 1;
    int64_t inv_w = fsc_mod_inverse(weight, modulus);
    if (inv_w == -1) return data[corrupted_idx];
    int64_t delta = (target - actual + modulus) % modulus;
    int64_t res = (data[corrupted_idx] + (__int128_t)delta * inv_w) % modulus;
    return (res < 0) ? res + modulus : res;
}

int fsc_block_seal(uint8_t* data, size_t size, int64_t block_id, int64_t modulus) {
    if (modulus <= 1) return FSC_SUCCESS;
    __int128_t s[4]; fsc_syndromes_4way(data, size - 3, s, modulus);
    int64_t b_salt = block_id + 1;
    int64_t t[3] = {b_salt % modulus, (b_salt * 7) % modulus, (b_salt * 13) % modulus};
    int64_t rhs[3] = {(t[0] - (int64_t)s[0] + modulus) % modulus,
                      (t[1] - (int64_t)s[1] + modulus) % modulus,
                      (t[2] - (int64_t)s[2] + modulus) % modulus};
    int64_t w[3] = {size - 2, size - 1, size};
    __int128_t M[3][4];
    for(int i=0; i<3; i++) {
        M[i][0] = 1; M[i][1] = 1; M[i][2] = 1; M[i][3] = rhs[i];
        if(i==1) { M[i][0]=w[0]; M[i][1]=w[1]; M[i][2]=w[2]; }
        if(i==2) { M[i][0]=(__int128_t)w[0]*w[0]; M[i][1]=(__int128_t)w[1]*w[1]; M[i][2]=(__int128_t)w[2]*w[2]; }
    }
    for(int i=0; i<3; i++) {
        int64_t inv = fsc_mod_inverse((int64_t)(M[i][i] % modulus), modulus);
        if (inv == -1) return FSC_ERR_SINGULAR;
        for(int j=i; j<4; j++) M[i][j] = (M[i][j] * inv) % modulus;
        for(int k=0; k<3; k++) {
            if(k != i) {
                __int128_t factor = M[k][i];
                for(int j=i; j<4; j++) M[k][j] = (M[k][j] - factor * M[i][j] % modulus + modulus) % modulus;
            }
        }
    }
    data[size-3] = (uint8_t)(M[0][3] % modulus);
    data[size-2] = (uint8_t)(M[1][3] % modulus);
    data[size-1] = (uint8_t)(M[2][3] % modulus);
    return FSC_SUCCESS;
}

int fsc_block_verify(const uint8_t* data, size_t size, int64_t block_id, int64_t modulus) {
    if (modulus <= 1) return 1;
    __int128_t s[4]; fsc_syndromes_4way(data, size, s, modulus);
    int64_t b_salt = block_id + 1;
    return ((int64_t)s[0] == (int64_t)(b_salt % modulus) &&
            (int64_t)s[1] == (int64_t)((b_salt * 7) % modulus) &&
            (int64_t)s[2] == (int64_t)((b_salt * 13) % modulus));
}

size_t fsc_batch_verify_model5(const uint8_t* data, size_t n_blocks, size_t block_size, int64_t modulus, size_t* corrupted_indices) {
    size_t count = 0;
    if (modulus <= 1) return 0;
    for (size_t b = 0; b < n_blocks; b++) {
        if (!fsc_block_verify(data + b*block_size, block_size, (int64_t)b, modulus)) {
            if (corrupted_indices) corrupted_indices[count] = b;
            count++;
        }
    }
    return count;
}

int fsc_volume_encode8(uint8_t* buffer, size_t n_blocks, size_t block_size, size_t k_parity, int64_t modulus) {
    if (modulus <= 1) return FSC_SUCCESS;
    size_t n_data = n_blocks - k_parity;
    size_t d_len = block_size - 3;

    // Seal data blocks in parallel
    #pragma omp parallel for
    for (size_t i = 0; i < n_data; i++) {
        fsc_block_seal(buffer + i * block_size, block_size, (int64_t)i, modulus);
    }

    // Pre-calculate weights for each parity to avoid redundant power calculations
    // weights[j][i] = (i+1)^j % modulus
    int64_t* weights = (int64_t*)malloc(k_parity * n_data * sizeof(int64_t));
    for (size_t j = 0; j < k_parity; j++) {
        for (size_t i = 0; i < n_data; i++) {
            int64_t w = 1;
            for (size_t p = 0; p < j; p++) w = (w * (i + 1)) % modulus;
            weights[j * n_data + i] = w;
        }
    }

    // Calculate parity blocks
    #pragma omp parallel for
    for (size_t j = 0; j < k_parity; j++) {
        uint8_t* parity_block = buffer + (n_data + j) * block_size;
        memset(parity_block, 0, block_size);

        // Using a 64-bit accumulator per byte to minimize modulus operations
        // This is safe because (255 * 250 * n_data) fits in 64-bit for reasonable n_data
        int64_t* acc = (int64_t*)calloc(d_len, sizeof(int64_t));

        for (size_t i = 0; i < n_data; i++) {
            const uint8_t* data_block = buffer + i * block_size;
            int64_t w = weights[j * n_data + i];
            if (w == 0) continue;
            if (w == 1) {
                for (size_t k = 0; k < d_len; k++) acc[k] += data_block[k];
            } else {
                for (size_t k = 0; k < d_len; k++) acc[k] += (int64_t)data_block[k] * w;
            }
        }

        for (size_t k = 0; k < d_len; k++) parity_block[k] = (uint8_t)(acc[k] % modulus);
        free(acc);

        fsc_block_seal(parity_block, block_size, (int64_t)(n_data + j), modulus);
    }

    free(weights);
    return FSC_SUCCESS;
}

int fsc_volume_write8(uint8_t* buffer, size_t n_blocks, size_t block_size, size_t k_parity, int64_t modulus, const uint8_t* user_data, size_t data_len) {
    // In this native core, we assume user_data is already placed in the buffer data parts by the Python layer
    return fsc_volume_encode8(buffer, n_blocks, block_size, k_parity, modulus);
}

int fsc_heal_erasure8(uint8_t* buffer, size_t n_blocks, size_t block_size, size_t k_parity, size_t n_bad, const size_t* bad_indices, int64_t modulus) {
    return FSC_SUCCESS; // Model 5 fallback to Python for multi-block
}

void fsc_poly_mul_avx2(const int64_t* a, const int64_t* b, int64_t* res, size_t n, int64_t q) {
    if (q <= 1) return;
    #pragma omp parallel for
    for (size_t i = 0; i < n; i++) {
        __int128_t acc = 0;
        for (size_t j = 0; j < n; j++) {
            size_t idx = (i >= j) ? (i - j) : (i - j + n);
            acc += (__int128_t)a[j] * b[idx];
        }
        res[i] = (int64_t)(acc % q);
    }
}

void fsc_audit_log(const char* event, int index, int64_t magnitude) {}
int fsc_silicon_verify_gate(const uint8_t* data, const uint8_t* weights, size_t n, int64_t target, int64_t modulus) {
    if (modulus <= 1) return 1;
    __int128_t sum = 0;
    for (size_t i = 0; i < n; i++) sum += (__int128_t)data[i] * weights[i];
    return (int64_t)(sum % modulus) == target;
}
int fsc_heal_multi8(uint8_t* data, const int32_t* weights, size_t n_data, const int64_t* targets, const int64_t* moduli, size_t k, const size_t* corrupted_indices) { return 0; }
int fsc_heal_multi64(int64_t* data, const int32_t* weights, size_t n_data, const int64_t* targets, const int64_t* moduli, size_t k, const size_t* corrupted_indices) { return 0; }
