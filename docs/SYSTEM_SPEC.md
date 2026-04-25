# FSC Universal Framework: System Specification

## Module: `fsc/fsc_binary.py`

### Class: `FSCReader`
*   **__init__**`(self, filename: str)`: Ingests an .fsc file. In v5+, performs **Pre-Flight Healing** of schema metadata using the meta-footer.
*   **verify_and_heal**`(self, record_idx: int, corrupted_field_idx: int = -1)`: Heals a specific record. Supports blind localization (=1$) and multi-fault erasure recovery.
*   **verify_all_records**`(self) -> np.ndarray`: Vectorized O(N*C) audit of all file records.

### Class: `FSCWriter`
*   **write**`(self, filename: str)`: Serializes records to .fsc format. In v5+, appends a `0xDEADC0DE` meta-footer for metadata protection.

---

## Module: `fsc/fsc_block.py`

### Class: `FSCBlock`
*   **heal**`(self) -> bool`: Performs Model 5 single-byte localization within a sector.

### Class: `FSCVolume`
*   **heal_volume**`(self) -> int`: Hierarchical recovery engine (Internal Model 5 + External algebraic RAID).
*   **scrub**`(self) -> Dict`: Proactive maintenance utility. Identifies and repairs latent bit-rot.

---

## Module: `fsc/fsc_dynamic.py`

### Class: `AdaptiveWeightEngine`
*   **calculate_weights**`(data_types, modulus, seed)`: Generates entropy-inverse weights to prioritize metadata protection.

---

## Module: `fsc/fsc_framework.py`

### Function: `solve_linear_system(A, b, p)`
*   Gaussian elimination over (p)$ with explicit singularity detection.

### Function: `gf_inv(a, p)`
*   Modular inverse using Fermat's Little Theorem.

---

## Native Layer: `libfsc.so`

### Function: `fsc_heal_multi8`
*   Low-latency C implementation of the multi-fault algebraic solver for UINT8 pages.

### Function: `fsc_calculate_sum8`
*   High-throughput (1.1 GB/s) vectorized syndrome calculation.

---
**FSC Defensive Strategy Notice**
Copyright (C) 2024 FSC Core Team. All Rights Reserved.
Protected by **AGPLv3** and **Patent Pending** status.
See [docs/DEFENSIVE_STRATEGY.md](docs/DEFENSIVE_STRATEGY.md) for full licensing and patent details.
