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

    def write(self, payload: bytes):
        p_len = min(len(payload), self.data_len)
        self.data[:p_len] = np.frombuffer(payload[:p_len], dtype=np.uint8)
        self.data[p_len:self.data_len] = 0
        t1, t2, t3 = self.block_id % self.m, (self.block_id * 7) % self.m, (self.block_id * 13) % self.m
        d = self.data[:self.data_len].astype(np.int64)
        s_d, sw_d, sw2_d = int(np.sum(d) % self.m), int(np.dot(d, self.w[:self.data_len]) % self.m), int(np.dot(d, self.w2[:self.data_len]) % self.m)
        n1, n2, n3 = self.size - 2, self.size - 1, self.size
        A = [[1, 1, 1], [n1, n2, n3], [pow(n1, 2, self.m), pow(n2, 2, self.m), pow(n3, 2, self.m)]]
        b = [(t1 - s_d) % self.m, (t2 - sw_d) % self.m, (t3 - sw2_d) % self.m]
        sol = solve_linear_system(A, b, self.m)
        if sol:
            for i in range(3): self.data[self.size - 3 + i] = int(sol[i]) % 256
        else: raise RuntimeError("Failed to solve for block invariants")

    def verify(self) -> bool:
        d = self.data.astype(np.int64)
        return (int(np.sum(d) % self.m) == self.block_id % self.m and
                int(np.dot(d, self.w) % self.m) == (self.block_id * 7) % self.m and
                int(np.dot(d, self.w2) % self.m) == (self.block_id * 13) % self.m)

    def heal(self) -> bool:
        if self.verify(): return True
        n, m = self.size, self.m
        d = self.data.astype(np.int64)
        s1, s2, s3 = int(np.sum(d) % m), int(np.dot(d, self.w) % m), int(np.dot(d, self.w2) % m)
        t1, t2, t3 = self.block_id % m, (self.block_id * 7) % m, (self.block_id * 13) % m
        syn1, syn2, syn3 = (s1 - t1) % m, (s2 - t2) % m, (s3 - t3) % m
        if syn1 == 0: return False
        try:
            w_idx = (syn2 * gf_inv(syn1, m)) % m
            if w_idx == 0 or w_idx > n or (w_idx * syn2) % m != syn3: return False
            idx = int(w_idx - 1)
            self.data[idx] = (int(self.data[idx]) - syn1) % 256
            return True
        except ValueError: return False

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
        for i in range(self.n_data_blocks):
            self.blocks[i].write(data[i*chunk_size : (i+1)*chunk_size])
        for j in range(self.k_parity):
            p_idx = self.n_data_blocks + j
            p_payload = np.zeros(self.blocks[0].data_len, dtype=np.int64)
            for i in range(self.n_data_blocks):
                p_payload += self.blocks[i].data[:self.blocks[0].data_len].astype(np.int64) * pow(i + 1, j, self.m)
            self.blocks[p_idx].write((p_payload % self.m).astype(np.uint8).tobytes())

    def heal_volume(self) -> int:
        """
        Returns total blocks healed (internal + cross-block).
        """
        internal_healed = 0
        bad = []
        for i, b in enumerate(self.blocks):
            was_valid = b.verify()
            if not was_valid:
                if b.heal(): internal_healed += 1
                else: bad.append(i)

        if not bad: return internal_healed
        if len(bad) > self.k_parity: return -1

        n_lost, d_len = len(bad), self.blocks[0].data_len
        A = [[pow(bi + 1, j, self.m) if bi < self.n_data_blocks else (-1 if (bi - self.n_data_blocks) == j else 0) for bi in bad] for j in range(n_lost)]
        all_d = np.zeros((self.n_blocks, d_len), dtype=np.int64)
        for i in range(self.n_blocks):
            if i not in bad: all_d[i] = self.blocks[i].data[:d_len]
        b_vec = np.zeros((n_lost, d_len), dtype=np.int64)
        for j in range(n_lost):
            p_idx = self.n_data_blocks + j
            k_sum = np.sum([all_d[i] * pow(i + 1, j, self.m) for i in range(self.n_data_blocks) if i not in bad], axis=0) % self.m
            b_vec[j] = (all_d[p_idx] - k_sum) % self.m if p_idx not in bad else (-k_sum) % self.m
        for col in range(d_len):
            sol = solve_linear_system(A, b_vec[:, col].tolist(), self.m)
            if sol:
                for k, bi in enumerate(bad): self.blocks[bi].data[col] = int(sol[k]) % 256
            else: return -2
        for bi in bad: self.blocks[bi].write(self.blocks[bi].data[:d_len].tobytes())
        return internal_healed + len(bad)

    def scrub(self) -> Dict:
        """Proactive background maintenance."""
        latent = [i for i, b in enumerate(self.blocks) if not b.verify()]
        healed = self.heal_volume()
        return {"status": "healthy" if healed >= 0 else "degraded", "sectors_scanned": self.n_blocks, "latent_errors": len(latent), "healed": healed}

    def read_volume(self) -> bytes:
        return b"".join(b.data[:b.data_len].tobytes() for b in self.blocks[:self.n_data_blocks])
