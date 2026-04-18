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
        """
        Write a page of records with a vertical parity record at the end.
        If the schema has a modulus, column sums are computed mod m.
        """
        n_data = len(self.schema.data_fields)
        # Use first constraint's modulus for column parity if available
        mod = self.schema.constraints[0].modulus if self.schema.constraints else None

        data_np = np.array(data_block, dtype=np.int64)
        col_sums = np.sum(data_np, axis=0)
        if mod:
            col_sums %= mod

        writer = FSCWriter(self.schema)
        for rec in data_block:
            writer.add_record(rec)
        writer.add_record(col_sums.tolist())
        writer.write(filename)

class FSCPageReader:
    def __init__(self, filename: str):
        self.reader = FSCReader(filename)
        self.n_data = len(self.reader.data_fields)
        # data_records and parity_record are views into self.reader.records
        self.data_records = self.reader.records[:-1, :self.n_data]
        self.parity_record = self.reader.records[-1, :self.n_data]
        self.mod = self.reader.constraints[0].modulus if self.reader.constraints else None

    def verify_and_heal_2d(self) -> bool:
        """
        Iterative 2D healing engine. Alternates between row-wise Model 5
        and column-wise sum invariants to resolve multi-erasure blocks.
        """
        changed = True
        max_iters = 10
        iters = 0

        while changed and iters < max_iters:
            changed = False
            iters += 1

            # Phase A: Row Healing (Automatic Model 5)
            for i in range(len(self.data_records)):
                old_row = self.data_records[i].copy()
                if self.reader.verify_and_heal(i):
                    if not np.array_equal(self.data_records[i], old_row):
                        changed = True

            # Phase B: Column Healing
            current_sums = np.sum(self.data_records, axis=0)
            if self.mod:
                current_sums %= self.mod
                diffs = (self.parity_record - current_sums) % self.mod
            else:
                diffs = self.parity_record - current_sums

            for col_idx in np.where(diffs != 0)[0]:
                diff = diffs[col_idx]
                dirty_rows = []
                for row_idx in range(len(self.data_records)):
                    # A row is 'dirty' if it fails row-wise verification
                    if not self.reader._verify_record(row_idx, self.data_records[row_idx]):
                        dirty_rows.append(row_idx)

                if len(dirty_rows) == 1:
                    # Exactly one erasure in this column!
                    row_idx = dirty_rows[0]
                    if self.mod:
                        self.data_records[row_idx, col_idx] = (self.data_records[row_idx, col_idx] + diff) % self.mod
                    else:
                        self.data_records[row_idx, col_idx] += diff
                    changed = True

        # Final Verification
        for i in range(len(self.data_records)):
            if not self.reader._verify_record(i, self.data_records[i]):
                return False
        return True

    def get_data(self) -> List[List[int]]:
        return self.data_records.tolist()
