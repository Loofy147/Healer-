## 2024-05-23 - [Logic Error in Heuristic Analyzer]
**Learning:** The FSCAnalyzer's XOR detection heuristic was incorrectly mixing raw data elements with computed XOR sums in its evaluation set, leading to false negatives (missing valid XOR invariants).
**Action:** Always ensure that heuristic sets only contain the target metric being evaluated (e.g., only XOR sums, not XOR sums + individual elements). Vectorized NumPy operations (np.bitwise_xor.reduce) naturally prevent this type of index-off-by-one or mixing error.

## 2024-05-23 - [NumPy tolist() vs. Array Creation Overhead]
**Learning:** For batch operations in Python, creating a NumPy array from a large list of lists is expensive (~0.9s for 1M records). However, once in NumPy, operations like  are extremely fast (~0.05s).
**Action:** To maximize performance, data should ideally stay in NumPy format throughout the pipeline. Transitioning between Python lists and NumPy arrays should be minimized.

## 2024-05-23 - [O(1) Algebraic Search in Model 5]
**Learning:** The previous implementation of FSC healing used nested Python sums to calculate algebraic residuals for every possible corrupted field candidate, resulting in O(N^2) complexity where N is the number of fields.
**Action:** By storing the pre-computed weighted sum of the corrupted record and using O(1) arithmetic (total_sum - weight*corrupt_val) to find the residual, healing speed improved by 5.8x. Vectorizing these checks with NumPy's dot product further reduces per-record overhead.

## 2024-05-23 - [Batching NumPy Operations vs. Per-Record Calls]
**Learning:** Sequential processing of 100k+ records using per-record method calls in Python is extremely slow due to interpreter overhead (~5s). Vectorized batch operations using matrix multiplication (@ operator) and broadcasting reduce this to <0.2s.
**Action:** Always provide batch-optimized versions of core methods (add_records, verify_all) that operate on NumPy matrices directly.

## 2024-05-23 - [Quadratic FSC Recovery]
**Learning:** Non-linear invariants (sum of squares) can be recovered using square roots, but involve sign ambiguity. For sensors like accelerometers, the magnitude invariant is physically meaningful but requires unsigned data or sign inference.
**Action:** Implemented quadratic_sum as a non-exact but physically relevant FSC type.
## 2025-05-14 - [FSC Optimization Learnings]
**Learning:** Python's `open()` and `close()` overhead is significant when performing frequent small random-access reads on persistent storage. Reusing a single file handle across multiple block loads in `PersistentFSCVolume` reduced 100-read latency from ~0.13s to ~0.02s (~6.5x speedup). Additionally, refactoring O(N) search loops into O(1) algebraic localization for Model 5 invariants is a critical win for large block sizes (e.g., 4KB sectors).
**Action:** Always prefer context-managed single-file-handle passes for batch storage operations and prioritize O(1) syndrome-based localization over brute-force search in self-healing logic.
## 2025-05-14 - [2D Page Healing Optimization]
**Learning:** Iterative 2D healing algorithms (alternating row and column verifications) can suffer from redundant row verifications if not cached. By caching row status and only re-verifying modified rows, 2D healing throughput for 50x20 pages increased by ~3.3x (0.0053s -> 0.0016s).
**Action:** Use status caching for iterative multi-dimensional reconciliation algorithms to avoid redundant O(N*M) checks in every sub-iteration.
## 2025-05-14 - [Vectorized Binary I/O Optimization]
**Learning:** Python's `struct.pack` and `struct.unpack` in loops are significant bottlenecks for binary data processing. By switching to numpy vectorized operations for invariant computation and structured numpy arrays for binary I/O, `FSCWriter` and `FSCReader` throughput improved dramatically. For 10,000 records, total write time dropped from ~0.73s to ~0.08s (~9x speedup).
**Action:** Use numpy structured dtypes and `frombuffer`/`tobytes` for high-throughput binary file formats instead of individual record packing.

