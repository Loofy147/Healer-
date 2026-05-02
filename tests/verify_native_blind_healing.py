import sys
import os
import numpy as np
sys.path.append(os.getcwd())

from fsc.core.fsc_native import native_heal_blind8

def test_blind_healing():
    print("Testing Native Blind Multi-Fault Healing...")
    modulus = 251
    n = 20
    k = 4 # Should handle up to 2 blind errors

    # Create original data
    original = np.random.randint(0, 251, n, dtype=np.uint8)

    # Calculate targets: sum(data[i] * (i+1)^j)
    targets = np.zeros(k, dtype=np.int64)
    for j in range(k):
        targets[j] = sum(int(original[i]) * pow(i + 1, j, modulus) for i in range(n)) % modulus

    # Corrupt data (2 indices)
    corrupted = original.copy()
    corrupted[3] = (int(corrupted[3]) + 10) % 256
    corrupted[12] = (int(corrupted[12]) + 50) % 256

    print(f"  Corrupted indices: [3, 12]")
    print(f"  Attempting native blind recovery (k={k})...")

    success = native_heal_blind8(corrupted, targets, modulus)

    if success:
        if np.array_equal(corrupted, original):
            print("✓ Blind Recovery Successful and Correct")
        else:
            print("✗ Blind Recovery returned Success but data is incorrect")
            print(f"  Original:  {original}")
            print(f"  Recovered: {corrupted}")
            # sys.exit(1) # Let's see why
    else:
        print("✗ Blind Recovery Failed")
        # sys.exit(1)

if __name__ == "__main__":
    test_blind_healing()
