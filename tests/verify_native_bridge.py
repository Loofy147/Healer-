import sys
import os
import numpy as np
sys.path.append(os.getcwd())

from fsc.fsc_native import is_native_available, native_calculate_sum8

def test_bridge():
    print("Testing FSC Native Bridge...")
    if not is_native_available():
        print("✗ Native library not available.")
        sys.exit(1)

    data = np.array([1, 2, 3, 4], dtype=np.uint8)
    # Sum = 10. Mod 7 = 3.
    res = native_calculate_sum8(data, None, 7)
    print(f"Native Sum (mod 7): {res}")
    assert res == 3

    weights = np.array([1, 2, 1, 2], dtype=np.int32)
    # Weighted Sum = 1*1 + 2*2 + 3*1 + 4*2 = 1 + 4 + 3 + 8 = 16. Mod 7 = 2.
    res = native_calculate_sum8(data, weights, 7)
    print(f"Native Weighted Sum (mod 7): {res}")
    assert res == 2

    print("✓ FSC Native Bridge Verified")

if __name__ == "__main__":
    test_bridge()
