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
    np.random.seed(42)
    original = np.random.randint(0, 251, n, dtype=np.uint8)

    # Calculate targets: sum(data[i] * (i+1)^j)
    targets = np.zeros(k, dtype=np.int64)
    for j in range(k):
        targets[j] = sum(int(original[i]) * pow(i + 1, j, modulus) for i in range(n)) % modulus

    # Corrupt data (2 indices)
    corrupted = original.copy()
    corrupted[3] = (int(corrupted[3]) + 10) % modulus
    corrupted[12] = (int(corrupted[12]) + 50) % modulus

    print(f"  Corrupted indices: [3, 12]")
    print(f"  Attempting native blind recovery (k={k})...")

    # The implementation adds BM[i], which is s[r] = targets[j] - actual
    # If we add 10 to data[3], actual increases by 10 * (3+1)^j
    # so s[j] = -10 * (3+1)^j.
    # To fix it, we should subtract 10.
    # My C code does: data[pos] = (data[pos] + BM) % modulus.
    # If BM = -10, then data[pos] = data[pos] - 10, which is correct.

    # Wait, in my test:
    # corrupted[3] = (original[3] + 10) % modulus
    # actual[j] = (sum(original[i]*(i+1)^j) + 10*(3+1)^j) % modulus
    # targets[j] = sum(original[i]*(i+1)^j) % modulus
    # s[j] = (targets[j] - actual[j]) % modulus = -10*(3+1)^j % modulus
    # BM for pos 3 will be -10.
    # data[3] = (corrupted[3] + BM) % modulus = (original[3] + 10 - 10) % modulus = original[3].
    # YES, adding BM is correct if BM is the error value (target - actual).

    # Let's try with 1 error first to be sure
    corrupted_1 = original.copy()
    corrupted_1[5] = (int(corrupted_1[5]) + 20) % modulus
    print(f"  Single fault test (idx 5)...")
    native_heal_blind8(corrupted_1, targets, modulus)
    if np.array_equal(corrupted_1, original):
        print("✓ Single Blind Recovery Successful")
    else:
        print("✗ Single Blind Recovery Failed")
        print(f"  Original:  {original}")
        print(f"  Recovered: {corrupted_1}")

    # Now the 2 error test
    success = native_heal_blind8(corrupted, targets, modulus)

    if success:
        if np.array_equal(corrupted, original):
            print("✓ Double Blind Recovery Successful and Correct")
        else:
            print("✗ Double Blind Recovery returned Success but data is incorrect")
            print(f"  Original:  {original}")
            print(f"  Recovered: {corrupted}")
    else:
        print("✗ Double Blind Recovery Failed")

if __name__ == "__main__":
    test_blind_healing()
