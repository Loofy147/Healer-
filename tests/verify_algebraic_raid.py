import sys
import os
import numpy as np

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fsc.fsc_block import FSCVolume

def test_algebraic_raid():
    print("━━ TESTING ALGEBRAIC RAID (Multi-Block Erasure Recovery) ━━")

    n_blocks = 10
    block_size = 64
    k_parity = 3
    volume = FSCVolume(n_blocks=n_blocks, block_size=block_size, k_parity=k_parity)

    # 1. Write Data
    original_data = b"Algebraic RAID can recover from multiple simultaneous sector failures!"
    volume.write_volume(original_data)
    print(f"  Volume initialized with {n_blocks} blocks ({k_parity} parity). Data written.")

    # 2. Verify all OK
    readback = volume.read_volume()
    assert readback.startswith(original_data), "Initial write failure"

    # 3. Destroy 3 blocks (Total Destruction - multi-byte corruption)
    print("\n[SCENARIO] Simultaneously destroying 3 blocks (Block 0, 2, 5)...")
    for bi in [0, 2, 5]:
        volume.blocks[bi].data[0:10] = 0xEE # Destroy bytes
        # volume.blocks[bi].heal() will now return False (erasure detected)

    # 4. Attempt Algebraic RAID Healing
    healed = volume.heal_volume()
    print(f"  RAID Healing Result: {healed} block(s) recovered.")

    # 5. Verify Recovery
    readback = volume.read_volume()
    if readback.startswith(original_data):
        print("  ✓ SUCCESS: All 3 blocks algebraically regenerated bit-perfectly.")
    else:
        print("  ✗ FAILURE: Data mismatch after recovery.")
        # Diagnostic
        for bi in [0, 2, 5]:
             if not volume.blocks[bi].verify():
                 print(f"    Block {bi} is still invalid.")

if __name__ == "__main__":
    test_algebraic_raid()
