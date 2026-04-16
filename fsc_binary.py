import numpy as np
import struct
import io
from typing import List, Dict, Any, Tuple

class FSCField:
    # Field types as defined in Section 5.2
    TYPES = {
        'UINT8': 'B',
        'UINT16': 'H',
        'UINT32': 'I',
        'UINT64': 'Q',
        'INT16': 'h',
        'INT32': 'i',
        'INT64': 'q'
    }

    def __init__(self, name: str, ftype: str, recoverable: bool = True, weight: int = 1):
        self.name = name.ljust(16)[:16]
        self.ftype = ftype
        self.fmt = self.TYPES[ftype]
        self.recoverable = 1 if recoverable else 0
        self.weight = weight

class FSCSchema:
    def __init__(self, fields: List[FSCField]):
        self.fields = fields
        # All records end with fiber_sum (INT64)
        self.fields.append(FSCField("fiber_sum", "INT64", recoverable=False))
        self.record_fmt = ">" + "".join(f.fmt for f in self.fields)
        self.record_size = struct.calcsize(self.record_fmt)

class FSCWriter:
    def __init__(self, schema: FSCSchema):
        self.schema = schema
        self.records = []

    def add_records(self, data_matrix: Any):
        """Batch add records from a 2D list or NumPy array."""
        arr = np.asarray(data_matrix, dtype=np.int64)
        fiber_sums = np.sum(arr, axis=1, keepdims=True)
        full_records = np.hstack([arr, fiber_sums]).tolist()
        self.records.extend(full_records)

    def add_record(self, data: List[int]):
        # data should not include fiber_sum
        fiber_sum = sum(data)
        record = list(data) + [fiber_sum]
        self.records.append(record)

    def write(self, filename: str):
        with open(filename, "wb") as f:
            # Header: FSC1 (4), version (1), n_fields (2), n_records (4)
            f.write(b"FSC1")
            f.write(struct.pack(">BHI", 1, len(self.schema.fields), len(self.records)))

            # Schema definition
            for field in self.schema.fields:
                f.write(field.name.encode('ascii'))
                # ftype: u8, recoverable: u8, weight: i8
                # We need a mapping for ftype to u8
                ftype_idx = list(FSCField.TYPES.keys()).index(field.ftype)
                f.write(struct.pack(">BBB", ftype_idx, field.recoverable, field.weight))

            # Records
            for record in self.records:
                f.write(struct.pack(self.schema.record_fmt, *record))

class FSCReader:
    def __init__(self, filename: str):
        self.filename = filename
        self.fields = []
        self.records = []
        self.ftype_list = list(FSCField.TYPES.keys())
        self._read_header()

    def _read_header(self):
        with open(self.filename, "rb") as f:
            magic = f.read(4)
            if magic != b"FSC1":
                raise ValueError("Invalid magic number")

            version, n_fields, n_records = struct.unpack(">BHI", f.read(7))

            for _ in range(n_fields):
                name = f.read(16).decode('ascii').strip()
                ftype_idx, recoverable, weight = struct.unpack(">BBB", f.read(3))
                # Treat weight as signed i8 if needed, but here simple u8 read
                self.fields.append({
                    'name': name,
                    'ftype': self.ftype_list[ftype_idx],
                    'fmt': FSCField.TYPES[self.ftype_list[ftype_idx]],
                    'recoverable': bool(recoverable),
                    'weight': weight
                })

            self.record_fmt = ">" + "".join(f['fmt'] for f in self.fields)
            self.record_size = struct.calcsize(self.record_fmt)

            for _ in range(n_records):
                record_data = f.read(self.record_size)
                self.records.append(list(struct.unpack(self.record_fmt, record_data)))

    def verify_all(self) -> np.ndarray:
        """Vectorized verification of all records. Returns boolean mask of validity."""
        arr = np.array(self.records, dtype=np.int64)
        fiber_sums = arr[:, -1]
        actual_sums = np.sum(arr[:, :-1], axis=1)
        return actual_sums == fiber_sums

    def verify_and_heal(self, record_idx: int, corrupted_field_idx: int = -1) -> bool:
        """
        Verify record integrity. If corrupted_field_idx is provided,
        attempts to heal that specific field.
        """
        record = self.records[record_idx]
        fiber_sum = record[-1]
        actual_sum = sum(record[:-1])

        if actual_sum == fiber_sum:
            return True

        if corrupted_field_idx != -1 and corrupted_field_idx < len(record) - 1:
            # Recovery: fiber_sum - sum of others
            others_sum = sum(record[i] for i in range(len(record)-1) if i != corrupted_field_idx)
            recovered_val = fiber_sum - others_sum
            self.records[record_idx][corrupted_field_idx] = recovered_val
            return True

        return False

    def get_records(self):
        return [r[:-1] for r in self.records]
