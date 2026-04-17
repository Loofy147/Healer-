import numpy as np
import struct
import io
from typing import List, Dict, Any, Tuple, Optional

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
                 is_fiber: bool = False, label: str = ""):
        self.weights = weights # weights should be a numpy array for speed
        self.target = target   # fixed target if not fiber
        self.is_fiber = is_fiber
        self.label = label
        self.stored_field_idx = -1 # Index in the full record if it's a stored invariant

class FSCSchema:
    """Schema defining fields and their algebraic constraints."""
    def __init__(self, fields: List[FSCField]):
        self.data_fields = fields
        self.constraints: List[FSCConstraint] = []
        self.all_fields = list(fields) # Includes stored invariants

    def add_constraint(self, weights: List[int], target: Optional[int] = None,
                       is_fiber: bool = False, label: str = ""):
        """Add a constraint. If not fiber and target is None, it's a 'Stored Sum' invariant."""
        if len(weights) != len(self.data_fields):
            raise ValueError(f"Constraint weights ({len(weights)}) must match data fields ({len(self.data_fields)})")

        c = FSCConstraint(np.array(weights, dtype=np.int64), target, is_fiber, label)
        if not is_fiber and target is None:
            # Add a stored invariant field
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
        self.records = []

    def add_record(self, data: List[int]):
        """Add a record. Invariants are automatically computed."""
        if len(data) != len(self.schema.data_fields):
            raise ValueError("Data length must match data_fields")

        full_record = list(data)
        # Ensure we have slots for stored invariants
        n_extra = len(self.schema.all_fields) - len(self.schema.data_fields)
        full_record.extend([0] * n_extra)

        data_np = np.array(data, dtype=np.int64)
        for c in self.schema.constraints:
            if not c.is_fiber and c.target is None:
                # Compute and store invariant
                val = int(np.dot(c.weights, data_np))
                full_record[c.stored_field_idx] = val

        self.records.append(full_record)

    def write(self, filename: str):
        with open(filename, "wb") as f:
            # Header: FSC1 (4), version (1), n_data_fields (2), n_constraints (1), n_stored (1), n_records (4)
            f.write(b"FSC1")
            f.write(struct.pack(">B HB B I", 2, len(self.schema.data_fields),
                                len(self.schema.constraints),
                                len(self.schema.all_fields) - len(self.schema.data_fields),
                                len(self.records)))

            # 1. Write Data Fields
            for field in self.schema.data_fields:
                f.write(field.name.encode('ascii'))
                ftype_idx = list(FSCField.TYPES.keys()).index(field.ftype)
                f.write(struct.pack(">B", ftype_idx))

            # 2. Write Constraints
            for c in self.schema.constraints:
                # type: fiber(1) or stored(0), target: i64, weights: n_data_fields * i8
                ctype = 1 if c.is_fiber else 0
                target = c.target if c.target is not None else 0
                f.write(struct.pack(">B q b", ctype, target, c.stored_field_idx))
                f.write(struct.pack(">" + "b"*len(c.weights), *c.weights.tolist()))

            # 3. Write Records
            record_fmt = self.schema.record_fmt
            for record in self.records:
                f.write(struct.pack(record_fmt, *record))

