"""
FSC: Forward Sector Correction - Hardened Recursive Implementation (v5)
Copyright (C) 2024 FSC Core Team. All Rights Reserved.

PUBLIC LICENSE: GNU Affero General Public License (AGPLv3)
COMMERCIAL LICENSE: Required for proprietary/enterprise use.

PATENT PENDING: Industrial applications of these algebraic primitives
for database pages, kernel block devices, and network protocols.
"""
import os
import numpy as np
import struct, io
from typing import List, Any, Optional
from collections import defaultdict
from itertools import combinations
from fsc.fsc_framework import solve_linear_system, gf_inv
from fsc.fsc_native import is_native_available, native_calculate_sum8, native_calculate_sum64, native_heal_single64, native_heal_multi64, native_heal_multi8, native_audit_log, FSC_SUCCESS, FSC_ERR_SINGULAR, FSC_ERR_BOUNDS, FSC_ERR_INVALID

FSC_COMMERCIAL_BUILD = False
MAX_FIELDS = 1024
MAX_CONSTRAINTS = 1024
MAX_RECORDS = 10000000

def fsc_audit_log(event_type: str, index: int, magnitude: int):
    if FSC_COMMERCIAL_BUILD:
         print(f"[COMMERCIAL-AUDIT] EVENT: {event_type} | OFFSET: {index} | MAGNITUDE: {magnitude}")

class FSCField:
    TYPES = {'UINT8': 'B', 'UINT16': 'H', 'UINT32': 'I', 'UINT64': 'Q', 'INT16': 'h', 'INT32': 'i', 'INT64': 'q'}
    def __init__(self, name: str, ftype: str):
        self.name = name[:16].ljust(16)
        self.ftype = ftype
        self.fmt = self.TYPES[ftype]

class FSCConstraint:
    def __init__(self, weights: Any, target: Optional[int] = None, is_fiber: bool = False, label: str = "", modulus: Optional[int] = None):
        self.weights = weights
        self.target = target
        self.is_fiber = is_fiber
        self.label = label
        self.modulus = modulus
        self.stored_field_idx = -1

class FSCSchema:
    def __init__(self, fields: List[FSCField]):
        self.data_fields = fields
        self.constraints: List[FSCConstraint] = []
        self.all_fields = list(fields)
    def add_constraint(self, weights: List[int], target: Optional[int] = None, is_fiber: bool = False, modulus: Optional[int] = None, label: str = ""):
        c = FSCConstraint(np.array(weights, dtype=np.int64), target, is_fiber=is_fiber, modulus=modulus, label=label)
        if target is None and not is_fiber:
            c.stored_field_idx = len(self.all_fields)
            self.all_fields.append(FSCField(f"stored_{len(self.constraints)}", "INT64"))
        self.constraints.append(c)

class FSCWriter:
    def __init__(self, schema: FSCSchema):
        self.schema = schema
        self._record_list = []
        self.all_fields = list(schema.all_fields)
    def add_record(self, data: Any): self.add_records([data])
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
            nd = len(self.schema.data_fields); nc = len(self.schema.constraints); ns = len(self.schema.all_fields) - nd; nr = len(records)
            meta = [nd, nc, ns, nr]
            s1 = sum(meta) % (2**32); s2 = sum((i+1)*v for i,v in enumerate(meta)) % (2**32)
            header = struct.pack(">B HH B I II", 5, nd, nc, ns, nr, s1, s2)
            f.write(header)
            for field in self.schema.data_fields:
                f.write(struct.pack(">16s", field.name.encode('ascii')))
                f_idx = list(FSCField.TYPES.keys()).index(field.ftype)
                f.write(struct.pack(">B", f_idx))
            c_block = io.BytesIO()
            for c in self.schema.constraints:
                ctype = 1 if c.is_fiber else 0
                c_block.write(struct.pack(">B q b q", ctype, c.target or 0, c.stored_field_idx, c.modulus or 0))
                c_block.write(struct.pack(">" + "b" * nd, *c.weights.tolist()))
            c_data = c_block.getvalue(); f.write(c_data)
            dt_list = [(f.name, ">" + f.fmt) for f in self.schema.all_fields]
            structured_recs = np.zeros(len(records), dtype=dt_list)
            for i, f_info in enumerate(self.schema.all_fields): structured_recs[f_info.name] = records[:, i]
            f.write(structured_recs.tobytes())
            P_META = 2305843009213693951; c_ints = np.frombuffer(c_data, dtype=np.uint8).astype(np.int64)
            p1 = int(np.sum(c_ints) % (2**32)); p2 = int(np.sum(c_ints * np.arange(1, len(c_ints)+1)) % P_META)
            f.write(struct.pack(">I I Q", 0xDEADC0DE, p1, p2))

