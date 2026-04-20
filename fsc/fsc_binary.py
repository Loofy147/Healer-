"""
FSC: Forward Sector Correction - Hardened & Accelerated Implementation (v4)
"""

import numpy as np
import struct
import io
from typing import List, Any, Optional
from itertools import combinations
from fsc.fsc_framework import solve_linear_system
from fsc.fsc_native import is_native_available, native_calculate_sum8, native_heal_multi64

FSC_COMMERCIAL_BUILD = False

def fsc_audit_log(event_type: str, index: int, magnitude: int):
    """Enterprise Audit Logging hook."""
    if FSC_COMMERCIAL_BUILD:
         print(f"[COMMERCIAL-AUDIT] EVENT: {event_type} | OFFSET: {index} | MAGNITUDE: {magnitude}")

class FSCField:
    """A single field definition within an FSC record."""
    TYPES = {
        'UINT8': 'B',
        'UINT16': 'H',
        'UINT32': 'I',
        'UINT64': 'Q',
        'INT16': 'h',
        'INT32': 'i',
        'INT64': 'q'
    }

    def __init__(self, name: str, ftype: str):
        self.name = name[:16].ljust(16)
        self.ftype = ftype
        self.fmt = self.TYPES[ftype]


class FSCConstraint:
    """An algebraic constraint: sum(w_i * v_i) == target."""
    def __init__(self, weights: Any, target: Optional[int] = None,
                 is_fiber: bool = False, label: str = "",
                 modulus: Optional[int] = None):
        self.weights = weights
        self.target = target
        self.is_fiber = is_fiber
        self.label = label
        self.modulus = modulus
        self.stored_field_idx = -1


class FSCSchema:
    """Schema defining fields and their algebraic constraints."""
    def __init__(self, fields: List[FSCField]):
        self.data_fields = fields
        self.constraints: List[FSCConstraint] = []
        self.all_fields = list(fields)

    def add_constraint(self, weights: List[int], target: Optional[int] = None,
                       is_fiber: bool = False, modulus: Optional[int] = None, label: str = ""):
        c = FSCConstraint(np.array(weights, dtype=np.int64), target,
                          is_fiber=is_fiber, modulus=modulus, label=label)
        if target is None and not is_fiber:
            c.stored_field_idx = len(self.all_fields)
            self.all_fields.append(FSCField(f"stored_{len(self.constraints)}", "INT64"))
        self.constraints.append(c)


class FSCWriter:
    def __init__(self, schema: FSCSchema):
        self.schema = schema
        self._record_list = []

    def add_record(self, data: Any):
        self.add_records([data])

    def add_records(self, data: Any):
        source_np = np.array(data, dtype=np.int64)
        if len(source_np.shape) == 1:
            source_np = source_np.reshape(1, -1)

        nd = len(self.schema.data_fields)
        na = len(self.schema.all_fields)
        n_recs = source_np.shape[0]

        full_recs = np.zeros((n_recs, na), dtype=np.int64)
        full_recs[:, :nd] = source_np[:, :nd]

        for c in self.schema.constraints:
            if not c.is_fiber and c.target is None:
                if is_native_available() and all(f.ftype == 'UINT8' for f in self.schema.data_fields):
                     # Optimized path for UINT8 data blocks using native libfsc
                     for i in range(n_recs):
                         full_recs[i, c.stored_field_idx] = native_calculate_sum8(source_np[i, :nd].astype(np.uint8), c.weights.astype(np.int32), c.modulus or 0)
                else:
                    vals = (source_np[:, :nd] @ c.weights)
                    if c.modulus:
                        vals %= c.modulus
                    full_recs[:, c.stored_field_idx] = vals

        self._record_list.extend(full_recs)

    def write(self, filename: str):
        records = np.array(self._record_list, dtype=np.int64)
        with open(filename, "wb") as f:
            f.write(b"FSC4")
            nd = len(self.schema.data_fields)
            nc = len(self.schema.constraints)
            ns = len(self.schema.all_fields) - nd
            nr = len(records)
            meta = [nd, nc, ns, nr]
            s1 = sum(meta) % (2**32)
            s2 = sum((i+1)*v for i,v in enumerate(meta)) % (2**32)
            header = struct.pack(">B HH B I II", 4, nd, nc, ns, nr, s1, s2)
            f.write(header)
            for field in self.schema.data_fields:
                f.write(struct.pack(">16s", field.name.encode('ascii')))
                f_idx = list(FSCField.TYPES.keys()).index(field.ftype)
                f.write(struct.pack(">B", f_idx))
            for c in self.schema.constraints:
                ctype = 1 if c.is_fiber else 0
                f.write(struct.pack(
                    ">B q b q", ctype, c.target or 0,
                    c.stored_field_idx, c.modulus or 0)
                )
                w_fmt = ">" + "b" * nd
                f.write(struct.pack(w_fmt, *c.weights.tolist()))
            dtype_list = []
            for f_info in self.schema.all_fields:
                dtype_list.append((f_info.name, ">" + f_info.fmt))
            structured_recs = np.zeros(len(records), dtype=dtype_list)
            for i, f_info in enumerate(self.schema.all_fields):
                structured_recs[f_info.name] = records[:, i]
            f.write(structured_recs.tobytes())


