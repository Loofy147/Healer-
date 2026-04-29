import numpy as np
import time
from fsc.storage.fsc_block import FSCVolume
from fsc.core.fsc_native import is_native_available

def bench_bolt():
    # Use standard sizes for regression but large enough to see improvements
    n_blocks = 5000
    block_size = 1024
    k_parity = 4

    print(f"--- BOLT Performance Benchmark (v7.18) ---")
    print(f"Configuration: {n_blocks} blocks, {block_size} bytes each, k={k_parity}")

    start_init = time.time()
    vol = FSCVolume(n_blocks, block_size, k_parity)
    end_init = time.time()
    print(f"Initialization: {end_init - start_init:.4f}s")

    chunk_size = vol.blocks[0].data_len
    data = b"STRICT_BOLT_CHECK" * (n_blocks * block_size // 15)
    data = data[:vol.n_data_blocks * chunk_size]

    print(f"Native Available: {is_native_available()}")

    # 1. RAID Encoding
    start = time.time()
    vol.write_volume(data)
    end = time.time()
    elapsed = end - start
    throughput = (len(data) / elapsed) / (1024*1024)
    print(f"RAID Encoding (Native): {elapsed:.4f}s ({throughput:.2f} MB/s)")

    # 2. Round-trip
    read_data = vol.read_volume()
    if read_data[:len(data)] == data:
        print("Round-trip: PASSED")
    else:
        print("Round-trip: FAILED")

    # 3. Erasure Healing
    bad_indices = [0, 10, 100, 500]
    for idx in bad_indices:
        vol.data_buffer[idx*block_size : (idx+1)*block_size] = 0

    start = time.time()
    healed = vol.heal_volume()
    end = time.time()
    print(f"Erasure Healing (4 lost): {end - start:.4f}s (healed={healed})")

    # Verify healing
    read_data_healed = vol.read_volume()
    if read_data_healed[:len(data)] == data:
        print("Healing verification: PASSED")
    else:
        print("Healing verification: FAILED")

if __name__ == "__main__":
    bench_bolt()