class FSCReader:
    def __init__(self, filename: str):
        self.filename = filename
        self.data_fields = []; self.all_fields = []; self.constraints = []
        self.records = np.array([], dtype=np.int64)
        self._read_file()
    def get_data(self) -> List[List[int]]: return self.records[:, :len(self.data_fields)].tolist()
    def _read_file(self):
        with open(self.filename, "rb") as f:
            magic = f.read(4)
            if magic == b"FSC4":
                header_data = f.read(18)
                ver, nd, nc, ns, nr, s1, s2 = struct.unpack(">B HH B I II", header_data)
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
                if ver == 5:
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
                ptr = 0
                for _ in range(nc):
                    ct, tg, si, mo = struct.unpack(">B q b q", c_raw[ptr:ptr+18]); ptr += 18
                    weights = list(struct.unpack(">" + "b"*nd, c_raw[ptr:ptr+nd])); ptr += nd
                    c = FSCConstraint(np.array(weights, dtype=np.int64), tg if ct==1 or tg!=0 or si==-1 else None, is_fiber=(ct==1), modulus=mo if mo!=0 else None)
                    c.stored_field_idx = si; self.constraints.append(c)
                f.seek(c_start + c_len); dt_list = [(f.name, ">" + f.fmt) for f in self.all_fields]
                if nr > 0:
                    raw = f.read(np.dtype(dt_list).itemsize * nr)
                    structured = np.frombuffer(raw, dtype=np.dtype(dt_list))
                    self.records = np.zeros((nr, len(self.all_fields)), dtype=np.int64)
                    for i, f_info in enumerate(self.all_fields): self.records[:, i] = structured[f_info.name]
                else: self.records = np.empty((0, len(self.all_fields)), dtype=np.int64)
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
            target = (r_idx % (c.modulus or 251)) if c.is_fiber else (c.target if c.target is not None else rec[c.stored_field_idx])
            actual = np.dot(data, c.weights)
            if c.modulus: actual %= c.modulus
            if actual != target: return False
        return True
    def verify_and_heal(self, r_idx: int, corrupted_field_idx: int = -1, corrupted_indices: List[int] = None) -> int:
        if corrupted_indices: er_indices = list(corrupted_indices)
        elif corrupted_field_idx != -1: er_indices = [corrupted_field_idx]
        else: er_indices = None
        rec = self.records[r_idx]; data_np = rec[:len(self.data_fields)].copy()
        failed = []; syndromes = []
        for i, c in enumerate(self.constraints):
            target = (r_idx % (c.modulus or 251)) if c.is_fiber else (c.target if c.target is not None else rec[c.stored_field_idx])
            actual = np.dot(data_np, c.weights)
            if c.modulus: actual %= c.modulus; synd = (target - actual) % c.modulus
            else: synd = target - actual
            if synd != 0: failed.append(i); syndromes.append(synd)
            else: syndromes.append(0)
        if not failed: return FSC_SUCCESS
        syndromes = np.array(syndromes, dtype=np.int64); failed = np.array(failed, dtype=np.int32)
        if er_indices:
            for t in range(1, len(failed) + 1):
                if t > len(er_indices): break
                for c_subset in combinations(failed, t):
                    if len(c_subset) < len(er_indices): continue
                    p = self.constraints[c_subset[0]].modulus
                    A = self._weight_matrix[list(c_subset)][:, list(er_indices)]
                    if p:
                        sol = solve_linear_system(A % p, [syndromes[i] % p for i in c_subset], p)
                        if sol:
                            for idx, ci in enumerate(er_indices): self.records[r_idx, ci] = (int(data_np[ci]) + sol[idx]) % p
                            return FSC_SUCCESS
                    else:
                        try:
                            sol = np.linalg.solve(A, [syndromes[i] for i in c_subset])
                            sol_l = sol.tolist()
                            for idx, ci in enumerate(er_indices): self.records[r_idx, ci] = int(data_np[ci] + round(sol_l[idx]))
                            return FSC_SUCCESS
                        except: continue
            return FSC_ERR_INVALID
        i1 = failed[0]; p1 = self.constraints[i1].modulus; s1 = syndromes[i1]
        for ci in range(len(self.data_fields)):
            w1 = self.constraints[i1].weights[ci]
            if w1 == 0: continue
            if p1:
                try:
                    mag = (s1 * gf_inv(int(w1 % p1), p1)) % p1
                    test_v = data_np.copy(); test_v[ci] = (test_v[ci] + mag) % p1
                    if self._verify_record(r_idx, test_v): self.records[r_idx, ci] = test_v[ci]; return FSC_SUCCESS
                except: continue
            else:
                if s1 % w1 == 0:
                    mag = s1 // w1; test_v = data_np.copy(); test_v[ci] += mag
                    if self._verify_record(r_idx, test_v): self.records[r_idx, ci] = test_v[ci]; return FSC_SUCCESS
        return FSC_ERR_INVALID
    def verify_all_records(self) -> np.ndarray:
        if not self.constraints or len(self.records) == 0: return np.ones(len(self.records), dtype=bool)
        data_matrix = self.records[:, :len(self.data_fields)]; record_indices = np.arange(len(self.records)).reshape(-1, 1)
        fiber_mod = np.where(self._moduli != 0, self._moduli, 251); fiber_targets = record_indices % fiber_mod
        targets = np.where(self._is_fiber, fiber_targets, np.where(self._has_fixed_target, self._fixed_targets, self.records[:, self._stored_indices]))
        actuals = data_matrix @ self._weight_matrix.T
        for mod_val in np.unique(self._moduli):
            if mod_val == 0: continue
            mask = (self._moduli == mod_val); actuals[:, mask] %= mod_val
        return np.all(actuals == targets, axis=1)
