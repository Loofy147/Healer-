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
        self.weights = weights # weights should be a numpy array for speed
        self.target = target   # fixed target if not fiber
        self.is_fiber = is_fiber
        self.label = label
        self.modulus = modulus
        self.stored_field_idx = -1 # Index in the full record if it's a stored invariant

class FSCSchema:
    """Schema defining fields and their algebraic constraints."""
    def __init__(self, fields: List[FSCField]):
        self.data_fields = fields
        self.constraints: List[FSCConstraint] = []
        self.all_fields = list(fields) # Includes stored invariants

    def add_constraint(self, weights: List[int], target: Optional[int] = None,
                       is_fiber: bool = False, label: str = "", modulus: Optional[int] = None):
        """Add a constraint. If not fiber and target is None, it's a 'Stored Sum' invariant."""
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

    @property
    def record_size(self) -> int:
        return struct.calcsize(self.record_fmt)

class FSCWriter:
    """Writes FSC binary files with embedded invariants."""
    def __init__(self, schema: FSCSchema):
        self.schema = schema
        self.records = np.empty((0, len(self.schema.all_fields)), dtype=np.int64)

    def add_record(self, data: List[int]):
        """Add a record. Invariants are automatically computed."""
        self.add_records(np.array([data], dtype=np.int64))

    def add_records(self, data_matrix: Any):
        """Batch add records from a 2D list or NumPy array."""
        source_np = np.atleast_2d(np.array(data_matrix, dtype=np.int64))
        n_recs = source_np.shape[0]
        n_data = len(self.schema.data_fields)
        n_all = len(self.schema.all_fields)

        full_recs = np.zeros((n_recs, n_all), dtype=np.int64)
        full_recs[:, :n_data] = source_np[:, :n_data]

        for c in self.schema.constraints:
            if not c.is_fiber and c.target is None:
                invariants = source_np[:, :n_data] @ c.weights
                if c.modulus:
                    invariants %= c.modulus
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
                ftype_idx = list(FSCField.TYPES.keys()).index(field.ftype)
                f.write(struct.pack(">B", ftype_idx))

            for c in self.schema.constraints:
                ctype = 1 if c.is_fiber else 0
                target = c.target if c.target is not None else 0
                modulus = c.modulus if c.modulus is not None else 0
                f.write(struct.pack(">B q b q", ctype, target, c.stored_field_idx, modulus))
                f.write(struct.pack(">" + "b"*len(c.weights), *c.weights.tolist()))

            s = struct.Struct(self.schema.record_fmt)
            for record in self.records:
                f.write(s.pack(*record))

