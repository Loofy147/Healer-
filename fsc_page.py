import struct
import os
from typing import List, Optional, Dict
from fsc_binary import FSCField, FSCSchema, FSCWriter, FSCReader

class FSCPageWriter:
    def __init__(self, schema: FSCSchema, page_size: int = 10):
        self.schema = schema
        self.page_size = page_size

    def write_page(self, data_block: List[List[int]], filename: str):
        n_data = len(self.schema.data_fields)
        col_sums = [0] * n_data
        for rec in data_block:
            for i in range(n_data):
                col_sums[i] += rec[i]

        writer = FSCWriter(self.schema)
        for rec in data_block:
            writer.add_record(rec)
        writer.add_record(col_sums)
        writer.write(filename)

class FSCPageReader:
    def __init__(self, filename: str):
        self.reader = FSCReader(filename)
        self.n_data = len(self.reader.data_fields)
        # records[:-1] are data records, record[-1] is the vertical parity
        self.data_records = [list(r[:self.n_data]) for r in self.reader.records[:-1]]
        self.parity_record = list(self.reader.records[-1][:self.n_data])

    def verify_and_heal_2d(self) -> bool:
        changed = True
        while changed:
            changed = False

            # Phase A: Row Healing
            for i in range(len(self.data_records)):
                self.reader.records[i][:self.n_data] = self.data_records[i]
                old_row = list(self.data_records[i])
                if self.reader.verify_and_heal(i):
                    new_row = self.reader.records[i][:self.n_data]
                    if new_row != old_row:
                        self.data_records[i] = list(new_row)
                        changed = True

            # Phase B: Column Healing
            for col_idx in range(self.n_data):
                current_sum = sum(rec[col_idx] for rec in self.data_records)
                target = self.parity_record[col_idx]

                if current_sum != target:
                    dirty_rows = []
                    for row_idx in range(len(self.data_records)):
                        self.reader.records[row_idx][:self.n_data] = self.data_records[row_idx]
                        # A row is dirty if it's not internally consistent
                        if not self.reader.verify_and_heal(row_idx):
                            dirty_rows.append(row_idx)

                    if len(dirty_rows) == 1:
                        row_idx = dirty_rows[0]
                        diff = target - current_sum
                        self.data_records[row_idx][col_idx] += diff
                        changed = True

        # Final Verification
        for i in range(len(self.data_records)):
            self.reader.records[i][:self.n_data] = self.data_records[i]
            if not self.reader.verify_and_heal(i):
                return False
        return True

    def get_data(self) -> List[List[int]]:
        return self.data_records