## 2026-04-26 - [Vectorized Polynomial FSC Optimization]
**Learning:** The initial implementation of polynomial evaluation in FSC was calculating modular powers O(k) for every call, and using Python loops for summation, leading to significant overhead for large codewords.
**Action:** Pre-compute modular powers and their inverses within the closure of the factory method. Use NumPy's vectorized `@` operator for sum-product calculations, which moves the heavy lifting to native code and achieves >10x speedup for 100-element codewords.

## 2026-04-26 - [Vectorized Algebraic RAID Optimization]
**Learning:** Cross-block healing in FSCVolume was previously implemented using a per-byte loop for the linear system solver. This resulted in O(N*L) complexity where N is the number of lost blocks and L is the block length (typically 4KB+).
**Action:** Vectorized the solver by pre-calculating the modular inverse of the system matrix $ over GF(p) and applying it to the entire syndrome matrix using NumPy's `@` operator. This reduced healing time for 4KB blocks from ~0.17s to ~0.01s (~14x speedup). Also vectorized parity computation in `write_volume`.

## 2026-04-26 - [Vectorized Algebraic Block Write Optimization]
**Learning:** For small fixed-size constraint matrices (e.g., 3x3 for Model 5), the overhead of calling a general-purpose linear solver like `solve_linear_system` or even NumPy's `dot` product for tiny inputs can exceed the actual compute time.
**Action:** Pre-calculate the modular inverse of the 3x3 constraint matrix during block initialization. Implement `FSCBlock.write` using manual modular multiplication for the parity calculation and pre-slice weight vectors to maximize throughput. This increased block write throughput from ~21k to ~45k blocks/sec (~2.1x speedup).

## 2026-04-26 - [O(1) Single-Fault FSC Localization]
**Learning:** Blind single-fault recovery (=1$) in `FSCReader` previously used an iterative O(k) verify pass for every column candidate. For files with many columns (100+), this became a significant bottleneck.
**Action:** Vectorized the localization process using syndrome cross-correlation. Since a single corruption at index $ with magnitude $ must satisfy  = mag \cdot w_{j,ci} \pmod{p}$, it follows that  \cdot w_{1,ci} = s_1 \cdot w_{j,ci} \pmod{p}$. Applying this check across all failed constraints simultaneously allows (1)$ localization relative to record length. Throughput improved from ~3.6k to ~21.5k heals/sec (~6x speedup).

## 2026-04-26 - [Vectorized Stream Encoding and Healing]
**Learning:** `FSCHealer` was performing stream encoding and healing using per-group Python calls, ignoring the batch potential of the input data.
**Action:** Implemented specialized batch processing paths in `encode_stream` and `heal_stream` for common structural models (Modular Sum, XOR, Polynomial). By utilizing NumPy matrix-vector multiplication and bitwise reductions on the entire stream, encoding speed improved by up to 10x for array inputs.

## 2026-04-26 - [Native Batch Sector Verification]
**Learning:** Python's overhead for loop-based sector verification in `FSCVolume.scrub` becomes significant as the number of blocks grows (e.g., 10,000 sectors). Even with vectorized intra-sector checks, the sheer number of calls adds latency.
**Action:** Implemented a native C function `fsc_batch_verify_model5` that performs the 3-constraint Model 5 verification for an entire buffer of blocks in a single pass. This reduced volume scrubbing time for 10,000 blocks from ~0.30s to ~0.16s (~2x speedup). The C implementation uses `__int128` accumulators to avoid overflow and is highly SIMD-friendly.

## 2024-05-24 - [AVX2 Weighted Sum Bottleneck]
**Learning:** The native `fsc_calculate_sum8_avx2` had a fast path for unweighted sums but fell back to a scalar loop for weighted sums. Since weighted sums are the core of Model 5/RAID verification and encoding, this was a major bottleneck (~0.84 GB/s).
**Action:** Implemented an AVX2 vectorized path for weighted sums using `_mm256_cvtepu8_epi32` and `_mm256_mul_epi32` with even/odd lane interleaving. This improved weighted verification throughput by ~4.1x (to 3.47 GB/s).