class FSCReader:
    """Reads and heals FSC binary files using Model 4 and 5."""
    def __init__(self, filename: str):
        self.filename = filename
        self.data_fields = []
        self.constraints = []
        self.records = np.array([], dtype=np.int64)
        self.ftype_list = list(FSCField.TYPES.keys())
        self._read_file()
        self._validity_mask = None

    def _read_file(self):
        with open(self.filename, "rb") as f:
            magic = f.read(4)
            if magic != b"FSC1": raise ValueError("Invalid magic")
            version, n_data_fields, n_constraints, n_stored_fields, n_records = struct.unpack(">B HB B I", f.read(9))
            for _ in range(n_data_fields):
                name = f.read(16).decode('ascii').strip()
                ftype_idx = struct.unpack(">B", f.read(1))[0]
                self.data_fields.append(FSCField(name, self.ftype_list[ftype_idx]))
            self.all_fields = list(self.data_fields)
            for i in range(n_stored_fields):
                self.all_fields.append(FSCField(f"stored_{i}", "INT64"))
            for _ in range(n_constraints):
                if version >= 3:
                    ctype, target, s_idx, modulus = struct.unpack(">B q b q", f.read(18))
                else:
                    ctype, target, s_idx = struct.unpack(">B q b", f.read(10))
                    modulus = 0
                weights = list(struct.unpack(">" + "b"*n_data_fields, f.read(n_data_fields)))
                c = FSCConstraint(np.array(weights, dtype=np.int64),
                                  target if ctype == 1 or target != 0 or s_idx == -1 else None,
                                  is_fiber=(ctype == 1),
                                  modulus=modulus if modulus != 0 else None)
                c.stored_field_idx = s_idx
                self.constraints.append(c)
            record_fmt = ">" + "".join(f.fmt for f in self.all_fields)
            s = struct.Struct(record_fmt)
            recs = []
            for _ in range(n_records):
                recs.append(s.unpack(f.read(s.size)))
            if recs: self.records = np.array(recs, dtype=np.int64)
            else: self.records = np.empty((0, len(self.all_fields)), dtype=np.int64)

    def verify_all(self) -> np.ndarray:
        n_recs = self.records.shape[0]
        n_data = len(self.data_fields)
        all_ok = np.ones(n_recs, dtype=bool)
        data_np = self.records[:, :n_data]
        for c in self.constraints:
            actual = data_np @ c.weights
            if c.modulus: actual %= c.modulus
            if c.is_fiber: targets = np.arange(n_recs) % (c.modulus if c.modulus else 251)
            elif c.target is not None: targets = np.full(n_recs, c.target, dtype=np.int64)
            else: targets = self.records[:, c.stored_field_idx]
            all_ok &= (actual == targets)
        self._validity_mask = all_ok
        return all_ok

    def verify_and_heal(self, record_idx: int, corrupted_field_idx: int = -1,
                        corrupted_indices: List[int] = None) -> bool:
        record = self.records[record_idx]
        data_np = record[:len(self.data_fields)]
        failed_indices = []
        syndromes = {} # syndrome = (target - actual) % modulus
        for i, c in enumerate(self.constraints):
            if c.is_fiber: target = record_idx % (c.modulus if c.modulus else 251)
            elif c.target is not None: target = c.target
            else: target = record[c.stored_field_idx]
            actual = int(np.dot(c.weights, data_np))
            if c.modulus: actual %= c.modulus
            if actual != target:
                failed_indices.append(i)
                syndromes[i] = (target - actual) % c.modulus if c.modulus else (target - actual)
        if not failed_indices: return True

        # Syndrome-Based Localization and Healing
        p = self.constraints[failed_indices[0]].modulus

        # CASE 1: Erasure Recovery (Positions known)
        erasure_indices = []
        if corrupted_field_idx != -1: erasure_indices.append(corrupted_field_idx)
        if corrupted_indices: erasure_indices.extend(corrupted_indices)
        erasure_indices = sorted(list(set(erasure_indices)))
        if erasure_indices:
            t = len(erasure_indices)
            if len(failed_indices) < t: return False
            if not p: return False
            A = []; b = []
            for i in range(t):
                idx = failed_indices[i]
                c = self.constraints[idx]
                A.append([int(c.weights[ci]) % p for ci in erasure_indices])
                b.append(syndromes[idx] % p)
            sol = solve_linear_system(A, b, p)
            if sol:
                for idx, ci in enumerate(erasure_indices):
                    self.records[record_idx, ci] = (int(data_np[ci]) + sol[idx]) % p
                return True
            return False

        # CASE 2: Single-Fault Syndrome Localization
        # Syndrome s_i = w_{i,j} * error_val
        for field_idx in range(len(self.data_fields)):
            error_candidates = []
            valid = True
            for i in failed_indices:
                c = self.constraints[i]
                w = int(c.weights[field_idx])
                if w == 0:
                    if syndromes[i] != 0: valid = False; break
                    continue
                if p:
                    try: error_candidates.append((syndromes[i] * pow(w, -1, p)) % p)
                    except ValueError: valid = False; break
                else:
                    if syndromes[i] % w != 0: valid = False; break
                    error_candidates.append(syndromes[i] // w)
            if valid and error_candidates and len(set(error_candidates)) == 1:
                error_val = error_candidates[0]
                new_val = (int(data_np[field_idx]) + error_val) % p if p else (int(data_np[field_idx]) + error_val)
                test_v = data_np.copy(); test_v[field_idx] = new_val
                if self._verify_record(record_idx, test_v):
                    self.records[record_idx, field_idx] = new_val
                    return True

        # CASE 3: Multi-Fault Syndrome Localization (k=2)
        if len(failed_indices) >= 2 and p:
            for combo in combinations(range(len(self.data_fields)), 2):
                A = []
                b = []
                # Use first two failed constraints
                for i in range(2):
                    idx = failed_indices[i]
                    c = self.constraints[idx]
                    A.append([int(c.weights[ci]) % p for ci in combo])
                    b.append(syndromes[idx] % p)
                sol = solve_linear_system(A, b, p)
                if sol:
                    test_v = data_np.copy()
                    for idx, ci in enumerate(combo):
                        test_v[ci] = (int(data_np[ci]) + sol[idx]) % p
                    if self._verify_record(record_idx, test_v):
                        for idx, ci in enumerate(combo):
                            self.records[record_idx, ci] = test_v[ci]
                        return True

        # General case for higher k (brute-force on t errors with t constraints)
        num_failed = len(failed_indices)
        for t in range(3, (num_failed // 2) + 1):
            for combo in combinations(range(len(self.data_fields)), t):
                if not p: continue
                A = []; b = []
                for i in range(t):
                    idx = failed_indices[i]
                    c = self.constraints[idx]
                    A.append([int(c.weights[ci]) % p for ci in combo])
                    b.append(syndromes[idx] % p)
                sol = solve_linear_system(A, b, p)
                if sol:
                    test_v = data_np.copy()
                    for idx, ci in enumerate(combo):
                        test_v[ci] = (int(data_np[ci]) + sol[idx]) % p
                    if self._verify_record(record_idx, test_v):
                        for idx, ci in enumerate(combo):
                            self.records[record_idx, ci] = test_v[ci]
                        return True
        return False

    def _verify_record(self, record_idx: int, data_np: np.ndarray) -> bool:
        record = self.records[record_idx]
        for c in self.constraints:
            if c.is_fiber: target = record_idx % (c.modulus if c.modulus else 251)
            elif c.target is not None: target = c.target
            else: target = record[c.stored_field_idx]
            actual = int(np.dot(c.weights, data_np))
            if c.modulus: actual %= c.modulus
            if actual != target: return False
        return True

    def get_data(self) -> List[List[int]]:
        return self.records[:, :len(self.data_fields)].tolist()
