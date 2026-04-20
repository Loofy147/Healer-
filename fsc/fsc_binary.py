"""
FSC: Forward Sector Correction - Consolidated Implementation
"""

import numpy as np
import struct
from typing import List, Any, Optional
from itertools import combinations
from fsc.fsc_framework import solve_linear_system

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
                vals = (source_np[:, :nd] @ c.weights)
                if c.modulus:
                    vals %= c.modulus
                full_recs[:, c.stored_field_idx] = vals

        self._record_list.extend(full_recs)

    def write(self, filename: str):
        records = np.array(self._record_list, dtype=np.int64)
        with open(filename, "wb") as f:
            f.write(b"FSC1")
            nd = len(self.schema.data_fields)
            nc = len(self.schema.constraints)
            ns = len(self.schema.all_fields) - nd
            nr = len(records)
            header = struct.pack(">B HB B I", 3, nd, nc, ns, nr)
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
            if f.read(4) != b"FSC1":
                raise ValueError("Invalid magic")
            header_data = f.read(9)
            _, nd, nc, ns, nr = struct.unpack(">B HB B I", header_data)
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

    def _verify_record(self, record_idx: int, data_np: np.ndarray) -> bool:
        record = self.records[record_idx]
        for c in self.constraints:
            if c.is_fiber:
                target = record_idx % (c.modulus or 251)
            elif c.target is not None:
                target = c.target
            else:
                target = record[c.stored_field_idx]

            actual = int(np.dot(c.weights, data_np))
            if c.modulus:
                actual %= c.modulus
            if actual != target:
                return False
        return True

    def verify_and_heal(self, record_idx: int, corrupted_field_idx: int = -1,
                        corrupted_indices: List[int] = None) -> bool:
        record = self.records[record_idx]
        data_np = record[:len(self.data_fields)]
        failed, syndromes = [], {}
        passed = []
        for i, c in enumerate(self.constraints):
            if c.is_fiber:
                target = record_idx % (c.modulus or 251)
            elif c.target is not None:
                target = c.target
            else:
                target = record[c.stored_field_idx]
            actual = int(np.dot(c.weights, data_np))
            if c.modulus:
                actual %= c.modulus
            if actual != target:
                failed.append(i)
                if c.modulus:
                    syndromes[i] = (target - actual) % c.modulus
                else:
                    syndromes[i] = (target - actual)
            else:
                passed.append(i)
        if not failed:
            return True

        c_idx = corrupted_field_idx
        er_idx = set([c_idx] if c_idx != -1 else [])
        if corrupted_indices:
            er_idx.update(corrupted_indices)
        er_indices = sorted(list(er_idx))
        if er_indices:
            t = len(er_indices)
            if len(failed) < t:
                return False
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

        # Optimized Blind Corruption Recovery
        # Strategy: Prune candidates using successful constraints
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
                # Optimization for t=1 with multiple failed constraints: Ratio check
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
