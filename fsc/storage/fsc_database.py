"""
FSC: Forward Sector Correction
Copyright (C) 2024 FSC Core Team. All Rights Reserved.

PUBLIC LICENSE: GNU Affero General Public License (AGPLv3)
COMMERCIAL LICENSE: Required for proprietary/enterprise use.

PATENT PENDING: Industrial applications of these algebraic primitives
for database pages, kernel block devices, and network protocols.
"""

"""
Structural Databases — Algebraic Table Constraints
==================================================
Designing database tables where rows and columns are algebraically linked.
The "Balance Sheet" of data: every cell participates in a row-sum
and a column-sum invariant. This is a 2D Structural FSC.
"""

import numpy as np
from typing import List, Optional, Dict

class StructuralTable:
    """
    A table where every row i and column j satisfies:
      Sum(row i) == R_i (Positional Row Invariant)
      Sum(col j) == C_j (Positional Col Invariant)
    """
    def __init__(self, rows: int, cols: int, m: int = 251):
        self.n_rows = rows
        self.n_cols = cols
        self.m = m
        # Table data including redundant row/col "edges"
        # We store an (R+1) x (C+1) grid.
        # The last row and last column are the structural balance fields.
        self.data = np.zeros((rows + 1, cols + 1), dtype=np.int64)

    def set_data(self, source_data: List[List[int]]):
        """
        Populate the table and calculate the structural balance fields.
        """
        source_np = np.array(source_data, dtype=np.int64) % self.m
        assert source_np.shape == (self.n_rows, self.n_cols)

        # 1. Fill core data
        self.data[:self.n_rows, :self.n_cols] = source_np

        # 2. Calculate row invariants (last column)
        # Structural Rule: Sum(row i) % m == i % m
        row_sums = np.sum(self.data[:self.n_rows, :self.n_cols], axis=1) % self.m
        row_targets = np.arange(self.n_rows) % self.m
        self.data[:self.n_rows, self.n_cols] = (row_targets - row_sums) % self.m

        # 3. Calculate column invariants (last row)
        # Structural Rule: Sum(col j) % m == j % m
        col_sums = np.sum(self.data[:self.n_rows, :self.n_cols+1], axis=0) % self.m
        col_targets = np.arange(self.n_cols + 1) % self.m
        self.data[self.n_rows, :self.n_cols+1] = (col_targets - col_sums) % self.m

    def corrupt(self, row: int, col: int, bad_val: int):
        self.data[row, col] = bad_val

    def verify_and_heal(self) -> List[Dict]:
        """
        Scans the table for violations and heals them.
        Uses the 2D intersection to pinpoint exactly which cell is bad.
        """
        # Phase 1: Violation detection
        row_sums = np.sum(self.data, axis=1) % self.m
        row_targets = np.arange(self.n_rows + 1) % self.m
        bad_rows = np.where(row_sums != row_targets)[0]

        col_sums = np.sum(self.data, axis=0) % self.m
        col_targets = np.arange(self.n_cols + 1) % self.m
        bad_cols = np.where(col_sums != col_targets)[0]

        heals = []
        if len(bad_rows) == 1 and len(bad_cols) == 1:
            r, c = bad_rows[0], bad_cols[0]
            # print(f"  [DB] Intersection detected at ({r}, {c}). Healing...")

            # Recover using row invariant: target = (current_sum - current_val + recovered_val) % m
            # target - (current_sum - current_val) = recovered_val % m
            target_r = r % self.m
            current_sum_r = row_sums[r]
            current_val = self.data[r, c]

            recovered_val = (target_r - (current_sum_r - current_val)) % self.m

            orig = int(self.data[r, c])
            self.data[r, c] = recovered_val
            heals.append({'row': int(r), 'col': int(c), 'original': orig, 'recovered': int(recovered_val)})

        return heals

def demo():
    print("━━ STRUCTURAL DATABASE TABLE DEMO ━━")
    table = StructuralTable(4, 4)

    # 1. Populate
    raw = [
        [10, 20, 30, 40],
        [5, 15, 25, 35],
        [100, 110, 120, 130],
        [2, 4, 6, 8]
    ]
    table.set_data(raw)
    print("Valid Table (with balance fields):")
    for row in table.data: print(f"  {row.tolist()}")

    # 2. Corrupt one cell
    print("\nCorrupting cell (2, 1) [Value 110 -> 0]...")
    table.corrupt(2, 1, 0)

    # 3. Heal
    heals = table.verify_and_heal()
    if heals:
        print(f"  ✓ Healed: {heals}")
    else:
        print("  ✗ Failed to heal.")

    print("\nFinal Table:")
    for row in table.data: print(f"  {row.tolist()}")
    assert table.data[2, 1] == 110

if __name__ == "__main__":
    demo()
