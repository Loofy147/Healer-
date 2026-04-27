# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# !!! FLAGGED FOR SECURITY REVIEW: OFFENSIVE ALGEBRAIC TOOL !!!
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# This file contains capabilities for database forgery, covert
# communication, or cryptographic brute-forcing.
# DO NOT DEPLOY IN PRODUCTION ENVIRONMENTS.
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

"""
FSC: Forward Sector Correction
Copyright (C) 2024 FSC Core Team. All Rights Reserved.

OFFENSIVE ARSENAL: SOVEREIGN DATABASE FORGER (Optimized)
========================================================
Achieves O(1) algebraic parity spoofing for arbitrary field changes.
Now expanded with Byzantine Volume Forgery (Model 6).
"""

import numpy as np
import sys
import time
from typing import List, Tuple, Optional
from fsc.fsc_framework import solve_linear_system
from fsc.fsc_binary import FSCField, FSCSchema, FSCWriter, FSCReader
from fsc.fsc_block import FSCVolume

# Modulus for the demo - using 2^31-1 for INT64 dot compatibility
P = 2147483647

class SovereignForger:
    def __init__(self, reader: FSCReader):
        self.reader = reader
        self.nc = len(reader.constraints)
        self.nd = len(reader.data_fields)

    def forge_record(self, record_idx: int, field_changes: dict,
                     compensation_indices: Optional[List[int]] = None) -> bool:
        """
        General algebraic compensation for arbitrary depth (k) constraints.
        Supports simultaneous multi-field forgery.
        """
        record = self.reader.records[record_idx].copy()

        targets = []
        for c in self.reader.constraints:
            if c.is_fiber: targets.append(record_idx % (c.modulus or 251))
            elif c.target is not None: targets.append(c.target)
            else: targets.append(record[c.stored_field_idx])
        targets = np.array(targets, dtype=np.int64)

        for f_idx, new_val in field_changes.items():
            record[f_idx] = new_val

        k = self.nc
        if compensation_indices is None:
            compensation_indices = self.find_optimal_indices(field_changes)

        if len(compensation_indices) < k: return False

        current_data = record[:self.nd].astype(np.int64)
        W = self.reader._weight_matrix

        actuals = []
        for i, c in enumerate(self.reader.constraints):
            act = int(np.dot(c.weights, current_data))
            if c.modulus: act %= c.modulus
            actuals.append(act)
        actuals = np.array(actuals, dtype=np.int64)

        p = int(self.reader._moduli[0] or P)
        b = (targets - actuals) % p
        A = W[:, compensation_indices] % p

        deltas = solve_linear_system(A.tolist(), b.tolist(), p)
        if deltas is None: return False

        for i, comp_idx in enumerate(compensation_indices):
            record[comp_idx] = (int(record[comp_idx]) + deltas[i]) % p

        self.reader.records[record_idx] = record
        return True

    def find_optimal_indices(self, field_changes: dict) -> List[int]:
        k = self.nc
        modified = set(field_changes.keys())
        available = [i for i in range(self.nd) if i not in modified]
        W = self.reader._weight_matrix
        impact = np.sum(np.abs(W), axis=0)
        sorted_available = sorted(available, key=lambda i: impact[i])
        return sorted_available[:k]

    def forge_batch_vectorized(self, record_indices: List[int], field_changes: dict):
        k = self.nc
        nr = len(record_indices)
        comp_indices = self.find_optimal_indices(field_changes)
        p = int(self.reader._moduli[0] or P)

        for rec_idx in record_indices:
            for f_idx, val in field_changes.items():
                self.reader.records[rec_idx, f_idx] = val

        record_matrix = self.reader.records[record_indices, :self.nd]
        actuals = record_matrix @ self.reader._weight_matrix.T
        actuals %= p

        target_matrix = np.zeros((nr, k), dtype=np.int64)
        for i, rec_idx in enumerate(record_indices):
            rec = self.reader.records[rec_idx]
            for c_idx, c in enumerate(self.reader.constraints):
                if c.is_fiber: target_matrix[i, c_idx] = rec_idx % (c.modulus or 251)
                elif c.target is not None: target_matrix[i, c_idx] = c.target
                else: target_matrix[i, c_idx] = rec[c.stored_field_idx]

        B = (target_matrix - actuals) % p
        A = self.reader._weight_matrix[:, comp_indices] % p

        try:
            delta_matrix = np.zeros((nr, k), dtype=np.int64)
            for i in range(nr):
                delta = solve_linear_system(A.tolist(), B[i].tolist(), p)
                if delta: delta_matrix[i] = delta

            for i, rec_idx in enumerate(record_indices):
                for j, comp_idx in enumerate(comp_indices):
                    self.reader.records[rec_idx, comp_idx] = (int(self.reader.records[rec_idx, comp_idx]) + delta_matrix[i, j]) % p
            return True
        except Exception: return False

