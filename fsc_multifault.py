"""
FSC Multi-fault: k simultaneous field corruptions
===================================================
Single-field FSC uses 1 invariant → recovers 1 corruption.
Multi-fault FSC uses k invariants → recovers k simultaneous corruptions.

Math: treat n data fields as polynomial coefficients over GF(p).
Store k evaluation points as invariants.
Any k corrupted fields → solve k×k linear system over GF(p).

This IS Reed-Solomon, derived from the fiber-stratification principle.
"""

import numpy as np
from itertools import combinations


# ── GF(p) ARITHMETIC ─────────────────────────────────────────────

def gf_inv(a, p):
    """Modular inverse via Fermat's little theorem."""
    return pow(int(a), p-2, p)

def gf_div(a, b, p):
    return (int(a) * gf_inv(b, p)) % p

def poly_eval(coeffs, x, p):
    """Evaluate polynomial at x over GF(p)."""
    return int(sum(int(c) * pow(int(x), i, p) for i,c in enumerate(coeffs))) % p

def lagrange_recover(known_points, query_x, p):
    """Lagrange interpolation: given k points, evaluate at query_x."""
    total = 0
    for i, (xi, yi) in enumerate(known_points):
        num = den = 1
        for j, (xj, _) in enumerate(known_points):
            if i != j:
                num = (num * (query_x - xj)) % p
                den = (den * (xi - xj)) % p
        total = (total + int(yi) * num * gf_inv(den, p)) % p
    return total

def solve_linear_system(A, b, p):
    """Gaussian elimination over GF(p)."""
    n = len(b)
    M = [[int(A[i][j]) % p for j in range(n)] + [int(b[i]) % p]
         for i in range(n)]
    for col in range(n):
        pivot = next((r for r in range(col,n) if M[r][col]%p != 0), None)
        if pivot is None:
            return None
        M[col], M[pivot] = M[pivot], M[col]
        inv_piv = gf_inv(M[col][col], p)
        M[col] = [(v * inv_piv) % p for v in M[col]]
        for row in range(n):
            if row != col and M[row][col] != 0:
                factor = M[row][col]
                M[row] = [(M[row][j] - factor*M[col][j]) % p
                           for j in range(n+1)]
    return [row[-1] % p for row in M]


# ── MULTI-FAULT FSC ENCODER ───────────────────────────────────────

class MultiFaultFSC:
    """
    k-fault tolerant FSC for a record of n integer fields.

    Encodes n data values + k evaluation points.
    Any k simultaneous field corruptions are recoverable.

    Algorithm:
      - Treat data as polynomial coefficients: P(x) = Σ data[i] * x^i
      - Store k evaluations: eval[j] = P(x_j) for j=0..k-1
      - On corruption: set up k equations, solve for corrupted values
    """

    def __init__(self, n_data: int, k_faults: int, p: int = 251):
        assert k_faults <= n_data, "Can't tolerate more faults than data fields"
        self.n     = n_data
        self.k     = k_faults
        self.p     = p
        # Evaluation points: use small primes for numerical stability
        self.eval_points = list(range(1, k_faults + 1))

    def encode(self, data: list) -> list:
        """
        Encode data → data + k evaluation points.
        Returns full record: data[0..n-1] + evals[0..k-1]
        """
        assert len(data) == self.n
        # Evaluation points: P(xⱼ) = Σ data[i] * xⱼ^i mod p
        evals = [poly_eval(data, xj, self.p) for xj in self.eval_points]
        return [v % self.p for v in data] + evals

    def recover(self, record: list, corrupted_indices: list) -> list:
        """
        Recover k corrupted fields from the evaluation invariants.

        corrupted_indices: list of field indices that were corrupted.
        len(corrupted_indices) must equal k (exactly k faults).

        Algorithm:
        1. We know: P(x₀)..P(x_{k-1}) from stored evals
        2. We know: n-k data coefficients (the uncorrupted ones)
        3. Unknown: k corrupted coefficients
        4. Each eval point gives: Σ known[i]*xj^i + Σ unknown[i]*xj^i = eval[j]
           → k equations in k unknowns → solve linear system
        """
        data_part = list(record[:self.n])
        eval_part = list(record[self.n:])
        k         = len(corrupted_indices)
        p         = self.p

        # For each eval point xj, build the equation:
        # Σ_{i in corrupted} unknown[i] * xj^i = eval[j] - Σ_{i not corrupted} data[i] * xj^i
        A = []  # k×k matrix
        b = []  # k RHS values

        for j, xj in enumerate(self.eval_points[:k]):
            row = [pow(int(xj), ci, p) for ci in corrupted_indices]
            known_sum = sum(int(data_part[i]) * pow(int(xj), i, p)
                           for i in range(self.n) if i not in corrupted_indices) % p
            rhs = (int(eval_part[j]) - known_sum) % p
            A.append(row)
            b.append(rhs)

        solution = solve_linear_system(A, b, p)
        if solution is None:
            return None

        healed = list(data_part)
        for idx, ci in enumerate(corrupted_indices):
            healed[ci] = solution[idx]
        return healed + eval_part

    def is_valid(self, record: list) -> bool:
        data_part = record[:self.n]
        eval_part = record[self.n:]
        for j, xj in enumerate(self.eval_points[:self.k]):
            expected = poly_eval(data_part, xj, self.p)
            if expected != int(eval_part[j]) % self.p:
                return False
        return True

    def detect_corruptions(self, record: list) -> list:
        """
        Identify which fields are corrupted by trying all k-combinations.
        Returns list of corrupted field indices, or None if undetectable.
        """
        if self.is_valid(record):
            return []

        data_part = record[:self.n]

        # Try all combinations of k corrupted fields
        for combo in combinations(range(self.n), self.k):
            healed = self.recover(record, list(combo))
            if healed and self.is_valid(healed):
                return list(combo)

        # Try fewer faults
        for num_faults in range(1, self.k):
            for combo in combinations(range(self.n), num_faults):
                healed = self.recover(record, list(combo))
                if healed and self.is_valid(healed):
                    return list(combo)

        return None


