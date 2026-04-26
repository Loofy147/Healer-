"""
FSC: Forward Sector Correction - Proactive Infrastructure (v7)
Copyright (C) 2024 FSC Core Team. All Rights Reserved.
"""

import numpy as np
import struct
from typing import List, Optional, Tuple, Dict
from fsc.fsc_framework import solve_linear_system, gf_inv
from fsc.fsc_native import is_native_available, native_calculate_sum8, native_heal_single8, FSC_SUCCESS, FSC_ERR_INVALID, FSC_ERR_BOUNDS

class FSCBlock:
    """
    Represents a physical storage sector with internal FSC protection.
    Uses 3-constraint Model 5 for robust intra-sector healing.
    """
    def __init__(self, block_id: int, size: int = 512, m: int = 251):
        self.block_id = block_id
        self.size = size
        self.m = m
        self.data_len = size - 3
        self.data = np.zeros(size, dtype=np.uint8)
        self.w = np.arange(1, size + 1, dtype=np.int64)
        self.w2 = self.w ** 2

        # Pre-slice weights for faster dot products in write()
        self._w_data = self.w[:self.data_len]
        self._w2_data = self.w2[:self.data_len]

        # Bolt Optimization: Pre-calculate the modular inverse of the 3x3 constraint matrix
        n1, n2, n3 = size - 2, size - 1, size
        A = np.array([[1, 1, 1], [n1, n2, n3], [pow(n1, 2, m), pow(n2, 2, m), pow(n3, 2, m)]], dtype=np.int64)
        I = np.eye(3, dtype=np.int64)
        A_inv_rows = []
        for i in range(3):
            row_sol = solve_linear_system(A.tolist(), I[i].tolist(), m)
            if row_sol is None: raise RuntimeError("Singular constraint matrix in FSCBlock")
            A_inv_rows.append(row_sol)
        self._A_inv = np.array(A_inv_rows, dtype=np.int64).T

    def write(self, payload: bytes):
        p_len = min(len(payload), self.data_len)
        self.data[:p_len] = np.frombuffer(payload[:p_len], dtype=np.uint8)
        self.data[p_len:self.data_len] = 0

        t1, t2, t3 = self.block_id % self.m, (self.block_id * 7) % self.m, (self.block_id * 13) % self.m
        d = self.data[:self.data_len].astype(np.int64)

        # Invariants for the data portion
        # Bolt: Avoid double-calculation by using manual sum/dot
        s_d = int(np.sum(d) % self.m)
        sw_d = int(np.dot(d, self._w_data) % self.m)
        sw2_d = int(np.dot(d, self._w2_data) % self.m)

        # Residues to be satisfied by the 3 parity bytes
        # Manual 3x3 modular multiplication to avoid NumPy overhead for tiny matrices
        b1, b2, b3 = (t1 - s_d) % self.m, (t2 - sw_d) % self.m, (t3 - sw2_d) % self.m

        inv = self._A_inv
        p1 = (inv[0,0]*b1 + inv[0,1]*b2 + inv[0,2]*b3) % self.m
        p2 = (inv[1,0]*b1 + inv[1,1]*b2 + inv[1,2]*b3) % self.m
        p3 = (inv[2,0]*b1 + inv[2,1]*b2 + inv[2,2]*b3) % self.m

        self.data[self.size - 3] = int(p1)
        self.data[self.size - 2] = int(p2)
        self.data[self.size - 1] = int(p3)

    def verify(self) -> bool:
        # Bolt Optimization: Avoid copy/re-slice if possible
        d = self.data.astype(np.int64)
        return (int(np.sum(d) % self.m) == self.block_id % self.m and
                int(np.dot(d, self.w) % self.m) == (self.block_id * 7) % self.m and
                int(np.dot(d, self.w2) % self.m) == (self.block_id * 13) % self.m)

    def heal(self) -> bool:
        n, m = self.size, self.m
        d = self.data.astype(np.int64)
        # Calculate actual sums
        s1, s2, s3 = int(np.sum(d) % m), int(np.dot(d, self.w) % m), int(np.dot(d, self.w2) % m)
        # Expected targets
        t1, t2, t3 = self.block_id % m, (self.block_id * 7) % m, (self.block_id * 13) % m

        if s1 == t1 and s2 == t2 and s3 == t3: return True

        syn1, syn2, syn3 = (s1 - t1) % m, (s2 - t2) % m, (s3 - t3) % m
        if syn1 == 0: return False
        try:
            # Single fault localization: w_idx = syn2 / syn1
            w_idx = (syn2 * gf_inv(syn1, m)) % m
            if w_idx == 0 or w_idx > n: return False
            # Consistency check with second-order syndrome
            if (w_idx * syn2) % m != syn3: return False

            idx = int(w_idx - 1)
            self.data[idx] = (int(self.data[idx]) - syn1) % 256
            return True
        except (ValueError, ZeroDivisionError): return False

