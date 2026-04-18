import struct
import os
import numpy as np
from typing import List, Optional, Dict
from fsc_binary import FSCField, FSCSchema, FSCWriter, FSCReader

class FSCPageWriter:
    def __init__(self, schema: FSCSchema, page_size: int = 10):
        self.schema = schema
        self.page_size = page_size

    def write_page(self, data_block: List[List[int]], filename: str):
        n_data = len(self.schema.data_fields)
        # Use numpy for column sums
        data_np = np.array(data_block, dtype=np.int64)
        col_sums = np.sum(data_np, axis=0).tolist()

        writer = FSCWriter(self.schema)
        for rec in data_block:
            writer.add_record(rec)
        writer.add_record(col_sums)
        writer.write(filename)

class FSCPageReader:
    def __init__(self, filename: str):
        self.reader = FSCReader(filename)
        self.n_data = len(self.reader.data_fields)
        # self.reader.records is already a NumPy array
        self.data_records = self.reader.records[:-1, :self.n_data]
        self.parity_record = self.reader.records[-1, :self.n_data]

    def verify_and_heal_2d(self) -> bool:
        changed = True
        while changed:
            changed = False

            # Phase A: Row Healing
            for i in range(len(self.data_records)):
                # self.reader.records shares data with self.data_records
                old_row = self.data_records[i].copy()
                if self.reader.verify_and_heal(i):
                    new_row = self.data_records[i]
                    if not np.array_equal(new_row, old_row):
                        changed = True

            # Phase B: Column Healing
            # Vectorized column sum check
            current_sums = np.sum(self.data_records, axis=0)
            diffs = self.parity_record - current_sums

            for col_idx in np.where(diffs != 0)[0]:
                diff = diffs[col_idx]
                dirty_rows = []
                for row_idx in range(len(self.data_records)):
                    # A row is dirty if it's not internally consistent
                    if not self.reader.verify_and_heal(row_idx):
                        dirty_rows.append(row_idx)

                if len(dirty_rows) == 1:
                    row_idx = dirty_rows[0]
                    self.data_records[row_idx, col_idx] += diff
                    changed = True

        # Final Verification
        for i in range(len(self.data_records)):
            if not self.reader.verify_and_heal(i):
                return False
        return True

    def get_data(self) -> List[List[int]]:
        return self.data_records.tolist()