class FSCReader:
    """Reads and heals FSC binary files using Model 4 and 5."""
    def __init__(self, filename: str):
        self.filename = filename
        self.data_fields = []
        self.constraints = []
        self.records = np.array([], dtype=np.int64)
        self.ftype_list = list(FSCField.TYPES.keys())
        self._read_file()

    def _read_file(self):
        with open(self.filename, "rb") as f:
            magic = f.read(4)
            if magic != b"FSC1": raise ValueError("Invalid magic")

            # version(1), n_data(2), n_cons(1), n_stored(1), n_recs(4)
            version, n_data_fields, n_constraints, n_stored_fields, n_records = struct.unpack(">B HB B I", f.read(9))

            # Read Data Fields
            for _ in range(n_data_fields):
                name = f.read(16).decode('ascii').strip()
                ftype_idx = struct.unpack(">B", f.read(1))[0]
                self.data_fields.append(FSCField(name, self.ftype_list[ftype_idx]))

            self.all_fields = list(self.data_fields)
            for i in range(n_stored_fields):
                self.all_fields.append(FSCField(f"stored_{i}", "INT64"))

            # Read Constraints
            for _ in range(n_constraints):
                ctype, target, s_idx = struct.unpack(">B q b", f.read(10))
                weights = list(struct.unpack(">" + "b"*n_data_fields, f.read(n_data_fields)))
                c = FSCConstraint(np.array(weights, dtype=np.int64), target if ctype == 1 or target != 0 or s_idx == -1 else None,
                                  is_fiber=(ctype == 1))
                c.stored_field_idx = s_idx
                self.constraints.append(c)

            # Read Records into NumPy array
            record_fmt = ">" + "".join(f.fmt for f in self.all_fields)
            record_size = struct.calcsize(record_fmt)

            recs = []
            for _ in range(n_records):
                data = struct.unpack(record_fmt, f.read(record_size))
                recs.append(data)

            if recs:
                self.records = np.array(recs, dtype=np.int64)
            else:
                self.records = np.empty((0, len(self.all_fields)), dtype=np.int64)

    def verify_and_heal(self, record_idx: int, corrupted_field_idx: int = -1) -> bool:
        """
        Automatically localize and heal corruption using multiple constraints (Model 5).
        If corrupted_field_idx is provided, uses it directly (Model 3/4 style).
        """
        record = self.records[record_idx]
        data_np = record[:len(self.data_fields)]

        failed_constraints = []
        actual_sums = {}
        for i, c in enumerate(self.constraints):
            if c.is_fiber: target = record_idx % 251
            elif c.target is not None: target = c.target
            else: target = record[c.stored_field_idx]

            actual = int(np.dot(c.weights, data_np))
            if actual != target:
                failed_constraints.append((i, target))
                actual_sums[i] = actual

        if not failed_constraints: return True

        # Manual localization if index provided
        if corrupted_field_idx != -1:
            for i, target in failed_constraints:
                c = self.constraints[i]
                if c.weights[corrupted_field_idx] != 0:
                    actual = actual_sums.get(i, int(np.dot(c.weights, data_np)))
                    others = actual - (c.weights[corrupted_field_idx] * data_np[corrupted_field_idx])
                    recovered_val = (target - others) // c.weights[corrupted_field_idx]
                    self.records[record_idx, corrupted_field_idx] = int(recovered_val)
                    return True
            return False

        # Model 5 localization (Automatic)
        valid_repairs = []
        for field_idx in range(len(self.data_fields)):
            candidates = []
            possible = True
            for i, target in failed_constraints:
                c = self.constraints[i]
                w = c.weights[field_idx]
                if w == 0:
                    possible = False
                    break

                actual = actual_sums[i]
                others = actual - (w * data_np[field_idx])

                # Division check
                if (target - others) % w != 0:
                    possible = False
                    break
                candidates.append((target - others) // w)

            if possible and candidates and len(set(candidates)) == 1:
                recovered_val = int(candidates[0])
                temp_data_np = data_np.copy()
                temp_data_np[field_idx] = recovered_val

                # Verify ALL constraints
                all_ok = True
                for i, c in enumerate(self.constraints):
                    if c.is_fiber: t = record_idx % 251
                    elif c.target is not None: t = c.target
                    else: t = record[c.stored_field_idx]

                    if int(np.dot(c.weights, temp_data_np)) != t:
                        all_ok = False
                        break

                if all_ok:
                    valid_repairs.append((field_idx, recovered_val))

        if len(valid_repairs) >= 1:
            # If multiple repairs possible, we take the first one but it implies underdetermination
            f_idx, r_val = valid_repairs[0]
            self.records[record_idx, f_idx] = r_val
            return True

        return False

    def get_data(self) -> List[List[int]]:
        return self.records[:, :len(self.data_fields)].tolist()