class FSCVolume:
    """
    Algebraic RAID Volume with Proactive Scrubbing (v7).
    """
    def __init__(self, n_blocks: int, block_size: int = 512, k_parity: int = 2):
        self.n_blocks, self.block_size, self.k_parity = n_blocks, block_size, k_parity
        self.n_data_blocks = n_blocks - k_parity
        self.blocks = [FSCBlock(i, block_size) for i in range(n_blocks)]
        self.m = 251

    def write_volume(self, data: bytes):
        chunk_size = self.blocks[0].data_len
        # Bolt Optimization: Fully vectorized parity computation using NumPy matrix multiplication
        all_data = np.zeros((self.n_data_blocks, chunk_size), dtype=np.int64)
        for i in range(self.n_data_blocks):
            self.blocks[i].write(data[i*chunk_size : (i+1)*chunk_size])
            all_data[i] = self.blocks[i].data[:chunk_size]

        powers_matrix = np.array([[pow(i + 1, j, self.m) for i in range(self.n_data_blocks)] for j in range(self.k_parity)], dtype=np.int64)
        parity_payloads = (powers_matrix @ all_data) % self.m

        for j in range(self.k_parity):
            p_idx = self.n_data_blocks + j
            self.blocks[p_idx].write(parity_payloads[j].astype(np.uint8).tobytes())

    def heal_volume(self) -> int:
        """
        Returns total blocks healed (internal + cross-block).
        """
        internal_healed = 0
        bad = []
        for i, b in enumerate(self.blocks):
            # Bolt Optimization: merge verify and heal to avoid double syndrome calculation
            d = b.data.astype(np.int64)
            s1, s2, s3 = int(np.sum(d) % b.m), int(np.dot(d, b.w) % b.m), int(np.dot(d, b.w2) % b.m)
            t1, t2, t3 = b.block_id % b.m, (b.block_id * 7) % b.m, (b.block_id * 13) % b.m

            if s1 == t1 and s2 == t2 and s3 == t3:
                continue

            # Try internal healing
            syn1, syn2, syn3 = (s1 - t1) % b.m, (s2 - t2) % b.m, (s3 - t3) % b.m
            healed = False
            if syn1 != 0:
                try:
                    w_idx = (syn2 * gf_inv(syn1, b.m)) % b.m
                    if 0 < w_idx <= b.size and (w_idx * syn2) % b.m == syn3:
                        idx = int(w_idx - 1)
                        b.data[idx] = (int(b.data[idx]) - syn1) % 256
                        internal_healed += 1
                        healed = True
                except (ValueError, ZeroDivisionError): pass

            if not healed:
                bad.append(i)

        if not bad: return internal_healed
        if len(bad) > self.k_parity: return -1

        n_lost, d_len = len(bad), self.blocks[0].data_len
        # Bolt Optimization: Vectorized cross-block healing using matrix inversion over GF(p)
        A = np.array([[pow(bi + 1, j, self.m) if bi < self.n_data_blocks else (-1 if (bi - self.n_data_blocks) == j else 0) for bi in bad] for j in range(n_lost)], dtype=np.int64)

        # Pre-calculate the modular inverse of the system matrix A
        I = np.eye(n_lost, dtype=np.int64)
        A_inv_rows = []
        for j in range(n_lost):
            row_sol = solve_linear_system(A.tolist(), I[j].tolist(), self.m)
            if row_sol is None: return -2
            A_inv_rows.append(row_sol)
        A_inv = np.array(A_inv_rows, dtype=np.int64).T

        # Vectorized syndrome calculation (b_vec)
        all_d = np.array([b.data[:d_len] for b in self.blocks], dtype=np.int64)
        powers_matrix = np.array([[pow(i + 1, j, self.m) for i in range(self.n_data_blocks)] for j in range(n_lost)], dtype=np.int64)

        mask = np.ones(self.n_data_blocks, dtype=bool)
        for bi in bad:
            if bi < self.n_data_blocks: mask[bi] = False

        # k_sum is the contribution of the remaining good data blocks to the syndromes
        k_sums = (powers_matrix[:, mask] @ all_d[:self.n_data_blocks][mask]) % self.m

        b_vec = np.zeros((n_lost, d_len), dtype=np.int64)
        for j in range(n_lost):
            p_idx = self.n_data_blocks + j
            b_vec[j] = (all_d[p_idx] - k_sums[j]) % self.m if p_idx not in bad else (-k_sums[j]) % self.m

        # Final vectorized solution: sol_matrix = A_inv @ b_vec (mod p)
        sol_matrix = (A_inv @ b_vec) % self.m

        for k, bi in enumerate(bad):
            self.blocks[bi].data[:d_len] = sol_matrix[k].astype(np.uint8)
            self.blocks[bi].write(self.blocks[bi].data[:d_len].tobytes())

        return internal_healed + len(bad)

    def scrub(self) -> Dict:
        """Proactive background maintenance."""
        latent = [i for i, b in enumerate(self.blocks) if not b.verify()]
        healed = self.heal_volume()
        return {"status": "healthy" if healed >= 0 else "degraded", "sectors_scanned": self.n_blocks, "latent_errors": len(latent), "healed": healed}

    def read_volume(self) -> bytes:
        return b"".join(b.data[:b.data_len].tobytes() for b in self.blocks[:self.n_data_blocks])
