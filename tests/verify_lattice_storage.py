import sys
import os
import numpy as np
sys.path.append(os.getcwd())

from fsc.storage.fsc_lattice import LatticeVolume

def test_lattice_storage():
    print("Testing Post-Quantum Lattice Volume...")
    n_blocks = 10
    block_size = 256
    vol = LatticeVolume(n_blocks, block_size)

    test_data = b"POST_QUANTUM_INTEGRITY_TEST"
    vol.write_block(0, test_data)
    vol.write_block(5, b"Sovereign data shard")

    # Verify initial state
    corrupted = vol.verify_volume()
    assert len(corrupted) == 0, f"Expected 0 corrupted, got {len(corrupted)}"
    print("  [INTEGRITY] Initial volume verification passed.")

    # Inject corruption
    print("  [ATTACK] Injecting bit-flip into block 0...")
    vol.data[0, 0] ^= 0x01

    corrupted = vol.verify_volume()
    assert 0 in corrupted, "Lattice integrity failed to detect block 0 corruption"
    print(f"  [INTEGRITY] Detected corruption in blocks: {corrupted}")

    # Restore and verify
    vol.data[0, 0] ^= 0x01
    assert len(vol.verify_volume()) == 0
    print("✓ Lattice Storage Verified")

if __name__ == "__main__":
    test_lattice_storage()
