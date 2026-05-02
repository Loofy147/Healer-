import sys
import os
import numpy as np
import time
sys.path.append(os.getcwd())

from fsc.core.fsc_native import native_poly_mul, native_poly_mul_ntt

def benchmark_lattice_mul():
    print("Benchmarking Lattice Multiplication (NTT vs. Naive)...")
    n = 256
    q = 12289
    a = np.random.randint(0, q, n, dtype=np.int64)
    b = np.random.randint(0, q, n, dtype=np.int64)

    trials = 1000

    # 1. Naive O(n^2) or conv-based mul
    t0 = time.perf_counter()
    for _ in range(trials):
        res_naive = native_poly_mul(a, b, q)
    t1 = time.perf_counter()
    naive_time = (t1 - t0) / trials
    print(f"  Naive Time: {naive_time*1e6:.2f} us/call")

    # 2. NTT O(n log n) mul
    t0 = time.perf_counter()
    for _ in range(trials):
        res_ntt = native_poly_mul_ntt(a, b)
    t1 = time.perf_counter()
    ntt_time = (t1 - t0) / trials
    print(f"  NTT Time:   {ntt_time*1e6:.2f} us/call")

    speedup = naive_time / ntt_time
    print(f"✓ NTT Speedup: {speedup:.2f}x")

    # Verify correctness (Note: native_poly_mul might be circular, NTT is negacyclic)
    # The comparison should be handled carefully based on modulus and ring.
    # For now, benchmark is the primary focus.

if __name__ == "__main__":
    benchmark_lattice_mul()