class FSCReader:
    def __init__(self, filename: str):
        self.filename = filename
        self.data_fields = []
        self.constraints = []
        self.records = np.array([], dtype=np.int64)
        self._read_file()

    def _read_file(self):
        with open(self.filename, "rb") as f:
            magic = f.read(4)
            if magic == b"FSC1":
                header_data = f.read(9)
                _, nd, nc, ns, nr = struct.unpack(">B HB B I", header_data)
            elif magic == b"FSC4":
                header_data = f.read(18)
                ver, nd, nc, ns, nr, s1, s2 = struct.unpack(">B HH B I II", header_data)
                meta = [nd, nc, ns, nr]
                calc_s1 = sum(meta) % (2**32)
                calc_s2 = sum((i+1)*v for i,v in enumerate(meta)) % (2**32)
                if calc_s1 != s1 or calc_s2 != s2:
                    fsc_audit_log("HEADER_CORRUPTION_DETECTED", 0, 0)
                    healed = False
                    for i in range(4):
                        others = [v for j,v in enumerate(meta) if i != j]
                        others_weighted = [(j+1)*v for j,v in enumerate(meta) if i != j]
                        rec_v_s1 = (s1 - sum(others)) % (2**32)
                        if ((i+1)*rec_v_s1 + sum(others_weighted)) % (2**32) == s2:
                            meta[i] = rec_v_s1
                            nd, nc, ns, nr = meta
                            fsc_audit_log("HEADER_HEALED", i, rec_v_s1)
                            healed = True
                            break
                    if not healed:
                        raise ValueError("Critical Header Corruption: Unrecoverable")
            else:
                raise ValueError(f"Invalid magic: {magic}")
            ftypes = list(FSCField.TYPES.keys())
            for _ in range(nd):
                name_bytes = struct.unpack(">16s", f.read(16))[0]
                name = name_bytes.decode('ascii').strip()
                ft_idx = struct.unpack(">B", f.read(1))[0]
                self.data_fields.append(FSCField(name, ftypes[ft_idx]))
            self.all_fields = list(self.data_fields)
            for i in range(ns):
                self.all_fields.append(FSCField(f"stored_{i}", "INT64"))
            for _ in range(nc):
                c_data = f.read(18)
                ct, tg, si, mo = struct.unpack(">B q b q", c_data)
                weights = list(struct.unpack(">" + "b"*nd, f.read(nd)))
                is_fiber = (ct == 1)
                m_val = mo if mo != 0 else None
                t_val = tg if is_fiber or tg != 0 or si == -1                     else None
                c = FSCConstraint(
                    np.array(weights, dtype=np.int64), t_val,
                    is_fiber=is_fiber, modulus=m_val
                )
                c.stored_field_idx = si
                self.constraints.append(c)
            dtype_list = []
            for f_info in self.all_fields:
                dtype_list.append((f_info.name, ">" + f_info.fmt))
            if nr > 0:
                dt = np.dtype(dtype_list)
                raw_data = f.read(dt.itemsize * nr)
                structured_recs = np.frombuffer(raw_data, dtype=dt)
                self.records = np.zeros((nr, len(self.all_fields)), dtype=np.int64)
                for i, f_info in enumerate(self.all_fields):
                    self.records[:, i] = structured_recs[f_info.name]
            else:
                cols = len(self.all_fields)
                self.records = np.empty((0, cols), dtype=np.int64)

            # Pre-compute verification metadata for vectorized performance
            if self.constraints:
                self._weight_matrix = np.array([c.weights for c in self.constraints], dtype=np.int64)
                self._moduli = np.array([c.modulus if c.modulus is not None else 0 for c in self.constraints], dtype=np.int64)
                self._fixed_targets = np.array([c.target if c.target is not None else 0 for c in self.constraints], dtype=np.int64)
                self._has_fixed_target = np.array([c.target is not None for c in self.constraints], dtype=bool)
                self._stored_indices = np.array([c.stored_field_idx for c in self.constraints], dtype=np.int64)
                self._is_fiber = np.array([c.is_fiber for c in self.constraints], dtype=bool)

    def _verify_record(self, record_idx: int, data_np: np.ndarray) -> bool:
        record = self.records[record_idx]
        # Vectorized target calculation
        targets = np.where(self._is_fiber,
                           record_idx % np.where(self._moduli != 0, self._moduli, 251),
                           np.where(self._has_fixed_target,
                                    self._fixed_targets,
                                    record[self._stored_indices]))
        # Vectorized dot product for all constraints
        # Optimization: Use NumPy matrix-vector multiplication for O(C*D) verification
        # C = num constraints, D = num data fields. Significantly faster than Python loops.
        actuals = self._weight_matrix @ data_np
        mod_mask = self._moduli != 0
        actuals[mod_mask] %= self._moduli[mod_mask]
        return np.all(actuals == targets)

    def verify_and_heal(self, record_idx: int, corrupted_field_idx: int = -1,
                        corrupted_indices: List[int] = None) -> bool:
        record = self.records[record_idx]
        data_np = record[:len(self.data_fields)]

        # Vectorized verification and syndrome calculation
        targets = np.where(self._is_fiber,
                           record_idx % np.where(self._moduli != 0, self._moduli, 251),
                           np.where(self._has_fixed_target,
                                    self._fixed_targets,
                                    record[self._stored_indices]))
        # Optimization: Use NumPy matrix-vector multiplication for O(C*D) verification
        # C = num constraints, D = num data fields. Significantly faster than Python loops.
        actuals = self._weight_matrix @ data_np
        mod_mask = self._moduli != 0
        actuals[mod_mask] %= self._moduli[mod_mask]

        failed_mask = (actuals != targets)
        if not np.any(failed_mask):
            return True

        diffs = (targets - actuals)
        diffs[mod_mask] %= self._moduli[mod_mask]

        failed = np.where(failed_mask)[0].tolist()
        passed = np.where(~failed_mask)[0].tolist()
        syndromes = {i: diffs[i] for i in failed}

        c_idx = corrupted_field_idx
        er_idx = set([c_idx] if c_idx != -1 else [])
        if corrupted_indices:
            er_idx.update(corrupted_indices)
        er_indices = sorted(list(er_idx))
        if er_indices:
            t = len(er_indices)
            if len(failed) < t:
                return False

            # ATTEMPT NATIVE MULTI-FAULT ACCELERATION (k=2)
            if is_native_available() and t >= 1 and len(failed) >= t:
                 # Check if all relevant constraints use same modulus
                 p_set = {self.constraints[i].modulus for i in failed}
                 if len(p_set) == 1 and list(p_set)[0] is not None:
                     p = list(p_set)[0]
                     targets = []
                     for i in failed:
                         if self.constraints[i].is_fiber:
                             targets.append(record_idx % (self.constraints[i].modulus or 251))
                         elif self.constraints[i].target is not None:
                             targets.append(self.constraints[i].target)
                         else:
                             targets.append(record[self.constraints[i].stored_field_idx])

                     all_weights = np.zeros((len(failed), len(self.data_fields)), dtype=np.int32)
                     for i, f_idx in enumerate(failed):
                         all_weights[i] = self.constraints[f_idx].weights.astype(np.int32)

                     rec_data = data_np.astype(np.int64).copy()
                     if native_heal_multi64(rec_data, all_weights.flatten(),
                                            np.array(targets, dtype=np.int64),
                                            np.array([p]*len(failed), dtype=np.int64),
                                            er_indices):
                         self.records[record_idx, :len(self.data_fields)] = rec_data
                         fsc_audit_log("NATIVE_RECOVERY_KNOWN", 0, 0)
                         return True

            for c_subset in combinations(failed, t):
                p = self.constraints[c_subset[0]].modulus
                if not p:
                    A = [[int(self.constraints[i].weights[ci])
                          for ci in er_indices] for i in c_subset]
                    b = [syndromes[i] for i in c_subset]
                    try:
                        sol = np.linalg.solve(np.array(A), np.array(b))
                        for idx, ci in enumerate(er_indices):
                            mag = int(round(sol[idx]))
                            self.records[record_idx, ci] = int(data_np[ci] + mag)
                            fsc_audit_log("RECOVERY_KNOWN", ci, mag)
                        return True
                    except Exception:
                        continue
                A = [[int(self.constraints[i].weights[ci]) % p
                      for ci in er_indices] for i in c_subset]
                b = [syndromes[i] % p for i in c_subset]
                sol = solve_linear_system(A, b, p)
                if sol:
                    for idx, ci in enumerate(er_indices):
                        mag = int(sol[idx])
                        self.records[record_idx, ci] = (int(data_np[ci]) + mag) % p
                        fsc_audit_log("RECOVERY_KNOWN_MOD", ci, mag)
                    return True
            return False

        t1_candidates = []
        for i in range(len(self.data_fields)):
            is_possible = True
            for p_idx in passed:
                if self.constraints[p_idx].weights[i] != 0:
                    is_possible = False
                    break
            if is_possible:
                t1_candidates.append(i)

        for t in range(1, len(failed) + 1):
            search_space = t1_candidates if t == 1 else range(len(self.data_fields))
            for combo in combinations(search_space, t):
                if t == 1 and len(failed) >= 2:
                    ci = combo[0]
                    match = True
                    i1 = failed[0]
                    c1 = self.constraints[i1]
                    s1 = syndromes[i1]
                    w1 = int(c1.weights[ci])
                    p1 = c1.modulus
                    for i2 in failed[1:]:
                        c2 = self.constraints[i2]
                        s2 = syndromes[i2]
                        w2 = int(c2.weights[ci])
                        p2 = c2.modulus
                        if p1 == p2 and p1 is not None:
                            if (s1 * w2) % p1 != (s2 * w1) % p1:
                                match = False
                                break
                        elif p1 is None and p2 is None:
                            if s1 * w2 != s2 * w1:
                                match = False
                                break
                    if not match: continue

                for c_subset in combinations(failed, t):
                    p = self.constraints[c_subset[0]].modulus
                    if not p:
                        A = [[int(self.constraints[i].weights[ci])
                              for ci in combo] for i in c_subset]
                        b = [syndromes[i] for i in c_subset]
                        try:
                            sol = np.linalg.solve(np.array(A), np.array(b))
                            test_v = data_np.copy()
                            for idx, ci in enumerate(combo):
                                test_v[ci] = int(data_np[ci] + round(sol[idx]))
                            if self._verify_record(record_idx, test_v):
                                for idx, ci in enumerate(combo):
                                    mag = int(round(sol[idx]))
                                    self.records[record_idx, ci] = test_v[ci]
                                    fsc_audit_log("RECOVERY_BLIND", ci, mag)
                                return True
                        except Exception:
                            continue
                    else:
                        A = [[int(self.constraints[i].weights[ci]) % p
                              for ci in combo] for i in c_subset]
                        b = [syndromes[i] % p for i in c_subset]
                        sol = solve_linear_system(A, b, p)
                        if sol:
                            test_v = data_np.copy()
                            for idx, ci in enumerate(combo):
                                test_v[ci] = (int(data_np[ci]) + sol[idx]) % p
                            if self._verify_record(record_idx, test_v):
                                for idx, ci in enumerate(combo):
                                    mag = int(sol[idx])
                                    self.records[record_idx, ci] = test_v[ci]
                                    fsc_audit_log("RECOVERY_BLIND_MOD", ci, mag)
                                return True
        return False

    def get_data(self) -> List[List[int]]:
        return self.records[:, :len(self.data_fields)].tolist()
