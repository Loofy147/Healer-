import sys
import os
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fsc.fsc_binary import FSCField, FSCSchema, FSCWriter, FSCReader

def debug():
    n_data = 10
    schema = FSCSchema([FSCField(f"f{i}", "INT64") for i in range(n_data)])
    for i in range(4):
        weights = [0] * n_data
        # C0: f0+f1+f2
        # C1: f1+f2+f3
        # C2: f2+f3+f4
        # C3: f3+f4+f5
        weights[i] = 1; weights[(i+1)%n_data] = 1; weights[(i+2)%n_data] = 1
        schema.add_constraint(weights, modulus=251)

    writer = FSCWriter(schema)
    data = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    writer.add_record(data)
    writer.write("debug.fsc")

    reader = FSCReader("debug.fsc")
    # Corrupt f3 and f5
    # Original: f3=40, f5=60
    # New: f3=50, f5=80
    reader.records[0, 3] = 50
    reader.records[0, 5] = 80

    # Trace verify_and_heal manually
    record = reader.records[0]
    data_np = record[:n_data]
    failed = []; syndromes = {}
    for i, c in enumerate(reader.constraints):
        target = record[c.stored_field_idx] if c.stored_field_idx != -1 else (c.target if c.target is not None else 0)
        actual = int(np.dot(c.weights, data_np)) % 251
        if actual != target:
            failed.append(i)
            syndromes[i] = (target - actual) % 251
            print(f"Constraint {i} failed. Target: {target}, Actual: {actual}, Syndrome: {syndromes[i]}")

if __name__ == "__main__":
    debug()
