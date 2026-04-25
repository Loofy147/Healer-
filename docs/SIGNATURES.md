# FSC Universal Framework: Method Signature Registry

This document serves as the authoritative index of all public classes and methods within the FSC ecosystem.

## 1. Python Core (fsc/)

### Module: `fsc/fsc_binary.py`
*   `class FSCReader(filename: str)`
    *   `verify_and_heal(record_idx: int, corrupted_indices: List[int] = None) -> int`
    *   `verify_all_records() -> np.ndarray`
    *   `get_data() -> List[List[int]]`
*   `class FSCWriter(schema: FSCSchema)`
    *   `add_record(data: Any)`
    *   `write(filename: str)`
*   `class FSCSchema(fields: List[FSCField])`
    *   `add_constraint(weights, target=None, is_fiber=False, modulus=None)`

### Module: `fsc/fsc_block.py`
*   `class FSCVolume(n_blocks, block_size=512, k_parity=2)`
    *   `write_volume(data: bytes)`
    *   `heal_volume() -> int`
    *   `scrub() -> Dict`
    *   `read_volume() -> bytes`
*   `class FSCBlock(block_id, size=512, m=251)`
    *   `write(payload: bytes)`
    *   `verify() -> bool`
    *   `heal() -> bool`

### Module: `fsc/fsc_dynamic.py`
*   `class AdaptiveWeightEngine`
    *   `calculate_weights(data_types, modulus, seed=1) -> np.ndarray`

---

## 2. Native Core (libfsc/)

### Header: `libfsc/libfsc.h`
*   `int64_t fsc_calculate_sum8(uint8_t* data, int32_t* weights, size_t n, int64_t modulus)`
*   `int64_t fsc_calculate_sum64(int64_t* data, int32_t* weights, size_t n, int64_t modulus)`
*   `int fsc_heal_multi8(uint8_t* data, int32_t* weights, size_t n, int64_t* targets, int64_t* moduli, size_t k, size_t* corrupted_indices)`
*   `int fsc_buffer_heal(FSCBuffer* b)`
*   `void fsc_audit_log(const char* event_type, int index, int64_t magnitude)`

---
**FSC Defensive Strategy Notice**
Copyright (C) 2024 FSC Core Team. All Rights Reserved.
Protected by **AGPLv3** and **Patent Pending** status.
See [docs/DEFENSIVE_STRATEGY.md](docs/DEFENSIVE_STRATEGY.md) for full licensing and patent details.
