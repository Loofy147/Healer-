import sys
import os
import numpy as np
sys.path.append(os.getcwd())

from fsc.storage.fsc_block import FSCVolume

def test_volume_scrubbing():
    print("=========================================================")
    print("  FSC v7: PROACTIVE ALGEBRAIC VOLUME SCRUBBING")
    print("=========================================================\n")

    # 10 blocks, 2 parity
    vol = FSCVolume(n_blocks=10, k_parity=2)
    data = b"STAY_IMMORTAL_" * 30 # Fill volume
    vol.write_volume(data)

    print("[STEP 1] Introducing Latent Errors (Bit-rot)...")
    # Block 2 has a bit-flip (Internal healable)
    vol.blocks[2].data[10] ^= 0xFF
    # Block 5 is wiped (Internal unrecoverable, needs cross-block RAID heal)
    vol.blocks[5].data[:] = 0

    print("\n[STEP 2] Running Proactive Scrub...")
    report = vol.scrub()
    print(f"Scrub Report: {report}")

    assert report["latent_errors"] == 2
    assert report["healed"] == 2
    assert report["status"] == "healthy"
    print("✓ Latent errors identified and proactive healed.")

    print("\n[STEP 3] Verifying Data Readback...")
    read_data = vol.read_volume()
    if read_data[:len(data)] == data:
        print("✓ Data bit-perfect after scrub.")
    else:
        print("✗ Data corruption after scrub.")
        exit(1)

    print("\n=========================================================")
    print("  VERIFICATION COMPLETE: INFRASTRUCTURE GAP CLOSED")
    print("=========================================================")

if __name__ == "__main__":
    test_volume_scrubbing()
