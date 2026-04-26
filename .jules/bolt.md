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
