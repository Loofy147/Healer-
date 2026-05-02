"""
FSC: Forward Sector Correction - Hardened Recursive Implementation (v6)
Copyright (C) 2024 FSC Core Team. All Rights Reserved.
"""
from fsc.enterprise.fsc_config import SovereignConfig
from fsc.advanced.fsc_manifold import LayeredManifold
import os
import numpy as np
import struct, io
from typing import List, Any, Optional, Tuple
from collections import defaultdict
from itertools import combinations
from fsc.core.fsc_framework import solve_linear_system, gf_inv
from fsc.core.fsc_native import is_native_available, native_calculate_sum8, native_calculate_sum64, native_heal_single64, native_heal_single8, native_heal_multi64, native_heal_multi8, native_audit_log, FSC_SUCCESS, FSC_ERR_SINGULAR, FSC_ERR_BOUNDS, FSC_ERR_INVALID

def fsc_audit_log(event_type: str, index: int, magnitude: int):
    if is_native_available(): native_audit_log(event_type, index, magnitude)

class FSCField:
    TYPES = {"INT64": ("q", 8), "UINT8": ("B", 1), "INT32": ("i", 4), "UINT32": ("I", 4), "UINT16": ("H", 2), "FLOAT64": ("d", 8)}
    def __init__(self, name: str, ftype: str):
        self.name = name; self.ftype = ftype; self.fmt, self.size = self.TYPES[ftype]

class FSCConstraint:
    def __init__(self, weights: Any, target: Optional[int] = None, is_fiber: bool = False, label: str = "", modulus: Optional[int] = None):
        self.weights = weights; self.target = target; self.is_fiber = is_fiber; self.label = label; self.modulus = modulus
        self.stored_field_idx = -1

class FSCSchema:
    def __init__(self, fields: List[FSCField]):
        self.fields = fields; self.constraints = []
        self.data_fields = fields
    def add_constraint(self, weights: List[int], target: Optional[int] = None, is_fiber: bool = False, modulus: Optional[int] = None, label: str = ""):
        self.constraints.append(FSCConstraint(np.array(weights, dtype=np.int64), target, is_fiber, label, modulus))

class FSCWriter:
    def __init__(self, schema: FSCSchema):
        self.schema = schema; self.records = []
        self.use_layered = False
        self.layered_manifold = None

    def enable_layered_protection(self):
        self.use_layered = True
        self.layered_manifold = LayeredManifold()

    def add_record(self, data: Any):
        self.add_records([data])

    def add_records(self, data: Any):
        for row in data:
            rec = list(row)
            for c in self.schema.constraints:
                if c.target is None and not c.is_fiber:
                    weights = c.weights[:len(row)]
                    res = np.dot(row, weights)
                    if c.modulus: res %= c.modulus
                    rec.append(res)
            self.records.append(rec)

    def write(self, filename: str):
        with open(filename, "wb") as f:
            ver = 6 if self.use_layered else 5
            nd = len(self.schema.fields)
            nc = len(self.schema.constraints)
            ns = len([c for c in self.schema.constraints if c.target is None and not c.is_fiber])
            nr = len(self.records)
            meta = [nd, nc, ns, nr]
            s1 = sum(meta) % (2**32)
            header = struct.pack(">4s B HH B I II", b"FSC4", ver, nd, nc, ns, nr, s1, 0)
            f.write(header)
            for field in self.schema.fields:
                f.write(struct.pack(">16s B", field.name.encode('ascii')[:16].ljust(16), list(FSCField.TYPES.keys()).index(field.ftype)))
            c_data = bytearray()
            si_ptr = nd
            for c in self.schema.constraints:
                if c.target is None and not c.is_fiber: c.stored_field_idx = si_ptr; si_ptr += 1
                c_data += struct.pack(">B q b q", 1 if c.is_fiber else 0, c.target or 0, c.stored_field_idx, c.modulus or 0)
                c_data += struct.pack(">" + "b"*nd, *[int(w) for w in c.weights[:nd]])
            f.write(c_data)
            all_fields = list(self.schema.fields)
            for i in range(ns): all_fields.append(FSCField(f"stored_{i}", "INT64"))
            fmt = ">" + "".join(f.fmt for f in all_fields)
            for r in self.records: f.write(struct.pack(fmt, *r))

            if self.use_layered:
                for r in self.records:
                    data_np = np.array(r[:nd], dtype=np.uint8)
                    syndromes = self.layered_manifold.seal_record(data_np)
                    for s in syndromes:
                        f.write(struct.pack(">q", s))

            P_META = 2305843009213693951; c_ints = np.frombuffer(c_data, dtype=np.uint8).astype(np.int64)
            p1 = int(np.sum(c_ints) % (2**32)); p2 = int(np.sum(c_ints * np.arange(1, len(c_ints)+1)) % P_META)
            f.write(struct.pack(">I I Q", 0xDEADC0DE, p1, p2))

