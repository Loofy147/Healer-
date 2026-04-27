# FSC Universal Framework: System Specification

## Module: fsc/fsc_binary.py

### Class: FSCReader
- **__init__**(self, filename: str): Ingests an .fsc file. In v5+, performs **Pre-Flight Healing** of schema metadata using the meta-footer.
- **verify_and_heal**(self, record_idx: int, corrupted_field_idx: int = -1): Heals a specific record. Supports blind localization (t=1) and multi-fault erasure recovery.
- **verify_all_records**(self) -> np.ndarray: Vectorized O(N*C) audit of all file records.

### Class: FSCWriter
- **write**(self, filename: str): Serializes records to .fsc format. In v5+, appends a 0xDEADC0DE meta-footer for metadata protection.

---

## Module: fsc/fsc_block.py

### Class: FSCBlock
- **heal**(self) -> bool: Performs Model 5 single-byte localization within a sector.
- **write**(self, payload: bytes): Optimized internal parity calculation using pre-inverted 3x3 modular matrix.

### Class: FSCVolume
- **heal_volume**(self) -> int: Hierarchical recovery engine (Internal Model 5 + External algebraic RAID). Optimized via C-acceleration.
- **scrub**(self) -> Dict: Proactive maintenance utility. Identifies and repairs latent bit-rot.

---

## Module: fsc/fsc_dynamic.py

### Class: AdaptiveWeightEngine
- **calculate_weights**(data_types, modulus, seed): Generates entropy-inverse weights to prioritize metadata protection.

---

## Native Layer: libfsc.so

### Function: fsc_heal_erasure8
- C-level multi-block RAID recovery solving the Vandermonde-like system over GF(p).

### Function: fsc_calculate_sum8
- High-throughput (1.1 GB/s) vectorized syndrome calculation.

### Function: fsc_batch_verify_model5
- Pass-through verification of 10,000 sectors in ~0.16s.

---

## Strategic Offensive Primitives (Arsenal)

### Module: prototypes/database_forger.py
- **Byzantine Forgery**: Simulating data modification that bypasses both internal sector parity and cross-block RAID parity.

### Module: immortality_research.py
- **Algebraic Ransomware**: Demonstration of irreversible manifold locking.

---
**FSC Defensive Strategy Notice**
Copyright (C) 2024 FSC Core Team. All Rights Reserved.
Protected by **AGPLv3** and **Patent Pending** status.
See [docs/DEFENSIVE_STRATEGY.md](docs/DEFENSIVE_STRATEGY.md) for full licensing and patent details.
