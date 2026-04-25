# FSC Universal Framework: Algebraic Self-Healing Data

The **Forward Sector Correction (FSC)** framework enables exact self-healing for structured data formats with zero or minimal overhead. By embedding linear algebraic invariants directly into the data definition, we transform files from passive bitstreams into active, self-correcting structures.

## Core Principle
**Data is its own checksum.**

Every structured record (e.g., a sensor reading, a financial tick, or a network packet) possesses latent algebraic properties. FSC makes these properties explicit. When a field is corrupted, it is recovered exactly using its relationship to the other fields and stored (or derived) invariants.

## Key Features
- **Multi-fault Tolerance**: Recover $ simultaneous corruptions using polynomial evaluation.
- **Streaming FSC**: Real-time sliding window recovery for live data feeds.
- **Non-numeric Support**: Self-healing for strings, blobs, and mixed-type records.
- **Exact Recovery**: Recover the bit-perfect original value using algebraic closure.
- **Recursive Metadata Protection (v5)**: Meta-invariants protect the structural definitions (moduli/weights) themselves, eliminating bootstrap fragility.
- **Entropy-Weighted Dynamic Stratification (v6)**: Adaptive weights prioritize protection of critical metadata in high-entropy streams.
- **Proactive Algebraic Volume Scrubbing (v7)**: Background maintenance identifies and repairs latent bit-rot before it exceeds redundancy thresholds.
- **Universal Application**: IoT, GPS, Finance, Medical Imaging, Video, and more.

## The Seven Structural Models
1. **Complement Pair**: Mirroring (e.g., DNA base pairing).
2. **Partition Record**: Universe coverage (e.g., Torus arc coloring).
3. **Balanced Group**: Weighted sum (e.g., Double-entry ledger).
4. **Fiber Record**: Positional invariant (Zero-overhead logs).
5. **Algebraic Format**: Multi-constraint overdetermination (Self-identifying corruption).
6. **Dynamic Stratified**: Entropy-derived weighting (v6).
7. **Proactive Volume**: RAID-level scrubbing (v7).

## Repository Structure
- **`fsc/fsc_framework.py`**: Universal FSC healing engine.
- **`fsc/fsc_structural.py`**: Core implementation of the 5 Structural Models.
- **`fsc/fsc_binary.py`**: Binary file format (.fsc) with Model 4/5/Meta support.
- **`fsc/fsc_block.py`**: 2D structural integrity for binary blocks and proactive volumes.
- **`fsc/fsc_dynamic.py`**: Entropy-weighted adaptive weighting engine.
- **`tests/`**: Suite of verification tests for each module.
- **`demos/`**: Practical demonstrations of the framework in action.
- **`prototypes/`**: Specialized domain-specific demonstrations (Audio, Medical, Video).

## Documentation & Audits
- **[docs/SYSTEM_SPEC.md](docs/SYSTEM_SPEC.md)**: Full API reference and method signatures.
- **[docs/AUDIT_REPORT.md](docs/AUDIT_REPORT.md)**: Deep audit of system quality and future roadmap.
- **[docs/FSC_Framework_Documentation.md](docs/FSC_Framework_Documentation.md)**: Detailed mathematical foundation and specifications.

## Getting Started

### Installation
```bash
pip install numpy mnemonic solders
```

### Run Demos
```bash
export PYTHONPATH=$PYTHONPATH:.
python3 demos/fsc_final_demo.py
```

### Run Tests
```bash
./run_tests.sh
```

## License & Commercial Protection
This project is **Dual-Licensed**:
- **Public License**: Licensed under the **GNU Affero General Public License (AGPLv3)**. This ensures that the math remains open and any cloud-based integrations must contribute back to the community.
- **Commercial License**: For proprietary integrations, enterprise support, and patent-safe deployments, a Commercial License is required.

For a detailed breakdown of our IP protection strategy (including patents and hardware cores), see **[docs/DEFENSIVE_STRATEGY.md](docs/DEFENSIVE_STRATEGY.md)**.

## Commercialization & Real-World Deployment
FSC is more than a prototype; it is a high-performance infrastructure primitive designed for deep integration into databases, kernels, and network stacks.

For a detailed vision of how FSC transforms the reliability of SQLite, Linux, and Cloud Infrastructure, see the **[ROADMAP.md](ROADMAP.md)**.

Illustrative C integration shims can be found in **`libfsc/shims/`**.

---
**FSC Defensive Strategy Notice**
Copyright (C) 2024 FSC Core Team. All Rights Reserved.
Protected by **AGPLv3** and **Patent Pending** status.
See [docs/DEFENSIVE_STRATEGY.md](docs/DEFENSIVE_STRATEGY.md) for full licensing and patent details.

## Strategic Technical Gaps Fulfilled
This framework actively bridges critical industry failures through algebraic innovation:
1.  **Metadata Fragility**: Resolved in v5 via **Recursive Manifold Protection**, ensuring that 1 byte of header corruption no longer causes 100% data loss.
2.  **Entropy Interference**: Resolved in v6 via **Dynamic Stratification**, allowing prioritized protection of critical database pointers in heterogeneous streams.
3.  **Latent bit-rot**: Resolved in v7 via **Proactive Volume Scrubbing**, enabling RAID systems to self-repair silent corruption before they reach catastrophic thresholds.
