import time
import sys
import os
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fsc.fsc_binary import FSCField, FSCSchema, FSCWriter, FSCReader
from fsc.fsc_persistent_storage import PersistentFSCVolume

def benchmark_syndrome_healing():
    print("━━ BENCHMARK: Syndrome-Based vs Brute-Force ━━")
    n_data = 10
    schema = FSCSchema([FSCField(f"f{i}", "INT64") for i in range(n_data)])
    # Add 4 constraints (supports k=2 blind healing)
    # Using independent weights for better localization
    for i in range(4):
        weights = [0] * n_data
        weights[i] = 1; weights[(i+1)%n_data] = 2; weights[(i+2)%n_data] = 3
        schema.add_constraint(weights, modulus=251)

    filename = "bench.fsc"
    writer = FSCWriter(schema)
    records = np.random.randint(0, 250, (100, n_data))
    writer.add_records(records)
    writer.write(filename)

    reader = FSCReader(filename)
    # Corrupt 2 fields in each record
    for i in range(len(reader.records)):
        reader.records[i, 0] = (reader.records[i, 0] + 50) % 251
        reader.records[i, 1] = (reader.records[i, 1] + 50) % 251

    t0 = time.perf_counter()
    healed_count = 0
    for i in range(len(reader.records)):
        if reader.verify_and_heal(i):
            healed_count += 1
    t1 = time.perf_counter()

    print(f"  Healed {healed_count} records (k=2) in {t1-t0:.4f}s")
    if healed_count > 0:
        print(f"  Throughput: {healed_count/(t1-t0):.1f} heals/sec")

    if os.path.exists(filename): os.remove(filename)

def benchmark_persistence():
    print("\n━━ BENCHMARK: Persistent Storage Throughput ━━")
    filename = "bench.fscv"
    if os.path.exists(filename): os.remove(filename)

    n_blocks = 50
    block_size = 512
    vol = PersistentFSCVolume(filename, n_blocks, block_size, cache_size=20)

    data = b"X" * (n_blocks * 500)

    t0 = time.perf_counter()
    vol.write(data)
    t1 = time.perf_counter()
    print(f"  Write 25KB (striped + parity) in {t1-t0:.4f}s")

    # Random access
    t2 = time.perf_counter()
    for _ in range(100):
        _ = vol.read()
    t3 = time.perf_counter()
    print(f"  100 reads (with LRU cache) in {t3-t2:.4f}s")

    if os.path.exists(filename): os.remove(filename)

if __name__ == "__main__":
    benchmark_syndrome_healing()
    benchmark_persistence()
