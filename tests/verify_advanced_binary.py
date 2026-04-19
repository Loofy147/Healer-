"""
FSC: Forward Sector Correction
Copyright (C) 2024 FSC Core Team. All Rights Reserved.

PUBLIC LICENSE: GNU Affero General Public License (AGPLv3)
COMMERCIAL LICENSE: Required for proprietary/enterprise use.

PATENT PENDING: Industrial applications of these algebraic primitives
for database pages, kernel block devices, and network protocols.
"""

import numpy as np
from fsc.fsc_binary import FSCField, FSCSchema, FSCWriter, FSCReader
import os

def test_model5_auto_localization():
    print("Testing Model 5 (Algebraic Overdetermination) Auto-Localization...")
    fields = [
        FSCField("f0", "INT32"),
        FSCField("f1", "INT32"),
        FSCField("f2", "INT32")
    ]
    schema = FSCSchema(fields)
    # Three independent constraints with modulus 251
    schema.add_constraint([1, 1, 0], modulus=251, label="f0+f1")
    schema.add_constraint([0, 1, 1], modulus=251, label="f1+f2")
    schema.add_constraint([1, 0, 1], modulus=251, label="f0+f2")

    writer = FSCWriter(schema)
    original_data = [100, 20, 50]
    writer.add_record(original_data)
    writer.write("test_m5.fsc")

    # Read and corrupt
    reader = FSCReader("test_m5.fsc")
    # Corrupt f1 (index 1)
    reader.records[0, 1] = 999

    print(f"  Corrupted record: {reader.records[0, :3]}")
    success = reader.verify_and_heal(0)
    print(f"  Healed record:    {reader.records[0, :3]}")

    if success and np.array_equal(reader.records[0, :3], original_data):
        print("✓ Model 5 Auto-Localization Verified")
    else:
        print("✗ Model 5 Auto-Localization Failed")
        exit(1)

def test_model4_fiber_binary():
    print("\nTesting Model 4 (Fiber) Zero-Overhead Binary...")
    # In this test, we use a fiber constraint with modulus 251.
    fields = [
        FSCField("v0", "INT32"),
        FSCField("v1", "INT32")
    ]
    schema = FSCSchema(fields)
    # Positional constraint: v0 + v1 = pos % 251
    schema.add_constraint([1, 1], is_fiber=True, modulus=251, label="fiber_sum")

    writer = FSCWriter(schema)
    # Record 0: pos 0 -> sum 0. [10, -10]
    # Record 1: pos 1 -> sum 1. [20, -19]
    writer.add_record([10, -10])
    writer.add_record([20, -19])
    writer.write("test_m4.fsc")

    reader = FSCReader("test_m4.fsc")

    # Corrupt record 1, field 0
    reader.records[1, 0] = 0
    print(f"  Corrupted record 1: {reader.records[1, :2]}")
    success = reader.verify_and_heal(1)
    print(f"  Healed record 1:    {reader.records[1, :2]}")

    if success and reader.records[1, 0] == 20:
        print("✓ Model 4 Fiber Binary Verified")
    else:
        print("✗ Model 4 Fiber Binary Failed")
        exit(1)

if __name__ == "__main__":
    test_model5_auto_localization()
    test_model4_fiber_binary()
