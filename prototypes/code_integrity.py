"""
FSC: Forward Sector Correction
Copyright (C) 2024 FSC Core Team. All Rights Reserved.

PUBLIC LICENSE: GNU Affero General Public License (AGPLv3)
COMMERCIAL LICENSE: Required for proprietary/enterprise use.

PATENT PENDING: Industrial applications of these algebraic primitives
for database pages, kernel block devices, and network protocols.
"""

"""
FSC Prototype: Source Code / Configuration Integrity
===================================================
Demonstrates how algebraic invariants can protect structured text
like source code or config files. We treat characters as integers
and embed linear invariants into the lines.
"""

import numpy as np
from typing import List
from fsc.fsc_structural import AlgebraicFormat

def protect_string(s: str, m: int = 251) -> dict:
    # Treat string as a sequence of integers
    vals = [ord(c) % m for c in s]
    n = len(vals)

    fmt = AlgebraicFormat([f"c{i}" for i in range(n)])

    # Constraint 1: Simple sum mod m
    weights1 = [1] * n
    target1 = sum(vals) % m
    fmt.add_constraint(weights1, target1, modulus=m, label="SUM_MOD")

    # Constraint 2: Weighted sum mod m (positional)
    weights2 = [(i + 1) for i in range(n)]
    target2 = sum((i + 1) * v for i, v in enumerate(vals)) % m
    fmt.add_constraint(weights2, target2, modulus=m, label="WEIGHTED_MOD")

    return {
        'original': s,
        'values': vals,
        'format': fmt,
        'm': m
    }

def simulate_and_heal(protection: dict, corrupted_s: str):
    print(f"Original:  \"{protection['original']}\"")
    print(f"Corrupted: \"{corrupted_s}\"")

    fmt = protection['format']
    m = protection['m']

    # Set corrupted values
    corrupted_vals = {f"c{i}": ord(c) % m for i, c in enumerate(corrupted_s)}
    fmt.set_fields(corrupted_vals)

    violations = fmt.validate()
    if not violations:
        print("✓ No corruption detected.")
        return corrupted_s

    print(f"✗ Corruption detected! Violations: {violations}")

    healed = fmt.heal()
    if healed:
        field_idx = int(healed['field'][1:])
        recovered_char = chr(healed['recovered'])

        healed_list = list(corrupted_s)
        healed_list[field_idx] = recovered_char
        healed_s = "".join(healed_list)

        print(f"✓ Field '{healed['field']}' recovered: '{recovered_char}'")
        print(f"Healed:   \"{healed_s}\"")
        return healed_s
    else:
        print("✗ Recovery failed (too many corruptions or ambiguous).")
        return None

def run_demo():
    print("━━ PROTOTYPE: SOURCE CODE INTEGRITY ━━")

    # Protected code line
    code = "x = compute_result(a, b);"
    protection = protect_string(code)

    # 1. Single character corruption (typo/bit-flip)
    # 'x' changed to 'y' at index 0
    corrupted_1 = "y = compute_result(a, b);"
    simulate_and_heal(protection, corrupted_1)

    print("-" * 40)

    # 2. Another corruption (inside a function name)
    corrupted_2 = "x = compute_tesult(a, b);"
    simulate_and_heal(protection, corrupted_2)

if __name__ == "__main__":
    run_demo()
