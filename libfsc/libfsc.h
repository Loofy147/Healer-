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

#ifndef LIBFSC_H
#define LIBFSC_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#ifndef FSC_COMMERCIAL_BUILD
#define FSC_COMMERCIAL_BUILD 0
#endif

#define FSC_MAX_K 16

/* Error Codes */
#define FSC_SUCCESS      1
#define FSC_ERR_SINGULAR 0
#define FSC_ERR_BOUNDS  -1
#define FSC_ERR_INVALID -2

int64_t fsc_calculate_sum8(const uint8_t* data, const int32_t* weights, size_t n, int64_t modulus);
uint8_t fsc_heal_single8(const uint8_t* data, const int32_t* weights, size_t n,
                        int64_t target, int64_t modulus, size_t corrupted_idx);
int64_t fsc_calculate_sum64(const int64_t* data, const int32_t* weights, size_t n, int64_t modulus);
int64_t fsc_heal_single64(const int64_t* data, const int32_t* weights, size_t n,
                         int64_t target, int64_t modulus, size_t corrupted_idx);
int fsc_heal_multi64(int64_t* data, const int32_t* weights, size_t n_data,
                    const int64_t* targets, const int64_t* moduli,
                    size_t k_faults, const size_t* corrupted_indices);
int fsc_heal_multi8(uint8_t* data, const int32_t* weights, size_t n_data,
                   const int64_t* targets, const int64_t* moduli,
                   size_t k_faults, const size_t* corrupted_indices);

size_t fsc_batch_verify_model5(const uint8_t* data, size_t n_blocks, size_t block_size, int64_t modulus, size_t* corrupted_indices);
int64_t fsc_calculate_sum8_avx2(const uint8_t* data, const int32_t* weights, size_t n, int64_t modulus);
int fsc_volume_write8(uint8_t* volume_data, size_t n_blocks, size_t block_size, size_t k_parity, int64_t modulus, const uint8_t* user_data, size_t user_data_len);
int fsc_silicon_verify_gate(const uint8_t* data, const uint8_t* rom_weights, size_t n, int64_t target, int64_t modulus);
int fsc_volume_encode8(uint8_t* volume_data, size_t n_blocks, size_t block_size, size_t k_parity, int64_t modulus);

int fsc_block_seal(uint8_t* block, size_t block_size, int64_t block_id, int64_t modulus);

int fsc_heal_erasure8(uint8_t* volume_data, size_t n_blocks, size_t block_size,
                     size_t k_parity, size_t n_lost, const size_t* bad_indices,
                     int64_t modulus);

int64_t fsc_mod_inverse(int64_t a, int64_t m);

typedef struct {
    uint8_t* buffer;
    size_t len;
    int64_t modulus;
    int64_t target;
    const int32_t* weights;
    const int32_t* weights2;
    int64_t target2;
} FSCBuffer;

void fsc_buffer_seal(FSCBuffer* b);
int fsc_buffer_verify(FSCBuffer* b);
int fsc_buffer_heal(FSCBuffer* b);
void fsc_audit_log(const char* event_type, int index, int64_t magnitude);

#ifdef __cplusplus
}
#endif

#endif
