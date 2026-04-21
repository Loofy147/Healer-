from fsc.fsc_native import FSC_SUCCESS
import sys
import os
import numpy as np
sys.path.append(os.getcwd())

import fsc.fsc_binary
from fsc.fsc_binary import FSCField, FSCSchema, FSCWriter, FSCReader

def test_native_acceleration():
    print("Testing Native Acceleration Integration...")
    fsc.fsc_binary.FSC_COMMERCIAL_BUILD = True

    fields = [FSCField(f"f{i}", "INT32") for i in range(4)]
    schema = FSCSchema(fields)
    p = 251
    schema.add_constraint([1, 1, 1, 1], modulus=p)
    schema.add_constraint([1, 2, 3, 4], modulus=p)

    writer = FSCWriter(schema)
    writer.add_record([10, 20, 30, 40])
    filename = "test_native.fsc"
    writer.write(filename)

    reader = FSCReader(filename)
    # Corrupt two fields
    reader.records[0, 1] = 99
    reader.records[0, 2] = 88

    print("\nAttempting native multi-fault healing...")
    # This should trigger "NATIVE_RECOVERY_KNOWN" log
    success = reader.verify_and_heal(0, corrupted_indices=[1, 2])

    assert success
    assert np.array_equal(reader.records[0, :4], [10, 20, 30, 40])
    print("✓ Native Acceleration Verified")

    if os.path.exists(filename):
        os.remove(filename)

if __name__ == "__main__":
    test_native_acceleration()
