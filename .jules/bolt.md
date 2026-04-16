## 2024-05-23 - [Logic Error in Heuristic Analyzer]
**Learning:** The FSCAnalyzer's XOR detection heuristic was incorrectly mixing raw data elements with computed XOR sums in its evaluation set, leading to false negatives (missing valid XOR invariants).
**Action:** Always ensure that heuristic sets only contain the target metric being evaluated (e.g., only XOR sums, not XOR sums + individual elements). Vectorized NumPy operations (np.bitwise_xor.reduce) naturally prevent this type of index-off-by-one or mixing error.

## 2024-05-23 - [NumPy tolist() vs. Array Creation Overhead]
**Learning:** For batch operations in Python, creating a NumPy array from a large list of lists is expensive (~0.9s for 1M records). However, once in NumPy, operations like  are extremely fast (~0.05s).
**Action:** To maximize performance, data should ideally stay in NumPy format throughout the pipeline. Transitioning between Python lists and NumPy arrays should be minimized.
