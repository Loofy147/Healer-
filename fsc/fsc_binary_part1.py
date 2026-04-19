"""
FSC: Forward Sector Correction
Copyright (C) 2024 FSC Core Team. All Rights Reserved.

PUBLIC LICENSE: GNU Affero General Public License (AGPLv3)
COMMERCIAL LICENSE: Required for proprietary/enterprise use.

PATENT PENDING: Industrial applications of these algebraic primitives
for database pages, kernel block devices, and network protocols.
"""

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
    def __init__(self, weights: List[int], target: Optional[int] = None,
                 is_fiber: bool = False, label: str = ""):
        self.weights = weights # length must match number of DATA fields
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

        c = FSCConstraint(weights, target, is_fiber, label)
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

        for c in self.schema.constraints:
            if not c.is_fiber and c.target is None:
                # Compute and store invariant
                val = sum(w * v for w, v in zip(c.weights, data))
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
                f.write(struct.pack(">" + "b"*len(c.weights), *c.weights))

            # 3. Write Records
            record_fmt = self.schema.record_fmt
            for record in self.records:
                f.write(struct.pack(record_fmt, *record))

class FSCReader:
    """Reads and heals FSC binary files using Model 4 and 5."""
    def __init__(self, filename: str):
        self.filename = filename
        self.data_fields = []
