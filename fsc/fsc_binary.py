"""
FSC: Forward Sector Correction - Hardened & Accelerated Implementation (v4)
"""
import os

import numpy as np
import struct
import io
from typing import List, Any, Optional
from collections import defaultdict
from itertools import combinations
from fsc.fsc_framework import solve_linear_system
from fsc.fsc_native import is_native_available, native_calculate_sum8, native_calculate_sum64, native_heal_single64, native_heal_multi64, native_heal_multi8, native_audit_log, FSC_SUCCESS, FSC_ERR_SINGULAR, FSC_ERR_BOUNDS, FSC_ERR_INVALID

FSC_COMMERCIAL_BUILD = False
MAX_FIELDS = 1024
MAX_CONSTRAINTS = 1024
MAX_RECORDS = 10000000  # 10M records limit


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
        if len(source_np.shape) == 1: source_np = source_np.reshape(1, -1)
        nd = len(self.schema.data_fields); na = len(self.schema.all_fields); n_recs = source_np.shape[0]
        full_recs = np.zeros((n_recs, na), dtype=np.int64); full_recs[:, :nd] = source_np[:, :nd]
        groups = defaultdict(list)
        for c in self.schema.constraints:
            if not c.is_fiber and c.target is None: groups[c.modulus].append(c)
        for modulus, c_list in groups.items():
            if not c_list: continue
            weights_batch = np.array([c.weights for c in c_list], dtype=np.int64)
            vals = source_np[:, :nd] @ weights_batch.T
            if modulus: vals %= modulus
            for i, c in enumerate(c_list): full_recs[:, c.stored_field_idx] = vals[:, i]
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

                if nd > MAX_FIELDS or nc > MAX_CONSTRAINTS or nr > MAX_RECORDS:
                    raise ValueError(f"Resource limit exceeded: fields={nd}, constraints={nc}, records={nr}")

            elif magic == b"FSC4":
                header_data = f.read(18)
                ver, nd, nc, ns, nr, s1, s2 = struct.unpack(">B HH B I II", header_data)

                if nd > MAX_FIELDS or nc > MAX_CONSTRAINTS or nr > MAX_RECORDS:
                    raise ValueError(f"Resource limit exceeded: fields={nd}, constraints={nc}, records={nr}")

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
                if ft_idx >= len(ftypes): raise ValueError(f"Invalid field type index: {ft_idx}")
                self.data_fields.append(FSCField(name, ftypes[ft_idx]))
            self.all_fields = list(self.data_fields)
            for i in range(ns):
                self.all_fields.append(FSCField(f"stored_{i}", "INT64"))
            for _ in range(nc):
                c_data = f.read(18)
                ct, tg, si, mo = struct.unpack(">B q b q", c_data)
                if len(c_data) < 18: raise ValueError("Truncated constraint header")
                weight_bytes = f.read(nd)
                if len(weight_bytes) != nd: raise ValueError(f"Constraint weight mismatch: expected {nd}, got {len(weight_bytes)}")
                weights = list(struct.unpack(">" + "b"*nd, weight_bytes))
                is_fiber = (ct == 1)
                m_val = mo if mo != 0 else None
                t_val = tg if is_fiber or tg != 0 or si == -1                     else None
                c = FSCConstraint(
                    np.array(weights, dtype=np.int64), t_val,
                    is_fiber=is_fiber, modulus=m_val
                )
                if si != -1 and (si < 0 or si >= nd + ns): raise ValueError(f"Invalid stored_field_idx: {si}")
                c.stored_field_idx = si
                self.constraints.append(c)
            dtype_list = []
            for f_info in self.all_fields:
                dtype_list.append((f_info.name, ">" + f_info.fmt))

            if nr > 0:
                dt = np.dtype(dtype_list)
                expected_size = dt.itemsize * nr
                file_size = os.path.getsize(self.filename)
                current_pos = f.tell()
                if current_pos + expected_size > file_size:
                    raise ValueError(f"File truncated: expected {expected_size} more bytes, but only {file_size - current_pos} available")
                raw_data = f.read(expected_size)

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
        targets = np.where(self._is_fiber, record_idx % np.where(self._moduli != 0, self._moduli, 251),
                           np.where(self._has_fixed_target, self._fixed_targets, record[self._stored_indices]))

        if is_native_available():
            actuals = np.zeros(len(self.constraints), dtype=np.int64)
            for i, c in enumerate(self.constraints):
                actuals[i] = native_calculate_sum64(data_np, c.weights.astype(np.int32), c.modulus or 0)
        else:
            actuals = data_np @ self._weight_matrix.T
            for mod_val in np.unique(self._moduli):
                if mod_val == 0: continue
                mask = (self._moduli == mod_val); actuals[mask] %= mod_val
        return np.all(actuals == targets)

    def verify_and_heal(self, record_idx: int, corrupted_field_idx: int = -1, corrupted_indices: List[int] = None) -> int:
        if not self.constraints: return FSC_SUCCESS
        record = self.records[record_idx]
        data_np = record[:len(self.data_fields)]
        record_indices = np.array([record_idx])
        fiber_mod = np.where(self._moduli != 0, self._moduli, 251)
        fiber_targets = record_indices % fiber_mod
        targets = np.where(self._is_fiber, fiber_targets[0], np.where(self._has_fixed_target, self._fixed_targets, record[self._stored_indices]))

        if is_native_available():
            actuals = np.zeros(len(self.constraints), dtype=np.int64)
            for i, c in enumerate(self.constraints):
                actuals[i] = native_calculate_sum64(data_np, c.weights.astype(np.int32), c.modulus or 0)
        else:
            actuals = data_np @ self._weight_matrix.T
            for mod_val in np.unique(self._moduli):
                if mod_val == 0: continue
                mask = (self._moduli == mod_val); actuals[mask] %= mod_val
        syndromes = (targets - actuals); failed = np.where(actuals != targets)[0]; passed = np.where(actuals == targets)[0]
        if len(failed) == 0: return FSC_SUCCESS

        er_indices = []
        if corrupted_field_idx != -1: er_indices = [corrupted_field_idx]
        elif corrupted_indices: er_indices = list(corrupted_indices)

        if er_indices:
            t = len(er_indices)
            if len(failed) < t: return FSC_ERR_BOUNDS

            # ATTEMPT NATIVE MULTI-FAULT ACCELERATION
            if is_native_available() and t >= 1 and len(failed) >= t:
                 p_set = {self.constraints[i].modulus for i in failed}
                 if len(p_set) == 1 and list(p_set)[0] is not None:
                     p = list(p_set)[0]
                     targets_list = []
                     for i in failed:
                         if self.constraints[i].is_fiber: targets_list.append(record_idx % (self.constraints[i].modulus or 251))
                         elif self.constraints[i].target is not None: targets_list.append(self.constraints[i].target)
                         else: targets_list.append(record[self.constraints[i].stored_field_idx])

                     all_weights = np.zeros((len(failed), len(self.data_fields)), dtype=np.int32)
                     for i, f_idx in enumerate(failed): all_weights[i] = self.constraints[f_idx].weights.astype(np.int32)

                     is_uint8 = all(f.fmt == "B" for f in self.data_fields)
                     if is_uint8:
                         rec_data = data_np.astype(np.uint8).copy()
                         if native_heal_multi8(rec_data, all_weights.flatten(), np.array(targets_list, dtype=np.int64), np.array([p]*len(failed), dtype=np.int64), er_indices):
                             self.records[record_idx, :len(self.data_fields)] = rec_data.astype(np.int64)
                             fsc_audit_log("NATIVE_RECOVERY_KNOWN_8", 0, 0)
                             return FSC_SUCCESS
                     else:
                         rec_data = data_np.astype(np.int64).copy()
                         if native_heal_multi64(rec_data, all_weights.flatten(), np.array(targets_list, dtype=np.int64), np.array([p]*len(failed), dtype=np.int64), er_indices):
                             self.records[record_idx, :len(self.data_fields)] = rec_data
                             fsc_audit_log("NATIVE_RECOVERY_KNOWN", 0, 0)
                             return FSC_SUCCESS

            # FALLBACK TO COMBINATORIAL SUBSET SOLVING
            for c_subset in combinations(failed, t):
                p = self.constraints[c_subset[0]].modulus
                if not p:
                    A = self._weight_matrix[list(c_subset)][:, list(er_indices)]
                    b = [syndromes[i] for i in c_subset]
                    try:
                        sol = np.linalg.solve(A, np.array(b))
                        for idx, ci in enumerate(er_indices):
                            mag = int(round(sol[idx]))
                            self.records[record_idx, ci] = int(data_np[ci] + mag)
                            fsc_audit_log("RECOVERY_KNOWN", ci, mag)
                        return FSC_SUCCESS
                    except Exception: continue
                else:
                    A = self._weight_matrix[list(c_subset)][:, list(er_indices)] % p
                    b = [syndromes[i] % p for i in c_subset]
                    sol = solve_linear_system(A, b, p)
                    if sol:
                        for idx, ci in enumerate(er_indices):
                            mag = int(sol[idx])
                            self.records[record_idx, ci] = (int(data_np[ci]) + mag) % p
                            fsc_audit_log("RECOVERY_KNOWN_MOD", ci, mag)
                        return FSC_SUCCESS
            return FSC_ERR_INVALID

        # BLIND RECOVERY
        if passed.size > 0:
            passed_weights = self._weight_matrix[passed]
            is_possible = np.all(passed_weights == 0, axis=0)
            t1_candidates = np.where(is_possible)[0].tolist()
        else: t1_candidates = list(range(len(self.data_fields)))

        for t in range(1, len(failed) + 1):
            if t == 1:
                # Attempt native single-fault recovery first
                if is_native_available() and len(failed) >= 1:
                    i1 = failed[0]
                    p1 = self.constraints[i1].modulus or 0
                    target = (record_idx % (self.constraints[i1].modulus or 251) if self.constraints[i1].is_fiber else (self.constraints[i1].target if self.constraints[i1].target is not None else record[self.constraints[i1].stored_field_idx]))

                    for ci in t1_candidates:
                        if self.constraints[i1].weights[ci] == 0: continue
                        mag = native_heal_single64(data_np, self.constraints[i1].weights.astype(np.int32), target, p1, ci)
                        orig_val = self.records[record_idx, ci]
                        self.records[record_idx, ci] = mag
                        if self._verify_record(record_idx, self.records[record_idx, :len(self.data_fields)]):
                             fsc_audit_log("NATIVE_RECOVERY_BLIND_SINGLE", ci, 0)
                             return FSC_SUCCESS
                        self.records[record_idx, ci] = orig_val

                cand_indices = np.array(t1_candidates)
                if len(cand_indices) > 0:
                    i1 = failed[0]; p1 = self.constraints[i1].modulus; s1 = syndromes[i1]; w1 = self._weight_matrix[i1, cand_indices]
                    if p1:
                        w1_mod = w1 % p1; nonzero = (w1_mod != 0)
                        if np.any(nonzero):
                            cands = cand_indices[nonzero]; w_subset = w1_mod[nonzero]
                            is_valid = np.ones(len(cands), dtype=bool)
                            for i_other in failed[1:]:
                                p_other = self.constraints[i_other].modulus
                                if p_other == p1:
                                    s_other = syndromes[i_other]; w_other = self._weight_matrix[i_other, cands]
                                    is_valid &= ((s1 * w_other) % p1 == (s_other * w_subset) % p1)
                                else: is_valid[:] = False; break
                            if np.any(is_valid):
                                ci = cands[np.argmax(is_valid)]
                                try:
                                    mag = (s1 * pow(int(self._weight_matrix[i1, ci] % p1), -1, p1)) % p1
                                    self.records[record_idx, ci] = (int(data_np[ci]) + mag) % p1
                                    fsc_audit_log("RECOVERY_BLIND_MOD_VEC", ci, mag)
                                    return FSC_SUCCESS
                                except ValueError: pass
                    else:
                        nonzero = (w1 != 0)
                        if np.any(nonzero):
                            cands = cand_indices[nonzero]; w_subset = w1[nonzero]
                            is_valid = (s1 % w_subset == 0)
                            if np.any(is_valid):
                                cands = cands[is_valid]; w_sub2 = w_subset[is_valid]
                                for i_other in failed[1:]:
                                    s_other = syndromes[i_other]; w_other = self._weight_matrix[i_other, cands]
                                    is_valid &= (s1 * w_other == s_other * w_sub2)
                                if np.any(is_valid):
                                    ci = cands[np.argmax(is_valid)]
                                    mag = s1 // int(self._weight_matrix[i1, ci])
                                    self.records[record_idx, ci] = int(data_np[ci] + mag)
                                    fsc_audit_log("RECOVERY_BLIND_VEC", ci, mag)
                                    return FSC_SUCCESS

            # MULTI-FAULT BLIND SEARCH
            search_space = range(len(self.data_fields))
            for combo in combinations(search_space, t):
                for c_subset in combinations(failed, t):
                    p = self.constraints[c_subset[0]].modulus
                    if not p:
                        A = self._weight_matrix[list(c_subset)][:, list(combo)]
                        b = [syndromes[i] for i in c_subset]
                        try:
                            sol = np.linalg.solve(A, np.array(b))
                            test_v = data_np.copy()
                            for idx, ci in enumerate(combo): test_v[ci] = int(data_np[ci] + round(sol[idx]))
                            if self._verify_record(record_idx, test_v):
                                for idx, ci in enumerate(combo):
                                    mag = int(round(sol[idx]))
                                    self.records[record_idx, ci] = test_v[ci]
                                    fsc_audit_log("RECOVERY_BLIND", ci, mag)
                                return FSC_SUCCESS
                        except Exception: continue
                    else:
                        A = self._weight_matrix[list(c_subset)][:, list(combo)] % p
                        b = [syndromes[i] % p for i in c_subset]
                        sol = solve_linear_system(A, b, p)
                        if sol:
                            test_v = data_np.copy()
                            for idx, ci in enumerate(combo): test_v[ci] = (int(data_np[ci]) + sol[idx]) % p
                            if self._verify_record(record_idx, test_v):
                                for idx, ci in enumerate(combo):
                                    mag = int(sol[idx])
                                    self.records[record_idx, ci] = test_v[ci]
                                    fsc_audit_log("RECOVERY_BLIND_MOD", ci, mag)
                                return FSC_SUCCESS
        return FSC_ERR_INVALID

    def verify_all_records(self) -> np.ndarray:
        if not self.constraints or len(self.records) == 0: return np.ones(len(self.records), dtype=bool)
        data_matrix = self.records[:, :len(self.data_fields)]
        record_indices = np.arange(len(self.records)).reshape(-1, 1)
        fiber_mod = np.where(self._moduli != 0, self._moduli, 251)
        fiber_targets = record_indices % fiber_mod; fixed_targets = self._fixed_targets; stored_targets = self.records[:, self._stored_indices]
        targets = np.where(self._is_fiber, fiber_targets, np.where(self._has_fixed_target, fixed_targets, stored_targets))
        actuals = data_matrix @ self._weight_matrix.T
        for mod_val in np.unique(self._moduli):
            if mod_val == 0: continue
            mask = (self._moduli == mod_val); actuals[:, mask] %= mod_val
        return np.all(actuals == targets, axis=1)

    def get_data(self) -> List[List[int]]:
        return self.records[:, :len(self.data_fields)].tolist()
