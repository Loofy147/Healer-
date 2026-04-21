"""
FSC: Forward Sector Correction
Copyright (C) 2024 FSC Core Team. All Rights Reserved.

PUBLIC LICENSE: GNU Affero General Public License (AGPLv3)
COMMERCIAL LICENSE: Required for proprietary/enterprise use.

PATENT PENDING: Industrial applications of these algebraic primitives
for database pages, kernel block devices, and network protocols.
"""

import numpy as np
import struct
from typing import List, Optional, Tuple
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
        """Write data and compute 3 internal invariants."""
        p_len = min(len(payload), self.data_len)
        self.data[:p_len] = np.frombuffer(payload[:p_len], dtype=np.uint8)
        self.data[p_len:self.data_len] = 0

        t1 = int(self.block_id % self.m)
        t2 = int((self.block_id * 7) % self.m)
        t3 = int((self.block_id * 13) % self.m)

        d = self.data[:self.data_len].astype(np.int64)
        s_d = int(np.sum(d) % self.m)
        sw_d = int(np.dot(d, self.w[:self.data_len]) % self.m)
        sw2_d = int(np.dot(d, self.w2[:self.data_len]) % self.m)

        n1, n2, n3 = self.size - 2, self.size - 1, self.size
        A = [
            [1, 1, 1],
            [n1, n2, n3],
            [pow(n1, 2, self.m), pow(n2, 2, self.m), pow(n3, 2, self.m)]
        ]
        b = [(t1 - s_d) % self.m, (t2 - sw_d) % self.m, (t3 - sw2_d) % self.m]

        sol = solve_linear_system(A, b, self.m)
        if sol:
            self.data[self.size - 3] = int(sol[0]) % 256
            self.data[self.size - 2] = int(sol[1]) % 256
            self.data[self.size - 1] = int(sol[2]) % 256
        else:
            raise RuntimeError("Failed to solve for block invariants")

    def verify(self) -> bool:
        d = self.data.astype(np.int64)
        s1 = int(np.sum(d) % self.m)
        s2 = int(np.dot(d, self.w) % self.m)
        s3 = int(np.dot(d, self.w2) % self.m)

        return (s1 == self.block_id % self.m and
                s2 == (self.block_id * 7) % self.m and
                s3 == (self.block_id * 13) % self.m)

    def heal(self) -> bool:
        """
        Internal block healing.
        Returns True if the block is valid (either was OK or successfully healed).
        Returns False if the block is irrecoverably corrupted (erasure candidate).
        """
        n = self.size
        m = self.m
        d = self.data.astype(np.int64)
        s1 = int(np.sum(d) % m)
        s2 = int(np.dot(d, self.w) % m)
        s3 = int(np.dot(d, self.w2) % m)

        t1, t2, t3 = self.block_id % m, (self.block_id * 7) % m, (self.block_id * 13) % m
        if s1 == t1 and s2 == t2 and s3 == t3:
            return True

        syn1 = (s1 - t1) % m
        syn2 = (s2 - t2) % m
        syn3 = (s3 - t3) % m

        if syn1 == 0: return False

        try:
            w = (syn2 * gf_inv(syn1, m)) % m
            if w == 0 or w > n: return False

            # Verify with third syndrome
            if (w * syn2) % m != syn3: return False

            idx = int(w - 1)
            val = int(self.data[idx])
            self.data[idx] = (val - syn1) % 256
            return True
        except ValueError: return False

class FSCVolume:
    """
    Algebraic RAID Volume.
    Provides K-fault tolerance across blocks using Model 5 (Algebraic Parity).
    """
    def __init__(self, n_blocks: int, block_size: int = 512, k_parity: int = 2):
        self.n_blocks = n_blocks
        self.block_size = block_size
        self.k_parity = k_parity
        self.n_data_blocks = n_blocks - k_parity
        self.blocks = [FSCBlock(i, block_size) for i in range(n_blocks)]
        self.m = 251 # Cross-block Galois Field modulus

    def write_volume(self, data: bytes):
        """
        Write data across data blocks and generate K algebraic parity blocks.
        Each block (including parity) is a valid self-healing FSCBlock.
        """
        chunk_size = self.blocks[0].data_len
        for i in range(self.n_data_blocks):
            start = i * chunk_size
            chunk = data[start:start+chunk_size]
            self.blocks[i].write(chunk)

        # Generate K parity blocks over the data_len payload
        for j in range(self.k_parity):
            p_idx = self.n_data_blocks + j
            parity_payload = np.zeros(self.blocks[0].data_len, dtype=np.int64)
            for i in range(self.n_data_blocks):
                w = pow(i + 1, j, self.m)
                parity_payload += self.blocks[i].data[:self.blocks[0].data_len].astype(np.int64) * w

            # Seal the parity block with its own internal invariants
            self.blocks[p_idx].write((parity_payload % self.m).astype(np.uint8).tobytes())

    def heal_volume(self) -> int:
        """
        Heals volume by identifying bad blocks (erasure detection)
        and solving the cross-block linear system to regenerate them.
        """
        # 1. Internal block healing (Scattered bit-flips)
        bad_indices = []
        for i in range(self.n_blocks):
            if not self.blocks[i].heal():
                bad_indices.append(i)

        if not bad_indices: return 0
        if len(bad_indices) > self.k_parity:
            return -1

        # 2. Cross-block recovery (Algebraic Regeneration of data_len payload)
        n_lost = len(bad_indices)
        A = []
        for j in range(n_lost):
            row = []
            for bi in bad_indices:
                if bi < self.n_data_blocks:
                    row.append(pow(bi + 1, j, self.m))
                else:
                    # Parity block bi is lost. It only participates in its own equation (j == bi-n_data)
                    p_idx = bi - self.n_data_blocks
                    # Weight is -1 because it's on the LHS: sum(w_i B_i) - P_j = 0
                    row.append(-1 if p_idx == j else 0)
            A.append(row)

        all_data = np.zeros((self.n_blocks, self.blocks[0].data_len), dtype=np.int64)
        for i in range(self.n_blocks):
            if i not in bad_indices:
                all_data[i] = self.blocks[i].data[:self.blocks[0].data_len]

        b = np.zeros((n_lost, self.blocks[0].data_len), dtype=np.int64)
        for j in range(n_lost):
            p_idx = self.n_data_blocks + j
            known_sum = np.zeros(self.blocks[0].data_len, dtype=np.int64)
            for i in range(self.n_data_blocks):
                if i not in bad_indices:
                    w = pow(i + 1, j, self.m)
                    known_sum += all_data[i] * w

            if p_idx not in bad_indices:
                # synd = target - actual
                b[j] = (all_data[p_idx] - known_sum) % self.m
            else:
                b[j] = (-known_sum) % self.m

        # Solve for each byte of the payload
        for col in range(self.blocks[0].data_len):
            sol = solve_linear_system(A, b[:, col].tolist(), self.m)
            if sol:
                for k, bi in enumerate(bad_indices):
                    # Temporarily store recovered byte in data array
                    self.blocks[bi].data[col] = int(sol[k]) % 256
            else:
                return -2

        # 3. Restore internal invariants for recovered blocks
        for bi in bad_indices:
            payload = self.blocks[bi].data[:self.blocks[0].data_len].tobytes()
            self.blocks[bi].write(payload)

        return n_lost


    def read_volume(self) -> bytes:
        return b"".join(b.data[:b.data_len].tobytes() for b in self.blocks[:self.n_data_blocks])
