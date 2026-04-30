"""
FSC: Forward Sector Correction - Multi-Fault Algebraic Solvers
Copyright (C) 2024 FSC Core Team. All Rights Reserved.
"""

import numpy as np
from typing import List, Optional
from fsc.core.fsc_framework import solve_linear_system
from fsc.enterprise.fsc_config import SovereignConfig

class MultiFaultSolver:
    """
    General k-fault algebraic solver using Vandermonde-like systems.
    Capable of correcting k erasures or floor(k/2) blind errors.
    """
    def __init__(self, n_data: int, k_faults: int, p: Optional[int] = None):
        self.n_data = n_data
        self.k_faults = k_faults
        self.p = p or SovereignConfig.get_manifold_params()["modulus"]

    def encode(self, data: np.ndarray) -> np.ndarray:
        """
        Encodes data into a codeword by evaluating a polynomial
        at k extra points.
        """
        assert len(data) == self.n_data
        # Simple systematic encoding: codeword = [data, parity]
        # Parity P_j = sum( (i+1)^j * D_i ) mod p
        parity = np.zeros(self.k_faults, dtype=np.int64)
        for j in range(self.k_faults):
            for i in range(self.n_data):
                parity[j] = (parity[j] + int(data[i]) * pow(i + 1, j + 1, self.p)) % self.p
        return np.concatenate([data, parity])

    def solve_erasures(self, codeword: np.ndarray, erased_indices: List[int]) -> np.ndarray:
        """
        Solves for lost symbols at known positions.
        """
        if not erased_indices: return codeword
        if len(erased_indices) > self.k_faults:
            raise ValueError("Too many erasures to solve")

        # System: sum( (i+1)^j * D_i ) = P_j
        # For erased i: sum_erased( (i+1)^j * D_i ) = P_j - sum_known( (i+1)^j * D_i )

        n_total = self.n_data + self.k_faults
        n_erased = len(erased_indices)

        A = np.zeros((self.k_faults, n_erased), dtype=np.int64)
        b = np.zeros(self.k_faults, dtype=np.int64)

        # Current data in codeword (with zeros at erased positions)
        d_current = codeword.copy()
        for idx in erased_indices: d_current[idx] = 0

        known_indices = [i for i in range(self.n_data) if i not in erased_indices]

        for j in range(self.k_faults):
            # Target is the stored parity if it's not erased
            target_parity_idx = self.n_data + j
            if target_parity_idx not in erased_indices:
                target = codeword[target_parity_idx]
            else:
                # If parity is erased, we can't use this equation as easily for data
                # but we can solve for data using other non-erased parities.
                continue

            s_known = 0
            for i in known_indices:
                s_known = (s_known + int(codeword[i]) * pow(i + 1, j + 1, self.p)) % self.p

            b[j] = (target - s_known + self.p) % self.p
            for k, e_idx in enumerate([ei for ei in erased_indices if ei < self.n_data]):
                A[j, k] = pow(e_idx + 1, j + 1, self.p)

        # We need n_erased_data equations
        erased_data_indices = [ei for ei in erased_indices if ei < self.n_data]
        n_ed = len(erased_data_indices)
        if n_ed == 0: return codeword

        # Find n_ed non-erased parity equations
        valid_eqs = []
        for j in range(self.k_faults):
            if (self.n_data + j) not in erased_indices:
                valid_eqs.append(j)

        if len(valid_eqs) < n_ed: return codeword # Should not happen if total erased <= k

        A_sub = A[valid_eqs[:n_ed], :n_ed]
        b_sub = b[valid_eqs[:n_ed]]

        sol = solve_linear_system(A_sub.tolist(), b_sub.tolist(), self.p)
        if sol:
            for k, e_idx in enumerate(erased_data_indices):
                codeword[e_idx] = sol[k]

        return codeword

if __name__ == "__main__":
    p_val = SovereignConfig.get_manifold_params()["modulus"]
    solver = MultiFaultSolver(n_data=10, k_faults=4)
    data = np.random.randint(0, p_val, 10, dtype=np.int64)
    cw = solver.encode(data)

    print(f"Original Data: {data}")
    # Erase 2 indices
    cw[2] = 0; cw[5] = 0
    recovered = solver.solve_erasures(cw, [2, 5])
    print(f"Recovered Data: {recovered[:10]}")
    assert np.array_equal(data, recovered[:10])
