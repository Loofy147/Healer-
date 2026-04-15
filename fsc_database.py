"""
Structural Databases — Algebraic Table Constraints
==================================================
Designing database tables where rows and columns are algebraically linked.
The "Balance Sheet" of data: every cell participates in a row-sum
and a column-sum invariant. This is a 2D Structural FSC.
"""

from typing import List, Optional, Dict
from fsc_structural import AlgebraicFormat

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
        self.data = [[0] * (cols + 1) for _ in range(rows + 1)]

    def set_data(self, source_data: List[List[int]]):
        """
        Populate the table and calculate the structural balance fields.
        """
        assert len(source_data) == self.n_rows
        assert all(len(row) == self.n_cols for row in source_data)

        # 1. Fill core data
        for i in range(self.n_rows):
            for j in range(self.n_cols):
                self.data[i][j] = source_data[i][j] % self.m

        # 2. Calculate row invariants (last column)
        # Structural Rule: Sum(row i) % m == i % m
        for i in range(self.n_rows):
            current_sum = sum(self.data[i][j] for j in range(self.n_cols)) % self.m
            target = i % self.m
            self.data[i][self.n_cols] = (target - current_sum) % self.m

        # 3. Calculate column invariants (last row)
        # Structural Rule: Sum(col j) % m == j % m
        for j in range(self.n_cols + 1): # Include the row-invariant column!
            current_sum = sum(self.data[i][j] for i in range(self.n_rows)) % self.m
            target = j % self.m
            self.data[self.n_rows][j] = (target - current_sum) % self.m

    def corrupt(self, row: int, col: int, bad_val: int):
        self.data[row][col] = bad_val

    def verify_and_heal(self) -> List[Dict]:
        """
        Scans the table for violations and heals them.
        Uses the 2D intersection to pinpoint exactly which cell is bad.
        """
        bad_rows = []
        for i in range(self.n_rows + 1):
            target = i % self.m
            actual = sum(self.data[i]) % self.m
            if actual != target:
                bad_rows.append(i)

        bad_cols = []
        for j in range(self.n_cols + 1):
            target = j % self.m
            actual = sum(self.data[i][j] for i in range(self.n_rows + 1)) % self.m
            if actual != target:
                bad_cols.append(j)

        heals = []
        if len(bad_rows) == 1 and len(bad_cols) == 1:
            # Single cell corruption detected at intersection!
            r, c = bad_rows[0], bad_cols[0]
            print(f"  [DB] Intersection detected at ({r}, {c}). Healing...")

            # Recover using row invariant
            target_r = r % self.m
            others_r = (sum(self.data[r]) - self.data[r][c]) % self.m
            recovered_val = (target_r - others_r) % self.m

            orig = self.data[r][c]
            self.data[r][c] = recovered_val
            heals.append({'row': r, 'col': c, 'original': orig, 'recovered': recovered_val})

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
    for row in table.data: print(f"  {row}")

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
    for row in table.data: print(f"  {row}")
    assert table.data[2][1] == 110

if __name__ == "__main__":
    demo()
