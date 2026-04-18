import numpy as np
from fsc_database import StructuralTable
import random

def test_database_healing():
    print("Testing Structural Database Table (2D Self-Healing)")
    R, C = 10, 10
    table = StructuralTable(R, C, m=251)

    # 1. Fill with random data
    raw = [[random.randint(0, 250) for _ in range(C)] for _ in range(R)]
    table.set_data(raw)

    # Copy for verification
    original_state = table.data.copy()

    # 2. Corrupt one random cell
    r = random.randint(0, R)
    c = random.randint(0, C)
    original_val = int(table.data[r, c])
    bad_val = (original_val + random.randint(1, 100)) % 251

    print(f"Corrupting cell ({r}, {c}): {original_val} -> {bad_val}")
    table.corrupt(r, c, bad_val)

    # 3. Heal
    heals = table.verify_and_heal()

    # 4. Final validation
    assert len(heals) == 1
    assert heals[0]['row'] == r
    assert heals[0]['col'] == c
    assert heals[0]['recovered'] == original_val
    assert np.array_equal(table.data, original_state)

    print("✓ DATABASE HEALING VERIFIED (2D Structural Invariants)")

if __name__ == "__main__":
    test_database_healing()
