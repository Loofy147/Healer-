import numpy as np
from fsc_binary import FSCField, FSCSchema, FSCWriter, FSCReader
import os

def test_multifault_binary_healing():
    print("Testing Multi-Fault Binary Healing (k=2)...")
    fields = [FSCField(f"f{i}", "INT32") for i in range(4)]
    schema = FSCSchema(fields)

    p = 251
    # Two independent modular constraints (Reed-Solomon style)
    # C1: sum(v_i) % p
    schema.add_constraint([1, 1, 1, 1], modulus=p, label="C1")
    # C2: sum((i+1)*v_i) % p
    schema.add_constraint([1, 2, 3, 4], modulus=p, label="C2")

    writer = FSCWriter(schema)
    original_data = [10, 20, 30, 40]
    writer.add_record(original_data)
    writer.write("test_multifault.fsc")

    reader = FSCReader("test_multifault.fsc")

    # Corrupt TWO fields: f1 (20) and f2 (30)
    reader.records[0, 1] = 99
    reader.records[0, 2] = 88

    print(f"  Corrupted record: {reader.records[0, :4]}")

    # Explicitly tell it which fields are bad (Erasure Recovery)
    success = reader.verify_and_heal(0, corrupted_indices=[1, 2])

    print(f"  Healed record:    {reader.records[0, :4]}")

    if success and np.array_equal(reader.records[0, :4], original_data):
        print("✓ Multi-Fault Binary Healing Verified")
    else:
        print("✗ Multi-Fault Binary Healing Failed")
        exit(1)

if __name__ == "__main__":
    test_multifault_binary_healing()
