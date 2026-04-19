import sys
import os
import numpy as np

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fsc.fsc_persistent_storage import PersistentFSCVolume

def test_persistence():
    print("━━ TESTING PERSISTENT FSC STORAGE ━━")
    filename = "test_volume.fscv"
    if os.path.exists(filename): os.remove(filename)

    n_blocks = 8
    block_size = 64
    vol = PersistentFSCVolume(filename, n_blocks, block_size)

    # 1. Write Data
    original_msg = b"Production FSC persistence layer test. Algebraic integrity preserved."
    vol.write(original_msg)
    print(f"  Data written to {filename}. Filesize: {os.path.getsize(filename)} bytes.")

    # 2. Corrupt the file directly on disk
    print("\n[SCENARIO 1] Corrupting block 2 on disk...")
    vol.corrupt_disk(block_idx=2, byte_offset=5, val=0xEE)

    # 3. Reload and Heal
    print("  Reloading volume and attempting hierarchical heal...")
    new_vol = PersistentFSCVolume(filename, n_blocks, block_size)
    healed = new_vol.heal_and_sync()

    readback = new_vol.read()
    if original_msg in readback:
        print(f"  ✓ SCENARIO 1 PASSED: Corruption healed and synced. ({healed} block(s) fixed)")
    else:
        print(f"  ✗ SCENARIO 1 FAILED.")

    # 4. Total block loss (simulated)
    print("\n[SCENARIO 2] Destroying block 4 on disk (multi-byte corruption)...")
    for i in range(10):
        vol.corrupt_disk(block_idx=4, byte_offset=i, val=0x00)

    new_vol_2 = PersistentFSCVolume(filename, n_blocks, block_size)
    healed_2 = new_vol_2.heal_and_sync()
    print(f"  Volume-level healing: {healed_2} block(s) recovered.")

    readback_2 = new_vol_2.read()
    if original_msg in readback_2:
        print("  ✓ SCENARIO 2 PASSED: Block 4 recovered using volume-level parity.")
    else:
        print("  ✗ SCENARIO 2 FAILED.")

    if os.path.exists(filename): os.remove(filename)

if __name__ == "__main__":
    test_persistence()
