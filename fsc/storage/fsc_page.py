"""
FSC: Forward Sector Correction
Copyright (C) 2024 FSC Core Team. All Rights Reserved.

PUBLIC LICENSE: GNU Affero General Public License (AGPLv3)
COMMERCIAL LICENSE: Required for proprietary/enterprise use.

PATENT PENDING: Industrial applications of these algebraic primitives
for database pages, kernel block devices, and network protocols.
"""

import struct
import os
import numpy as np
from typing import List, Optional, Dict
from fsc.storage.fsc_binary import FSCField, FSCSchema, FSCWriter, FSCReader
from fsc.core.fsc_native import FSC_SUCCESS, FSC_ERR_SINGULAR, FSC_ERR_BOUNDS, FSC_ERR_INVALID

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

    def verify_and_heal_2d(self) -> int:
        """
        Iterative 2D healing engine. Alternates between row-wise Model 5
        and column-wise sum invariants to resolve multi-erasure blocks.
        """
        changed = True
        max_iters = 10
        iters = 0

        # Performance: Cache row status to avoid redundant O(N*M) verifications
        all_status = self.reader.verify_all_records()
        row_status = all_status[:-1].tolist()

        while changed and iters < max_iters:
            changed = False
            iters += 1

            # Phase A: Row Healing (Automatic Model 5)
            for i in range(len(self.data_records)):
                if not row_status[i]:
                    old_row = self.data_records[i].copy()
                    if self.reader.verify_and_heal(i) == FSC_SUCCESS:
                        if not np.array_equal(self.data_records[i], old_row):
                            changed = True
                            row_status[i] = True

            # Phase B: Column Healing
            current_sums = np.sum(self.data_records, axis=0)
            if self.mod:
                current_sums %= self.mod
                diffs = (self.parity_record - current_sums) % self.mod
            else:
                diffs = self.parity_record - current_sums

            dirty_col_indices = np.where(diffs != 0)[0]
            if len(dirty_col_indices) > 0:
                dirty_row_indices = [i for i, ok in enumerate(row_status) if not ok]

                for col_idx in dirty_col_indices:
                    diff = diffs[col_idx]
                    # Exactly one erasure in this column!
                    if len(dirty_row_indices) == 1:
                        row_idx = dirty_row_indices[0]
                        if self.mod:
                            self.data_records[row_idx, col_idx] = (self.data_records[row_idx, col_idx] + diff) % self.mod
                        else:
                            self.data_records[row_idx, col_idx] += diff

                        # Re-verify only the modified row
                        row_status[row_idx] = self.reader._verify_record(row_idx, self.data_records[row_idx])
                        if row_status[row_idx]:
                            # Update dirty list for subsequent columns in this iteration
                            dirty_row_indices = [i for i, ok in enumerate(row_status) if not ok]
                        changed = True

        return FSC_SUCCESS if all(row_status) else FSC_ERR_INVALID

    def get_data(self) -> List[List[int]]:
        return self.data_records.tolist()