class FSCReader:
    def __init__(self, filename: str):
        self.filename = filename
        self.data_fields = []; self.all_fields = []; self.constraints = []
        self.records = np.array([], dtype=np.int64)
        self.layered_syndromes = []
        self.ver = 0
        self._read_file()

    def get_data(self) -> List[List[int]]: return self.records[:, :len(self.data_fields)].tolist()

    def _read_file(self):
        with open(self.filename, "rb") as f:
            magic = f.read(4)
            if magic == b"FSC4":
                header_data = f.read(18)
                ver, nd, nc, ns, nr, s1, s2 = struct.unpack(">B HH B I II", header_data)
                self.ver = ver
                meta = [nd, nc, ns, nr]
                if sum(meta) % (2**32) != s1: raise ValueError("Header Corruption")
                ftypes = list(FSCField.TYPES.keys())
                for _ in range(nd):
                    n_b = struct.unpack(">16s", f.read(16))[0]; name = n_b.decode('ascii').strip()
                    ft_idx = struct.unpack(">B", f.read(1))[0]
                    self.data_fields.append(FSCField(name, ftypes[ft_idx]))
                self.all_fields = list(self.data_fields)
                for i in range(ns): self.all_fields.append(FSCField(f"stored_{i}", "INT64"))
                c_start = f.tell(); c_len = nc * (18 + nd); c_raw = bytearray(f.read(c_len))

                f.seek(0, 2); f_end = f.tell(); f.seek(f_end - 16); footer = f.read(16)
                if len(footer) == 16:
                    f_mag, f_p1, f_p2 = struct.unpack(">I I Q", footer)
                    if f_mag == 0xDEADC0DE:
                        P_META = 2305843009213693951; c_ints = np.frombuffer(c_raw, dtype=np.uint8).astype(np.int64)
                        a_p1 = int(np.sum(c_ints) % (2**32)); a_p2 = int(np.sum(c_ints * np.arange(1, len(c_ints)+1)) % P_META)
                        if a_p1 != f_p1 or a_p2 != f_p2:
                            fsc_audit_log("META_CORRUPTION", 0, 0)
                            s1_v = (f_p1 - a_p1) % (2**32); s2_v = (f_p2 - a_p2) % P_META
                            if s1_v != 0:
                                try:
                                    loc = (s2_v * gf_inv(s1_v, P_META)) % P_META
                                    if 1 <= loc <= len(c_ints):
                                        idx = int(loc - 1); c_raw[idx] = (c_raw[idx] + s1_v) % 256
                                        fsc_audit_log("META_HEALED", idx, s1_v)
                                except: pass

                f.seek(c_start + c_len)
                ptr = 0
                for _ in range(nc):
                    ct, tg, si, mo = struct.unpack(">B q b q", c_raw[ptr:ptr+18]); ptr += 18
                    weights = list(struct.unpack(">" + "b"*nd, c_raw[ptr:ptr+nd])); ptr += nd
                    c = FSCConstraint(np.array(weights, dtype=np.int64), tg if ct==1 or tg!=0 or si==-1 else None, is_fiber=(ct==1), modulus=mo if mo!=0 else None)
                    c.stored_field_idx = si; self.constraints.append(c)

                dt_list = [(f.name, ">" + f.fmt) for f in self.all_fields]
                if nr > 0:
                    raw = f.read(np.dtype(dt_list).itemsize * nr)
                    structured = np.frombuffer(raw, dtype=np.dtype(dt_list))
                    self.records = np.zeros((nr, len(self.all_fields)), dtype=np.int64)
                    for i, f_info in enumerate(self.all_fields): self.records[:, i] = structured[f_info.name]
                else: self.records = np.empty((0, len(self.all_fields)), dtype=np.int64)

                if ver == 6:
                    for _ in range(nr):
                        s1, s2 = struct.unpack(">q q", f.read(16))
                        self.layered_syndromes.append([s1, s2])

                if self.constraints:
                    self._weight_matrix = np.array([c.weights for c in self.constraints], dtype=np.int64)
                    self._moduli = np.array([c.modulus if c.modulus is not None else 0 for c in self.constraints], dtype=np.int64)
                    self._fixed_targets = np.array([c.target if c.target is not None else 0 for c in self.constraints], dtype=np.int64)
                    self._has_fixed_target = np.array([c.target is not None for c in self.constraints], dtype=bool)
                    self._stored_indices = np.array([c.stored_field_idx if c.stored_field_idx != -1 else 0 for c in self.constraints], dtype=np.int32)
                    self._is_fiber = np.array([c.is_fiber for c in self.constraints], dtype=bool)

    def _verify_record(self, r_idx: int, data: np.ndarray) -> bool:
        rec = self.records[r_idx]
        for i, c in enumerate(self.constraints):
            target = (r_idx % (c.modulus or SovereignConfig.get_manifold_params()["modulus"])) if c.is_fiber else (c.target if c.target is not None else rec[c.stored_field_idx])
            actual = np.dot(data, c.weights)
            if c.modulus: actual %= c.modulus
            if actual != target: return False

        if self.ver == 6:
            lm = LayeredManifold()
            if not lm.verify_record(data.astype(np.uint8), self.layered_syndromes[r_idx]):
                return False
        return True

    def verify_and_heal(self, r_idx: int, corrupted_field_idx: int = -1, corrupted_indices: List[int] = None) -> int:
        if corrupted_indices: er_indices = list(corrupted_indices)
        elif corrupted_field_idx != -1: er_indices = [corrupted_field_idx]
        else: er_indices = None
        rec = self.records[r_idx]; data_np = rec[:len(self.data_fields)].copy()

        syndromes = []
        failed = []
        for i, c in enumerate(self.constraints):
            target = (r_idx % (c.modulus or SovereignConfig.get_manifold_params()["modulus"])) if c.is_fiber else (c.target if c.target is not None else rec[c.stored_field_idx])
            actual = np.dot(data_np, c.weights)
            if c.modulus: actual %= c.modulus; synd = (target - actual) % c.modulus
            else: synd = target - actual
            syndromes.append(synd)
            if synd != 0: failed.append(i)

        if not failed: return FSC_SUCCESS

        syndromes = np.array(syndromes, dtype=np.int64)
        failed = np.array(failed, dtype=np.int32)

        if er_indices:
            if is_native_available() and len(er_indices) <= len(failed):
                p_main = int(self._moduli[failed[0]])
                if all(int(self._moduli[f_idx]) == p_main for f_idx in failed):
                    weights_subset = self._weight_matrix[failed].flatten().astype(np.int32)
                    targets_subset = np.array([self.constraints[f_idx].target if self.constraints[f_idx].target is not None else self.records[r_idx, self.constraints[f_idx].stored_field_idx] for f_idx in failed], dtype=np.int64)
                    moduli_subset = np.array([p_main] * len(failed), dtype=np.int64)
                    test_data = data_np.copy()
                    if native_heal_multi64(test_data, weights_subset, targets_subset, moduli_subset, er_indices):
                        if self._verify_record(r_idx, test_data):
                            self.records[r_idx, :len(self.data_fields)] = test_data
                            return FSC_SUCCESS
            for t in range(1, len(failed) + 1):
                if t > len(er_indices): break
                for c_subset in combinations(failed, t):
                    if len(c_subset) < len(er_indices): continue
                    p = int(self._moduli[c_subset[0]])
                    A = self._weight_matrix[list(c_subset)][:, list(er_indices)]
                    if p > 0:
                        sol = solve_linear_system(A % p, [syndromes[i] % p for i in c_subset], p)
                        if sol:
                            test_v = data_np.copy()
                            for idx, ci in enumerate(er_indices): test_v[ci] = (int(data_np[ci]) + sol[idx]) % p
                            if self._verify_record(r_idx, test_v):
                                for idx, ci in enumerate(er_indices): self.records[r_idx, ci] = test_v[ci]
                                return FSC_SUCCESS
                    else:
                        try:
                            sol = np.linalg.solve(A, [syndromes[i] for i in c_subset])
                            sol_l = sol.tolist()
                            test_v = data_np.copy()
                            for idx, ci in enumerate(er_indices): test_v[ci] = int(data_np[ci] + round(sol_l[idx]))
                            if self._verify_record(r_idx, test_v):
                                for idx, ci in enumerate(er_indices): self.records[r_idx, ci] = test_v[ci]
                                return FSC_SUCCESS
                        except: continue
            return FSC_ERR_INVALID

        i1 = failed[0]; p1 = int(self._moduli[i1]); s1 = syndromes[i1]
        w1 = self._weight_matrix[i1]

        if p1 > 0:
            cand_mask = (w1 % p1 != 0)
            for f_idx in failed[1:]:
                pj = int(self._moduli[f_idx])
                if pj == p1:
                    sj = syndromes[f_idx]
                    wj = self._weight_matrix[f_idx]
                    cand_mask &= ((sj * w1) % p1 == (s1 * wj) % p1)

            cand_indices = np.where(cand_mask)[0]
            for ci in cand_indices:
                try:
                    mag = (s1 * gf_inv(int(w1[ci] % p1), p1)) % p1
                    test_v = data_np.copy(); test_v[ci] = (test_v[ci] + mag) % p1
                    if self._verify_record(r_idx, test_v): self.records[r_idx, ci] = test_v[ci]; return FSC_SUCCESS
                except: continue
        else:
            cand_indices = np.where(w1 != 0)[0]
            for ci in cand_indices:
                ww1 = w1[ci]
                if s1 % ww1 == 0:
                    mag = s1 // ww1; test_v = data_np.copy(); test_v[ci] += mag
                    if self._verify_record(r_idx, test_v): self.records[r_idx, ci] = test_v[ci]; return FSC_SUCCESS
        return FSC_ERR_INVALID

    def verify_all_records(self) -> np.ndarray:
        if not self.constraints or len(self.records) == 0: return np.ones(len(self.records), dtype=bool)
        data_matrix = self.records[:, :len(self.data_fields)]; record_indices = np.arange(len(self.records)).reshape(-1, 1)
        fiber_mod = np.where(self._moduli != 0, self._moduli, SovereignConfig.get_manifold_params()["modulus"]); fiber_targets = record_indices % fiber_mod
        targets = np.where(self._is_fiber, fiber_targets, np.where(self._has_fixed_target, self._fixed_targets, self.records[:, self._stored_indices]))
        actuals = data_matrix @ self._weight_matrix.T
        for mod_val in np.unique(self._moduli):
            if mod_val == 0: continue
            mask = (self._moduli == mod_val); actuals[:, mask] %= mod_val
        valid = np.all(actuals == targets, axis=1)

        if self.ver == 6:
            lm = LayeredManifold()
            for r_idx in range(len(self.records)):
                if valid[r_idx]:
                    if not lm.verify_record(self.records[r_idx, :len(self.data_fields)].astype(np.uint8), self.layered_syndromes[r_idx]):
                        valid[r_idx] = False
        return valid