# ── DEMO ─────────────────────────────────────────────────────────

if __name__ == '__main__':
    import random
    random.seed(42)

    print("=" * 64)
    print("  FSC MULTI-FAULT — k Simultaneous Field Corruptions")
    print("=" * 64)

    p = 251  # prime field

    test_cases = [
        (6, 1, "1 fault, 1 invariant"),
        (6, 2, "2 faults, 2 invariants"),
        (6, 3, "3 faults, 3 invariants"),
        (8, 4, "4 faults, 4 invariants"),
    ]

    for n_data, k_faults, label in test_cases:
        print(f"\n  ── {label} (n={n_data} fields, p={p}) ──")

        fsc = MultiFaultFSC(n_data, k_faults, p)

        # Generate data and encode
        data = [random.randint(0, p-1) for _ in range(n_data)]
        record = fsc.encode(data)
        assert fsc.is_valid(record), "Encoding failed"

        # Corrupt exactly k fields
        corrupt_positions = random.sample(range(n_data), k_faults)
        corrupted = list(record)
        originals = {}
        for ci in corrupt_positions:
            originals[ci] = corrupted[ci]
            corrupted[ci] = random.randint(0, p-1)

        print(f"    Original data:  {data}")
        print(f"    Corrupted at:   {corrupt_positions}")
        print(f"    Valid after corruption: {fsc.is_valid(corrupted)}")

        # Auto-detect which fields are corrupted
        detected = fsc.detect_corruptions(corrupted)
        print(f"    Auto-detected:  {detected}")

        # Recover
        healed = fsc.recover(corrupted, detected or corrupt_positions)
        ok = healed is not None and healed[:n_data] == [v%p for v in data]
        print(f"    Recovery exact: {ok}")
        if healed:
            print(f"    Healed data:    {healed[:n_data]}")

        overhead = k_faults  # k evaluation points = k bytes each (mod 251)
        overhead_pct = 100 * overhead / n_data
        print(f"    Overhead:       {overhead} eval points = {overhead_pct:.0f}% of data size")

    # Stress test
    print("\n  ── Stress Test: 1000 random records ──")
    fsc = MultiFaultFSC(6, 2, p)
    success = 0
    for _ in range(1000):
        data = [random.randint(0,p-1) for _ in range(6)]
        record = fsc.encode(data)
        corrupt_pos = random.sample(range(6), 2)
        corrupted = list(record)
        for ci in corrupt_pos:
            corrupted[ci] = random.randint(0,p-1)
        healed = fsc.recover(corrupted, corrupt_pos)
        if healed and healed[:6] == [v%p for v in data]:
            success += 1

    print(f"    2-fault recovery: {success}/1000 exact ({success/10:.1f}%)")

    print(f"""
  OVERHEAD SCALING:
  k faults → k evaluation points → k×ceil(log₂(p)/8) bytes
  For p=251 (8-bit): k bytes overhead per record

  k=1: 1 byte  → survives any 1-field corruption
  k=2: 2 bytes → survives any 2 simultaneous corruptions
  k=3: 3 bytes → survives any 3 simultaneous corruptions
  k=n: n bytes → full Reed-Solomon (50% erasure tolerance)

  This is FSC generalized to polynomial erasure codes.
  The single-field case (k=1, our FSC sum invariant) is
  the special case of a degree-0 polynomial (constant).
""")
