"""
FSC: Forward Sector Correction
Copyright (C) 2024 FSC Core Team. All Rights Reserved.

PUBLIC LICENSE: GNU Affero General Public License (AGPLv3)
COMMERCIAL LICENSE: Required for proprietary/enterprise use.

PATENT PENDING: Industrial applications of these algebraic primitives
for database pages, kernel block devices, and network protocols.
"""

import sys
import os
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fsc.fsc_binary import FSCField, FSCSchema, FSCWriter, FSCReader

def test_syndrome_k2():
    print("━━ TESTING GENERALIZED SYNDROME DECODING (k=2) ━━")
    n_data = 10
    schema = FSCSchema([FSCField(f"f{i}", "INT64") for i in range(n_data)])
    for i in range(4):
        weights = [0] * n_data
        weights[i] = 1; weights[(i+1)%n_data] = 1; weights[(i+2)%n_data] = 1
        schema.add_constraint(weights, modulus=251)
    filename = "k2.fsc"
    writer = FSCWriter(schema)
    data = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    writer.add_record(data)
    writer.write(filename)
    reader = FSCReader(filename)
    reader.records[0, 3] = 50; reader.records[0, 5] = 80
    success = reader.verify_and_heal(0)
    healed = reader.records[0, :n_data].tolist()
    if success and healed == data:
        print("  ✓ k=2 VERIFIED")
    else:
        print("  ✗ k=2 FAILED")
    if os.path.exists(filename): os.remove(filename)

def test_syndrome_k3():
    print("\n━━ TESTING GENERALIZED SYNDROME DECODING (k=3) ━━")
    n_data = 10
    schema = FSCSchema([FSCField(f"f{i}", "INT64") for i in range(n_data)])
    for i in range(6):
        weights = [0] * n_data
        weights[i] = 1; weights[(i+1)%n_data] = 1; weights[(i+2)%n_data] = 1
        schema.add_constraint(weights, modulus=251)
    filename = "k3.fsc"
    writer = FSCWriter(schema)
    data = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    writer.add_record(data)
    writer.write(filename)
    reader = FSCReader(filename)
    reader.records[0, 1] = 99; reader.records[0, 4] = 99; reader.records[0, 7] = 99
    success = reader.verify_and_heal(0)
    healed = reader.records[0, :n_data].tolist()
    if success and healed == data:
        print("  ✓ k=3 VERIFIED")
    else:
        print("  ✗ k=3 FAILED")
    if os.path.exists(filename): os.remove(filename)

if __name__ == "__main__":
    test_syndrome_k2()
    test_syndrome_k3()
