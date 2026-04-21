"""
FSC: Forward Sector Correction
Copyright (C) 2024 FSC Core Team. All Rights Reserved.

OFFENSIVE ARSENAL: SOVEREIGN DATABASE FORGER (Optimized)
========================================================
Achieves O(1) algebraic parity spoofing for arbitrary field changes.
"""

import numpy as np
import sys
from typing import List, Tuple, Optional
from fsc.fsc_framework import solve_linear_system
from fsc.fsc_binary import FSCField, FSCSchema, FSCWriter, FSCReader

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

        # 1. Resolve targets (Dynamic target support)
        targets = []
        for c in self.reader.constraints:
            if c.is_fiber: targets.append(record_idx % (c.modulus or 251))
            elif c.target is not None: targets.append(c.target)
            else: targets.append(record[c.stored_field_idx])
        targets = np.array(targets, dtype=np.int64)

        for f_idx, new_val in field_changes.items():
            record[f_idx] = new_val

        # 2. Optimal Index Selection (Heuristic: indices with weights closest to identity)
        k = self.nc
        if compensation_indices is None:
            compensation_indices = self.find_optimal_indices(field_changes)

        if len(compensation_indices) < k:
            return False

        # 3. Multi-Constraint Linear Solve
        current_data = record[:self.nd].astype(np.int64)
        W = self.reader._weight_matrix

        # Vectorized syndrome calculation for all constraints
        actuals = []
        for i, c in enumerate(self.reader.constraints):
            act = int(np.dot(c.weights, current_data))
            if c.modulus: act %= c.modulus
            actuals.append(act)
        actuals = np.array(actuals, dtype=np.int64)

        # We solve for deltas: A @ delta = b (mod p)
        # where b is the current drift from target
        # Note: Prototype assumes uniform modulus across constraints
        p = int(self.reader._moduli[0] or P)
        b = (targets - actuals) % p
        A = W[:, compensation_indices] % p

        deltas = solve_linear_system(A.tolist(), b.tolist(), p)
        if deltas is None:
            # Singular matrix, try next available set of indices
            return False

        # 4. Inject Parity Shadow
        for i, comp_idx in enumerate(compensation_indices):
            record[comp_idx] = (int(record[comp_idx]) + deltas[i]) % p

        self.reader.records[record_idx] = record
        return True

    def find_optimal_indices(self, field_changes: dict) -> List[int]:
        """
        Finds k indices that form a non-singular matrix with minimal total weight.
        Minimizes the magnitude of compensation changes to reduce forensic footprint.
        """
        k = self.nc
        modified = set(field_changes.keys())
        available = [i for i in range(self.nd) if i not in modified]

        # Sort available indices by weight sum across all constraints (heuristic for 'impact')
        W = self.reader._weight_matrix
        impact = np.sum(np.abs(W), axis=0)
        sorted_available = sorted(available, key=lambda i: impact[i])

        # Try first k available. If singular, we'd need to iterate, but for demo we pick the first k.
        return sorted_available[:k]

    def forge_batch(self, record_indices: List[int], field_changes_list: List[dict]):
        """
        Forges multiple records in sequence using optimized algebraic compensation.
        """
        print(f"[!] Initiating batch forgery for {len(record_indices)} records...")
        count = 0
        for idx, changes in zip(record_indices, field_changes_list):
            if self.forge_record(idx, changes):
                count += 1
        print(f"[✓] Batch Forgery Complete: {count} records poisoned.")

    def forge_batch_vectorized(self, record_indices: List[int], field_changes: dict):
        """
        Forges multiple records simultaneously using matrix-matrix algebraic solve.
        All records undergo the same field change template.
        """
        k = self.nc
        nr = len(record_indices)
        comp_indices = self.find_optimal_indices(field_changes)
        p = int(self.reader._moduli[0] or P)

        # 1. Apply primary changes to all records
        for rec_idx in record_indices:
            for f_idx, val in field_changes.items():
                self.reader.records[rec_idx, f_idx] = val

        # 2. Vectorized Syndrome Matrix calculation
        # syndromes: (nr, nc)
        record_matrix = self.reader.records[record_indices, :self.nd]
        actuals = record_matrix @ self.reader._weight_matrix.T
        actuals %= p

        # Resolve targets for all records
        target_matrix = np.zeros((nr, k), dtype=np.int64)
        for i, rec_idx in enumerate(record_indices):
            rec = self.reader.records[rec_idx]
            for c_idx, c in enumerate(self.reader.constraints):
                if c.is_fiber: target_matrix[i, c_idx] = rec_idx % (c.modulus or 251)
                elif c.target is not None: target_matrix[i, c_idx] = c.target
                else: target_matrix[i, c_idx] = rec[c.stored_field_idx]

        B = (target_matrix - actuals) % p

        # 3. Batch Linear Solve (A @ X = B)
        # A: (nc, k)
        A = self.reader._weight_matrix[:, comp_indices] % p

        # We need to solve NR linear systems. If NR is large, we invert A once.
        try:
            # Simple inversion in GF(P) for small k
            # Since k is small (usually < 16), Gaussian elimination is fine.
            # We use the existing solver column by column
            delta_matrix = np.zeros((nr, k), dtype=np.int64)
            for i in range(nr):
                delta = solve_linear_system(A.tolist(), B[i].tolist(), p)
                if delta:
                    delta_matrix[i] = delta

            # 4. Apply batch compensation
            for i, rec_idx in enumerate(record_indices):
                for j, comp_idx in enumerate(comp_indices):
                    self.reader.records[rec_idx, comp_idx] = (int(self.reader.records[rec_idx, comp_idx]) + delta_matrix[i, j]) % p

            return True
        except Exception:
            return False

