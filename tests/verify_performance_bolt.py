import numpy as np
import time
from fsc.fsc_block import FSCVolume
from fsc.fsc_native import is_native_available

def bench_bolt():
    n_blocks = 2000
    block_size = 512
    k_parity = 4
    vol = FSCVolume(n_blocks, block_size, k_parity)

    data = np.random.randint(0, 256, (n_blocks - k_parity) * (block_size - 3), dtype=np.uint8).tobytes()

    print(f"--- BOLT Performance Benchmark ---")
    print(f"Configuration: {n_blocks} blocks, {block_size} bytes each, k={k_parity}")
    print(f"Native Available: {is_native_available()}")

    # 1. RAID Encoding (write_volume)
    start = time.time()
    vol.write_volume(data)
    end = time.time()
    throughput = (len(data) / (end - start)) / (1024*1024)
    print(f"RAID Encoding (Native): {end - start:.4f}s ({throughput:.2f} MB/s)")

    # 2. Multi-block Erasure Healing
    # Induce erasures
    bad_indices = [0, 10, 100, 500]
    for idx in bad_indices:
        vol.data_buffer[idx*block_size : (idx+1)*block_size] = 0

    start = time.time()
    healed = vol.heal_volume()
    end = time.time()
    print(f"Erasure Healing ({len(bad_indices)} lost): {end - start:.4f}s (healed={healed})")

    # 3. Volume Scrubbing (Full batch verification)
    start = time.time()
    results = vol.scrub()
    end = time.time()
    print(f"Volume Scrubbing: {end - start:.4f}s (latent={results['latent_errors']})")

if __name__ == "__main__":
    bench_bolt()