## 2024-05-24 - [AVX2 Unweighted Sum with _mm256_sad_epu8]
**Learning:** `_mm256_sad_epu8` is the most efficient way to sum bytes in AVX2, as it performs 32 absolute differences against zero and accumulates into 64-bit lanes in a single instruction. This achieved ~15 GB/s, significantly faster than a standard accumulation loop.
**Action:** Use `_mm256_sad_epu8` for all unweighted byte summation tasks in native core.

## 2024-05-24 - [Hoisting Sums in Multi-Fault Healing]
**Learning:** The previous `fsc_heal_multi8` implementation had a nested O(k * N) loop with an $O(k)$ branch check inside the inner loop to skip corrupted indices. For large records, the branch mispredictions and redundant summation were costly.
**Action:** Hoist the full record sum out of the solver loop using the optimized vectorized path, then perform $O(k^2)$ scalar subtractions for the corrupted indices. This replaces $O(k \cdot N)$ with $O(N + k^2)$, significantly improving multi-fault recovery speed for large records.

## 2024-05-24 - [Native Block Seal and Verify]
**Learning:** Python's NumPy overhead for small dot products and sum operations (e.g., in `FSCBlock.write` and `verify`) is roughly 50-60% of total execution time. By moving these operations to a native C shim using optimized SIMD syndromes, throughput for a 4KB block increased by ~2.3x.
**Action:** Always provide native shims for frequently called per-block logic like `write` and `verify`.

## 2024-05-24 - [Class-Level Caching for Shared Hardware Parameters]
**Learning:** Initializing thousands of `FSCBlock` objects with redundant modular inverse calculations and NumPy array allocations was the primary bottleneck in volume setup (~0.96s).
**Action:** Implement a class-level `_cache` to share immutable algebraic parameters (weight vectors, constraint matrices) across all blocks. This reduced initialization time to ~0.01s (96x speedup).

## 2024-05-24 - [Hoisting Weights and Accumulating in 64-bit Native]
**Learning:** The native `fsc_volume_encode8` was previously performing per-byte power calculations and modular reductions. In a RAID system with many data blocks, this resulted in significant redundant arithmetic.
**Action:** Pre-calculate parity weights outside the inner data loops and use a 64-bit accumulator (`int64_t`) to sum byte products for an entire block, deferring the modulo operation until the very end. This improved encoding throughput from 15 MB/s to 128 MB/s (8.4x speedup).

## 2024-05-24 - [Native Gaussian Elimination for RAID Healing]
**Learning:** Transitioning multi-block RAID recovery from Python to native C (with `__int128_t` precision and Gaussian elimination) removes the overhead of complex linear algebra in the interpreter and avoids per-block memory copying.
**Action:** Implement `fsc_heal_erasure8` directly in C. This provides a robust foundation for high-performance RAID arrays and handles up to 16 parity blocks efficiently.

## 2024-05-24 - [SIMD Syndrome and Unweighted Sums]
**Learning:** For large sector sizes (e.g., 4KB), unweighted summation and syndrome checks were consuming ~20% of the seal/verify time.
**Action:** Use AVX2 `_mm256_sad_epu8` for unweighted summation (`s0`). This instruction is highly optimized for byte summation and achieves ~15 GB/s throughput. Vectorized the remaining loops to further reduce per-byte overhead.

## 2024-05-24 - [Parallel Data-Major RAID Healing]
**Learning:** Sequential syndrome and residual calculation in RAID healing was a major bottleneck for large arrays (~0.58s). Parallelizing across parity blocks using OpenMP in a Data-Major pattern (one pass through data blocks) reduces cache misses and latency.
**Action:** Implement parallel residual calculation in `fsc_heal_erasure8`. This improved multi-block healing time from 0.58s to 0.37s.

## 2024-05-24 - [AVX2 Weighted Syndrome Bottlenecks]
**Learning:** Initial attempts to vectorize weighted products (data * i and data * i^2) in small moduli ran into overflow issues or register pressure.
**Action:** Used a tiered approach: 32-way SIMD for unweighted sums (`s0`) and careful 8-way SIMD for weighted sums (`s1`, `s2`) with periodic reductions. This ensures max throughput for the most common verification case.
