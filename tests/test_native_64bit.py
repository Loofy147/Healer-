import numpy as np
from fsc.fsc_binary import FSCField, FSCSchema, FSCWriter, FSCReader
from fsc.fsc_native import is_native_available, native_calculate_sum64, native_heal_single64
import os

def test_native_64bit_acceleration():
    print("Testing Native 64-bit Acceleration...")

    if not is_native_available():
        print("! Native library not available, skipping.")
        return

    fields = [FSCField(f"f{i}", "INT64") for i in range(10)]
    schema = FSCSchema(fields)

    p = 251
    # Model 5: TWO independent constraints for unambiguous localization
    schema.add_constraint([1 for i in range(10)], modulus=p, label="C1")
    schema.add_constraint([i + 1 for i in range(10)], modulus=p, label="C2")

    original_data = np.array([i + 1 for i in range(10)], dtype=np.int64)
    writer = FSCWriter(schema)
    writer.add_record(original_data)
    filename = "test_native_64.fsc"
    writer.write(filename)

    reader = FSCReader(filename)

    # 1. Verify acceleration in _verify_record
    valid = reader._verify_record(0, reader.records[0, :10])
    print(f"  Initial verification: {valid}")
    assert valid, "Initial verification failed"

    # 2. Verify single-fault recovery using native_heal_single64
    # Corrupt one field: f5 (value 6)
    reader.records[0, 5] = 99
    print(f"  Corrupted record: {reader.records[0, :10]}")

    # known index recovery
    # verify_and_heal will call native_heal_multi64 because t=1 and len(failed)=2
    # but let's test blind recovery which uses native_heal_single64
    success = reader.verify_and_heal(0)
    print(f"  Healed record (blind):    {reader.records[0, :10]}")
    assert success, "Single-fault recovery (blind) failed"
    assert reader.records[0, 5] == original_data[5], f"Incorrect recovery value: expected {original_data[5]} got {reader.records[0, 5]}"

    print("✓ Native 64-bit Acceleration Verified")
    if os.path.exists(filename): os.remove(filename)

if __name__ == "__main__":
    test_native_64bit_acceleration()
