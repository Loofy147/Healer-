import numpy as np
import struct
import io
from typing import List, Dict, Any, Tuple, Optional
from itertools import combinations
from fsc_framework import solve_linear_system

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
        self.name = name.ljust(16)[:16]
        self.ftype = ftype
        self.fmt = self.TYPES[ftype]

class FSCConstraint:
    """An algebraic constraint: sum(w_i * v_i) == target."""
    def __init__(self, weights: Any, target: Optional[int] = None,
                 is_fiber: bool = False, label: str = "", modulus: Optional[int] = None):
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
                       is_fiber: bool = False, label: str = "", modulus: Optional[int] = None):
        if len(weights) != len(self.data_fields):
            raise ValueError(f"Constraint weights ({len(weights)}) must match data fields ({len(self.data_fields)})")
        c = FSCConstraint(np.array(weights, dtype=np.int64), target, is_fiber, label, modulus)
        if not is_fiber and target is None:
            field_name = label if label else f"sum_{len(self.constraints)}"
            inv_field = FSCField(field_name, "INT64")
            self.all_fields.append(inv_field)
            c.stored_field_idx = len(self.all_fields) - 1
        self.constraints.append(c)

    @property
    def record_fmt(self) -> str:
        return ">" + "".join(f.fmt for f in self.all_fields)

