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

/**
 * libfsc.h - Bare-metal Forward Sector Correction (FSC) Library
 *
 * Provides zero-dependency, non-allocating, self-healing data primitives.
 */

#ifndef LIBFSC_H
#define LIBFSC_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/*
 * FSC_COMMERCIAL_BUILD: Toggle for advanced enterprise features.
 * When disabled (default), only core algebraic healing is available.
 */
#ifndef FSC_COMMERCIAL_BUILD
#define FSC_COMMERCIAL_BUILD 0
#endif

#define FSC_MAX_K 16

/* Error Codes */
#define FSC_SUCCESS      1
#define FSC_ERR_SINGULAR 0
#define FSC_ERR_BOUNDS  -1
#define FSC_ERR_INVALID -2

/**
 * fsc_calculate_sum8: Calculates modular sum of a uint8_t buffer.
 * weights can be NULL (defaults to 1).
 */
int64_t fsc_calculate_sum8(const uint8_t* data, const int32_t* weights, size_t n, int64_t modulus);

/**
 * fsc_heal_single8: Recovers one corrupted byte.
 */
uint8_t fsc_heal_single8(const uint8_t* data, const int32_t* weights, size_t n,
                        int64_t target, int64_t modulus, size_t corrupted_idx);

/**
 * fsc_calculate_sum64: Calculates modular sum of an int64_t array.
 */
int64_t fsc_calculate_sum64(const int64_t* data, const int32_t* weights, size_t n, int64_t modulus);

/**
 * fsc_heal_single64: Recovers one corrupted int64_t.
 */
int64_t fsc_heal_single64(const int64_t* data, const int32_t* weights, size_t n,
                         int64_t target, int64_t modulus, size_t corrupted_idx);

/**
 * fsc_heal_multi64: Recovers K corrupted int64_t fields.
 */
int fsc_heal_multi64(int64_t* data, const int32_t* weights, size_t n_data,
                    const int64_t* targets, const int64_t* moduli,
                    size_t k_faults, const size_t* corrupted_indices);

/**
 * fsc_mod_inverse: Extended Euclidean Algorithm.
 */
int64_t fsc_mod_inverse(int64_t a, int64_t m);

/* Immortal Buffer API */

typedef struct {
    uint8_t* buffer;
    size_t len;
    int64_t modulus;
    int64_t target;
    const int32_t* weights;
    const int32_t* weights2;
    int64_t target2;
} FSCBuffer;

/**
 * fsc_buffer_seal: Calculates and sets the targets for a buffer.
 */
void fsc_buffer_seal(FSCBuffer* b);

/**
 * fsc_buffer_verify: Checks integrity. Returns 1 if OK.
 */
int fsc_buffer_verify(FSCBuffer* b);

/**
 * fsc_buffer_heal: Localizes and heals a single-byte corruption.
 * Returns index of healed byte, or -1 if failed.
 */
int fsc_buffer_heal(FSCBuffer* b);

/**
 * fsc_audit_log: Advanced forensic logging for data corruption events.
 * (Commercial License Required)
 */
void fsc_audit_log(const char* event_type, int index, int64_t magnitude);

#ifdef __cplusplus
}
#endif

#endif
