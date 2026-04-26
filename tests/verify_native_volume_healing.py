"""
FSC: Forward Sector Correction
Verification for C-accelerated RAID Volume healing.
"""

import numpy as np
import time
from fsc.fsc_block import FSCVolume
from fsc.fsc_native import is_native_available

def test_native_volume_healing():
    print("Testing C-accelerated RAID Volume Healing (Model 5 + erasure coding)")

    if not is_native_available():
        print("  [SKIP] Native library not available.")
        return

    n_blocks = 10
    block_size = 512
    k_parity = 2
    vol = FSCVolume(n_blocks, block_size, k_parity)

    # 1. Write some data
    chunk_size = vol.blocks[0].data_len
    original_data = b"X" * (vol.n_data_blocks * chunk_size)
    vol.write_volume(original_data)

    # 2. Corrupt two blocks completely (erasure)
    print("  [CORRUPTION] Destroying blocks 2 and 5...")
    vol.blocks[2].data[:] = 0
    vol.blocks[5].data[:] = 0

    # 3. Heal using C-accelerated path
    start = time.time()
    healed_count = vol.heal_volume()
    end = time.time()

    print(f"  [HEALING] Recovered {healed_count} blocks in {end-start:.6f}s")

    # 4. Verify data integrity
    recovered_data = vol.read_volume()
    if recovered_data == original_data:
        print("  ✓ DATA RECOVERY SUCCESSFUL (Bit-perfect)")
    else:
        print("  ✗ DATA RECOVERY FAILED")
        exit(1)

    # 5. Stress test with internal bit-flips + erasure
    print("\n  [STRESS] Simulating scattered bit-flips + one block erasure...")
    b3_orig = vol.blocks[3].data.copy()
    vol.blocks[3].data[10] ^= 0x1  # Smallest possible flip
    vol.blocks[7].data[:] = 0       # Block erasure

    healed_count = vol.heal_volume()
    print(f"  [HEALING] Volume heal recovered {healed_count} blocks.")

    recovered_data = vol.read_volume()
    if recovered_data == original_data:
        print("  ✓ STRESS TEST PASSED")
    else:
        print("  ✗ STRESS TEST FAILED")
        if not np.array_equal(vol.blocks[3].data, b3_orig):
             print(f"    Block 3 recovery failed. Value at 10: {vol.blocks[3].data[10]}, Expected: {b3_orig[10]}")
        exit(1)

if __name__ == "__main__":
    test_native_volume_healing()
