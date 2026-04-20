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
from fsc.fsc_framework import solve_linear_system

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
        # O(1) Algebraic Localization (Model 5)
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

        if syn1 == 0:
            # If syn1 is 0 but syn2/syn3 are not, it's not a single corruption
            # or it's a corruption in a way that preserves the sum but not the weighted sum.
            return False

        # i + 1 = syn2 / syn1
        try:
            w = (syn2 * pow(syn1, -1, m)) % m
            if w == 0 or w > n:
                return False

            # Verify with third syndrome
            if (w * syn2) % m != syn3:
                return False

            idx = int(w - 1)
            val = int(self.data[idx])
            self.data[idx] = (val - syn1) % 256
            return True
        except ValueError:
            # No modular inverse
            return False

class FSCVolume:
    def __init__(self, n_blocks: int, block_size: int = 512):
        self.blocks = [FSCBlock(i, block_size) for i in range(n_blocks)]
        self.n_blocks = n_blocks
        self.block_size = block_size

    def write_volume(self, data: bytes):
        chunk_size = self.blocks[0].data_len
        for i in range(self.n_blocks - 1):
            start = i * chunk_size
            chunk = data[start:start+chunk_size]
            self.blocks[i].write(chunk)

        # Cross-block XOR Parity of the FULL DATA (including invariants)
        # To make it simple, we'll XOR the entire block contents
        parity_content = np.zeros(self.block_size, dtype=np.uint8)
        for i in range(self.n_blocks - 1):
            parity_content = np.bitwise_xor(parity_content, self.blocks[i].data)

        # The last block stores this XOR parity.
        # Note: This block will NOT satisfy its own internal Model 5 invariants
        # unless we re-calculate them, but then the XOR property is lost for those bytes.
        # RAID-5 usually doesn't have internal block checksums.
        # Here we'll just store it raw and skip internal heal for the parity block in hierarchical mode if it fails.
        self.blocks[-1].data = parity_content

    def heal_volume(self) -> int:
        healed_count = 0
        # For the parity block, we just check if it matches the XOR sum of others
        def check_parity():
            p = np.zeros(self.block_size, dtype=np.uint8)
            for i in range(self.n_blocks - 1): p = np.bitwise_xor(p, self.blocks[i].data)
            return np.array_equal(p, self.blocks[-1].data)

        bad_indices = []
        for i in range(self.n_blocks - 1):
            if not self.blocks[i].heal():
                bad_indices.append(i)

        # If parity block itself is bad
        if not check_parity() and not bad_indices:
            # We don't have another way to heal parity block if it's the only one bad
            # But we can recompute it!
            p = np.zeros(self.block_size, dtype=np.uint8)
            for i in range(self.n_blocks - 1): p = np.bitwise_xor(p, self.blocks[i].data)
            self.blocks[-1].data = p
            # healed_count += 1 # Not really healing data, just parity
            return 0

        if len(bad_indices) == 1:
            idx = bad_indices[0]
            rec = np.zeros(self.block_size, dtype=np.uint8)
            for i in range(self.n_blocks):
                if i != idx: rec = np.bitwise_xor(rec, self.blocks[i].data)
            self.blocks[idx].data = rec
            healed_count += 1
        return healed_count

    def read_volume(self) -> bytes:
        return b"".join(b.data[:b.data_len].tobytes() for b in self.blocks[:-1])
