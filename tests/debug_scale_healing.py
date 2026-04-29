import numpy as np
from fsc.storage.fsc_block import FSCVolume
from fsc.core.fsc_native import is_native_available

def debug_scale():
    n_blocks = 1000
    block_size = 4096
    k_parity = 4
    vol = FSCVolume(n_blocks, block_size, k_parity)

    chunk_size = vol.blocks[0].data_len
    data = b"X" * vol.n_data_blocks * chunk_size
    vol.write_volume(data)

    # Verify all blocks initially
    print("Initial verify:", all(b.verify() for b in vol.blocks))

    # Erase 4 blocks
    bad = [0, 10, 100, 500]
    for idx in bad:
        vol.data_buffer[idx*block_size : (idx+1)*block_size] = 0

    print(f"Heal attempt for {bad}...")
    h = vol.heal_volume()
    print(f"Healed count: {h}")

    mismatches = []
    for idx in bad:
        if not vol.blocks[idx].verify():
            mismatches.append(idx)

    if mismatches:
        print(f"Healing FAILED for blocks: {mismatches}")
        # Check block 0 salted target
        b0 = vol.blocks[0]
        s1 = np.sum(b0.data.astype(np.int64)) % 251
        print(f"Block 0: s1={s1}, expected=1")
    else:
        print("Healing SUCCESS")

if __name__ == "__main__":
    debug_scale()