def run_offensive_demo():
    print("=========================================================")
    print("  SOVEREIGN ARSENAL: VECTORIZED DATABASE FORGERY")
    print("=========================================================\n")

    n_data = 20
    schema = FSCSchema([FSCField(f"f{i}", "INT64") for i in range(n_data)])
    for i in range(3):
        weights = np.random.randint(1, 50, n_data).tolist()
        schema.add_constraint(weights, modulus=P)

    filename = "vault.fsc"
    writer = FSCWriter(schema)
    writer.add_record([0] * n_data)
    writer.write(filename)

    reader = FSCReader(filename)
    forger = SovereignForger(reader)

    print("[*] Target Record Initial State: Validated.")
    print("[!] Forging Account Balance (Field 10) to $1,000,000,000...")
    forger.forge_record(0, {10: 1000000000})

    if reader._verify_record(0, reader.records[0, :n_data]):
        print("[✓] FORGERY SUCCESSFUL: Algebraic invariants satisfied.")
        print(f"[*] Forged Balance: ${reader.records[0, 10]:,}")
    else:
        print("[✗] FORGERY FAILED: Checksum triggered.")
        sys.exit(1)

if __name__ == "__main__":
    run_offensive_demo()

def test_batch_forgery():
    print("\n[!] TESTING VECTORIZED BATCH FORGERY...")
    n_data = 50
    n_recs = 100
    schema = FSCSchema([FSCField(f"f{i}", "INT64") for i in range(n_data)])
    for _ in range(4):
        schema.add_constraint(np.random.randint(1, 10, n_data).tolist(), modulus=2147483647)

    filename = "batch_vault.fsc"
    writer = FSCWriter(schema)
    for _ in range(n_recs):
        writer.add_record([0] * n_data)
    writer.write(filename)

    reader = FSCReader(filename)
    forger = SovereignForger(reader)

    indices = list(range(n_recs))
    changes = {10: 123456, 20: 654321} # Template for all records

    t0 = time.perf_counter()
    success = forger.forge_batch_vectorized(indices, changes)
    t1 = time.perf_counter()

    if success:
        print(f"[✓] Batch Forgery Successful: 100 records poisoned in {t1-t0:.4f}s.")
        # Bulk verify with core optimized reader
        all_status = reader.verify_all_records()
        if np.all(all_status):
            print("[✓] ALGEBRAIC STEALTH CONFIRMED: Core auditor accepts all 100 poisoned records.")
        else:
            print(f"[✗] AUDIT FAILED: {np.sum(~all_status)} records triggered parity check.")
    else:
        print("[✗] Batch Forgery Execution Failed.")

import time

if __name__ == "__main__":
    test_batch_forgery()
