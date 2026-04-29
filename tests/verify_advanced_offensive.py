"""
FSC: Forward Sector Correction
Verification for Silicon Simulation (Horizon 4) and Byzantine Forgery (Model 6).
"""

import numpy as np
from fsc.advanced.fsc_silicon import FSCSiliconBlackbox
from prototypes.database_forger import ByzantineVolumeForger
from fsc.storage.fsc_block import FSCVolume

def test_silicon_simulation():
    print("Testing Silicon Acceleration Simulation (Horizon 4)...")
    bb = FSCSiliconBlackbox()
    # The FSCSiliconCore uses rom_weights = np.arange(1, 4097, dtype=np.uint8)
    # np.uint8 weights will wrap at 256.
    # Let's align our test expectations with the internal core logic.

    sig_len = 10
    sig = np.full(sig_len, 65, dtype=np.uint8)
    weights = np.arange(1, sig_len + 1, dtype=np.uint8) # Core weights for first 10

    # Calculate target as the core would
    target = int(np.sum(sig.astype(np.int64) * weights.astype(np.int64)) % 251)

    # Corrupt sig[0]
    sig[0] = 0
    res = bb.process_signal(sig, target)

    assert res == "HEALED_IN_SILICON"
    assert sig[0] == 65
    print("  ✓ Silicon healing verified.")

def test_byzantine_forgery():
    print("\nTesting Byzantine Volume Forgery (Model 6)...")
    vol = FSCVolume(n_blocks=8, block_size=128, k_parity=2)
    original_data = b"BYZANTINE-TEST-BLOCK" + b"." * 500
    vol.write_volume(original_data)

    forger = ByzantineVolumeForger(vol)
    new_data = b"FORGED-DATA"
    changes = {i: new_data[i] for i in range(len(new_data))}

    # Forge Sector 1
    success = forger.forge_sector(1, changes)
    assert success

    # Audit
    assert vol.blocks[1].verify(), "Sector internal parity failed!"
    status = vol.scrub()
    assert status['status'] == 'healthy' and status['latent_errors'] == 0, "Volume RAID parity failed!"

    recovered = vol.read_volume()
    d_len = vol.blocks[0].data_len
    start = 1 * d_len
    assert recovered[start : start + len(new_data)] == new_data
    print("  ✓ Byzantine stealth verified (Internal & RAID bypass).")

if __name__ == "__main__":
    try:
        test_silicon_simulation()
        test_byzantine_forgery()
        print("\n✓ ALL ADVANCED OFFENSIVE TESTS PASSED")
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
