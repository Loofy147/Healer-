# FSC Universal Framework: Algebraic Self-Healing Data

## 1. The Principle
**Data is its own checksum.**

The FSC framework is built on the single observation that every structured data format possesses latent algebraic properties. By making these properties explicit through linear invariants, we transform data from a passive sequence of bits into an active, self-healing structure.

---

## 2. Mathematical Foundation

### The Three Conditions for Exact Closure
1.  **Field Consistency**: All operations occur within a defined field ($Z, Z_m, GF(2), GF(p)$).
2.  **Linearity**: The invariant is a linear combination of data elements.
3.  **Overdetermination**: Detection and healing require more constraints than degrees of freedom for corruption.

### The Four Invariant Types
*   **Integer Sum**: $S = \sum v_i$ (Field: $Z$)
*   **Modular Sum**: $S = \sum v_i \pmod m$ (Field: $Z_m$)
*   **XOR Sum**: $S = \bigoplus v_i$ (Field: $GF(2)$)
*   **Polynomial Evaluation**: $S = P(x)$ (Field: $GF(p)$ - Multi-fault)

---

## 3. Structural FSC Models
1.  **Complement Pair**: Involution (DNA).
2.  **Partition Record**: Disjoint coverage (Torus).
3.  **Balanced Group**: Type-defined sum (Ledger).
4.  **Fiber Record**: Positional invariant (Zero-overhead).
5.  **Algebraic Format**: Multi-constraint overdetermination (Self-localizing).

---

## 4. Advanced Frontiers (Phase 3)

### 4.1 Multi-Fault Binary Recovery
Generalizes FSC to recover $k$ simultaneous corruptions. The \`.fsc\` format (v3) supports persistent modulus metadata and automatic system-of-equations solving over $GF(p)$.

### 4.2 Non-Linear Continuity Healing
Handles quadratic invariants ($\sum v_i^2 = S$) by using sequential record continuity to resolve the $\pm$ root ambiguity.

### 4.3 2D Page Integrity
Iterative healing alternating between row-wise Model 5 and column-wise modular parity to resolve large erasure blocks.

### 4.4 Wallet Mnemonic Recovery (Positional Robustness)
High-impact application using Sum and Weighted Sum invariants mod 2048 to recover 2 missing words from ANY position in a 12-word BIP-39 mnemonic phrase. Verified via 15-way mixed positional stress tests.

---

## 5. File Format Specification v3 (.fsc)

### Header (18 bytes per constraint)
- **Magic**: \`FSC1\`
- **Version**: \`0x03\`
- **Constraints**: Includes a 64-bit \`modulus\` field for finite field arithmetic closure.

### Recovery Algorithm
1. Detect failed constraints.
2. If $k=1$, apply Model 5 localization.
3. If $k>1$, set up $k \times k$ linear system $Ax = b$ over $GF(p)$ and solve via Gaussian elimination.

---

## 6. Verified Applications

| Domain | Mechanism | Integrity Mode | Result |
| :--- | :--- | :--- | :--- |
| **Mnemonic** | (12, 10) Mod Solver | algebraic utility | 15/15 positional tests |
| **Code Integrity** | Character Sums | structural text | bit-flips healed |
| **MRI / 3D** | Fiber Sums | structural tensor | voxels recovered |
| **HFT / Finance** | XOR Sums | streaming | nanosecond latency |
| **Sensors** | Quadratic + Continuity | non-linear | sign resolved |

---
**FSC Defensive Strategy Notice**
Copyright (C) 2024 FSC Core Team. All Rights Reserved.
Protected by **AGPLv3** and **Patent Pending** status.
See [docs/DEFENSIVE_STRATEGY.md](docs/DEFENSIVE_STRATEGY.md) for full licensing and patent details.