class FSCWriter:
    def __init__(self, schema: FSCSchema):
        self.schema = schema
        self.records = np.empty((0, len(self.schema.all_fields)), dtype=np.int64)

    def add_record(self, data: List[int]):
        self.add_records(np.array([data], dtype=np.int64))

    def add_records(self, data_matrix: Any):
        source_np = np.atleast_2d(np.array(data_matrix, dtype=np.int64))
        n_recs = source_np.shape[0]
        n_data = len(self.schema.data_fields)
        n_all = len(self.schema.all_fields)
        full_recs = np.zeros((n_recs, n_all), dtype=np.int64)
        full_recs[:, :n_data] = source_np[:, :n_data]
        for c in self.schema.constraints:
            if not c.is_fiber and c.target is None:
                invariants = source_np[:, :n_data] @ c.weights
                if c.modulus: invariants %= c.modulus
                full_recs[:, c.stored_field_idx] = invariants
        self.records = np.vstack([self.records, full_recs]) if self.records.size else full_recs

    def write(self, filename: str):
        with open(filename, "wb") as f:
            f.write(b"FSC1")
            f.write(struct.pack(">B HB B I", 3, len(self.schema.data_fields),
                                len(self.schema.constraints),
                                len(self.schema.all_fields) - len(self.schema.data_fields),
                                len(self.records)))
            for field in self.schema.data_fields:
                f.write(field.name.encode('ascii'))
                f.write(struct.pack(">B", list(FSCField.TYPES.keys()).index(field.ftype)))
            for c in self.schema.constraints:
                f.write(struct.pack(">B q b q", 1 if c.is_fiber else 0, c.target or 0, c.stored_field_idx, c.modulus or 0))
                f.write(struct.pack(">" + "b"*len(c.weights), *c.weights.tolist()))
            s = struct.Struct(self.schema.record_fmt)
            for record in self.records: f.write(s.pack(*record))

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
            if magic != b"FSC1": raise ValueError("Invalid magic")
            version, n_data, n_cons, n_stored, n_recs = struct.unpack(">B HB B I", f.read(9))
            ftype_list = list(FSCField.TYPES.keys())
            for _ in range(n_data):
                name = f.read(16).decode('ascii').strip()
                self.data_fields.append(FSCField(name, ftype_list[struct.unpack(">B", f.read(1))[0]]))
            self.all_fields = list(self.data_fields)
            for i in range(n_stored): self.all_fields.append(FSCField(f"stored_{i}", "INT64"))
            for _ in range(n_cons):
                ctype, target, s_idx, modulus = struct.unpack(">B q b q", f.read(18))
                weights = list(struct.unpack(">" + "b"*n_data, f.read(n_data)))
                c = FSCConstraint(np.array(weights, dtype=np.int64), target if ctype == 1 or target != 0 or s_idx == -1 else None, is_fiber=(ctype == 1), modulus=modulus if modulus != 0 else None)
                c.stored_field_idx = s_idx
                self.constraints.append(c)
            s = struct.Struct(">"+"".join(f.fmt for f in self.all_fields))
            recs = [s.unpack(f.read(s.size)) for _ in range(n_recs)]
            self.records = np.array(recs, dtype=np.int64) if recs else np.empty((0, len(self.all_fields)), dtype=np.int64)

    def verify_and_heal(self, record_idx: int, corrupted_field_idx: int = -1, corrupted_indices: List[int] = None) -> bool:
        record = self.records[record_idx]
        data_np = record[:len(self.data_fields)]
        failed = []; syndromes = {}
        for i, c in enumerate(self.constraints):
            target = record_idx % (c.modulus or 251) if c.is_fiber else (c.target if c.target is not None else record[c.stored_field_idx])
            actual = int(np.dot(c.weights, data_np))
            if c.modulus: actual %= c.modulus
            if actual != target:
                failed.append(i); syndromes[i] = (target - actual) % c.modulus if c.modulus else (target - actual)
        if not failed: return True

        erasure_indices = sorted(list(set(([corrupted_field_idx] if corrupted_field_idx != -1 else []) + (corrupted_indices or []))))

        if erasure_indices:
            t = len(erasure_indices)
            if len(failed) < t: return False
            for c_subset in combinations(failed, t):
                p = self.constraints[c_subset[0]].modulus
                if not p:
                    # Non-modular Fallback (Algebraic)
                    A = [[int(self.constraints[i].weights[ci]) for ci in erasure_indices] for i in c_subset]
                    b = [syndromes[i] for i in c_subset]
                    try:
                        sol = np.linalg.solve(np.array(A), np.array(b))
                        for idx, ci in enumerate(erasure_indices): self.records[record_idx, ci] = int(data_np[ci] + round(sol[idx]))
                        return True
                    except: continue

                A = [[int(self.constraints[i].weights[ci]) % p for ci in erasure_indices] for i in c_subset]
                b = [syndromes[i] % p for i in c_subset]
                sol = solve_linear_system(A, b, p)
                if sol:
                    for idx, ci in enumerate(erasure_indices): self.records[record_idx, ci] = (int(data_np[ci]) + sol[idx]) % p
                    return True
            return False

        # Blind Corruption Recovery
        for t in range(1, len(failed) + 1):
            for combo in combinations(range(len(self.data_fields)), t):
                for c_subset in combinations(failed, t):
                    p = self.constraints[c_subset[0]].modulus
                    if not p:
                        A = [[int(self.constraints[i].weights[ci]) for ci in combo] for i in c_subset]
                        b = [syndromes[i] for i in c_subset]
                        try:
                            sol = np.linalg.solve(np.array(A), np.array(b))
                            test_v = data_np.copy()
                            for idx, ci in enumerate(combo): test_v[ci] = int(data_np[ci] + round(sol[idx]))
                            if self._verify_record(record_idx, test_v):
                                for idx, ci in enumerate(combo): self.records[record_idx, ci] = test_v[ci]
                                return True
                        except: continue
                    else:
                        A = [[int(self.constraints[i].weights[ci]) % p for ci in combo] for i in c_subset]
                        b = [syndromes[i] % p for i in c_subset]
                        sol = solve_linear_system(A, b, p)
                        if sol:
                            test_v = data_np.copy()
                            for idx, ci in enumerate(combo): test_v[ci] = (int(data_np[ci]) + sol[idx]) % p
                            if self._verify_record(record_idx, test_v):
                                for idx, ci in enumerate(combo): self.records[record_idx, ci] = test_v[ci]
                                return True
                    if len(failed) == t: break
                if t > 4: break
        return False

    def _verify_record(self, record_idx: int, data_np: np.ndarray) -> bool:
        record = self.records[record_idx]
        for c in self.constraints:
            target = record_idx % (c.modulus or 251) if c.is_fiber else (c.target if c.target is not None else record[c.stored_field_idx])
            actual = int(np.dot(c.weights, data_np))
            if c.modulus: actual %= c.modulus
            if actual != target: return False
        return True

    def get_data(self) -> List[List[int]]: return self.records[:, :len(self.data_fields)].tolist()