class ByzantineVolumeForger:
    """
    Model 6: Cross-layer Forgery.
    Modifies data in a way that bypasses both FSCBlock (internal sector)
    parity AND FSCVolume (cross-block RAID) parity.
    """
    def __init__(self, volume: FSCVolume):
        self.vol = volume

    def forge_sector(self, sector_idx: int, byte_changes: dict) -> bool:
        """
        Forges a single sector and simultaneously updates RAID parity blocks
        to maintain global volume invariants.
        """
        block = self.vol.blocks[sector_idx]
        d_len = block.data_len
        m = self.vol.m

        # 1. Apply primary changes to the sector
        orig_sector_data = block.data.copy()
        for offset, val in byte_changes.items():
            if offset < d_len:
                block.data[offset] = val

        # 2. Heal internal Model 5 parity of the sector
        # (Internal Model 5 parity is at the last 3 bytes)
        block.write(block.data[:d_len].tobytes())

        # 3. Calculate deltas for cross-block parity
        # Parity P_j = sum( (bi+1)^j * D_bi ) mod m
        deltas = (block.data[:d_len].astype(np.int64) - orig_sector_data[:d_len].astype(np.int64)) % m

        # 4. Propagate deltas to all parity blocks
        for j in range(self.vol.k_parity):
            p_idx = self.vol.n_data_blocks + j
            p_block = self.vol.blocks[p_idx]

            weight = pow(sector_idx + 1, j, m)
            p_deltas = (deltas * weight) % m

            # Update parity payload
            p_payload = p_block.data[:d_len].astype(np.int64)
            p_payload = (p_payload + p_deltas) % m

            # Write and reseal the parity block
            p_block.write(p_payload.astype(np.uint8).tobytes())

        return True

def run_byzantine_demo():
    print("\n" + "="*60)
    print("  BYZANTINE SHADOW-OPS: CROSS-BLOCK VOLUME FORGERY")
    print("="*60)

    # 1. Setup Volume
    vol = FSCVolume(n_blocks=10, block_size=512, k_parity=2)
    original_msg = b"TOP-SECRET-DATA-VOL-01" + b"." * 4000
    vol.write_volume(original_msg)

    print("[*] Volume Initialized. Global integrity validated.")

    # 2. Perform Byzantine Forgery
    forger = ByzantineVolumeForger(vol)
    print("[!] Initiating Forgery on Sector 2...")
    print("[!] Changing 'TOP-SECRET' to 'PUBLIC-INFO'...")

    # 'TOP-SECRET' starts at index 0 of Sector 0.
    # Wait, 'TOP-SECRET' is in sector 0.
    new_text = b"PUBLIC-INFO"
    changes = {i: new_text[i] for i in range(len(new_text))}
    forger.forge_sector(0, changes)

    # 3. Validate Stealth
    print("\n[STEALH AUDIT]")
    # Internal sector check
    if vol.blocks[0].verify():
        print("[✓] SECTOR STEALTH: Sector 0 reports internal HEALTHY.")
    else:
        print("[✗] SECTOR STEALTH: Sector 0 parity triggered!")

    # Volume RAID check
    status = vol.scrub()
    if status['status'] == 'healthy' and status['latent_errors'] == 0:
        print("[✓] VOLUME STEALTH: RAID Scrub reports volume HEALTHY.")
    else:
        print("[✗] VOLUME STEALTH: RAID Scrub detected the forgery!")
        print(f"    Details: {status}")

    # Data check
    recovered = vol.read_volume()
    if recovered.startswith(b"PUBLIC-INFO"):
        print(f"\n[✓] FORGERY CONFIRMED: Recovered data = '{recovered[:11].decode()}'")
    else:
        print("[✗] FORGERY FAILED: Data mismatch.")

if __name__ == "__main__":
    run_byzantine_demo()
