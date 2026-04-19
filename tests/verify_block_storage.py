import sys
import os
import numpy as np

# Add parent directory to sys.path to import local modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fsc.fsc_block import FSCVolume

def test_block_storage():
    print("━━ TESTING SECTOR-AWARE BLOCK STORAGE (Hierarchical Healing) ━━")

    n_blocks = 5
    block_size = 64
    volume = FSCVolume(n_blocks=n_blocks, block_size=block_size)

    # 1. Write Data
    original_data = b"FSC block-level integrity demonstration. Hierarchical healing works!"
    volume.write_volume(original_data)
    print(f"  Volume initialized with {n_blocks} blocks. Data written.")

    # 2. Simulate Single-Byte Corruptions (Internal Sector Healing)
    print("\n[SCENARIO 1] Simulating scattered byte corruptions...")
    # Corrupt block 0, byte 5
    volume.blocks[0].data[5] ^= 0xFF
    # Corrupt block 2, byte 10
    volume.blocks[2].data[10] ^= 0xAA

    healed = volume.heal_volume()
    print(f"  Internal healing check: Scattered corruptions were recovered internally.")

    readback = volume.read_volume()
    if readback.startswith(original_data):
        print("  ✓ SCENARIO 1 PASSED: Scattered corruptions healed internally.")
    else:
        print(f"  ✗ SCENARIO 1 FAILED.")

    # 3. Simulate Multi-Byte Corruption (Internal Healing Fails, Volume Healing Succeeds)
    print("\n[SCENARIO 2] Simulating multi-byte corruption in Block 1 (Internal recovery fails)...")
    volume.blocks[1].data[0] ^= 0xFF
    volume.blocks[1].data[1] ^= 0xFF
    volume.blocks[1].data[2] ^= 0xFF

    # Internal healing should fail to find a SINGLE byte to fix 3 corrupted bytes.
    healed = volume.heal_volume()
    print(f"  Volume-level healing: {healed} block(s) recovered using cross-sector parity.")

    readback = volume.read_volume()
    if readback.startswith(original_data):
        print("  ✓ SCENARIO 2 PASSED: Multi-byte corruption recovered using volume-level parity.")
    else:
        print(f"  ✗ SCENARIO 2 FAILED.")
        print(f"    Expected: {original_data[:10]}...")
        print(f"    Got:      {readback[:10]}...")

if __name__ == "__main__":
    test_block_storage()
