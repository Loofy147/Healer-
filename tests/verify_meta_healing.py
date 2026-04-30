import sys
import os
import struct
import numpy as np
sys.path.append(os.getcwd())

from fsc.storage.fsc_binary import FSCField, FSCSchema, FSCWriter, FSCReader
import fsc.storage.fsc_binary

def test_meta_healing():
    print("=========================================================")
    print("  FSC v5 RECURSIVE METADATA HEALING VERIFICATION")
    print("=========================================================\n")

    # Enable audit logs to see healing in action
    fsc.storage.fsc_binary.FSC_COMMERCIAL_BUILD = True

    fields = [FSCField("val", "UINT8")]
    schema = FSCSchema(fields)
    # Define a constraint with modulus 251
    schema.add_constraint([1], target=100, modulus=251)

    writer = FSCWriter(schema)
    writer.add_record([100])
    filename = "meta_test.fsc"
    writer.write(filename)

    print("[STEP 1] Corrupting Metadata (Modulus: 251 -> 250)...")
    # Modulus is at offset 49 (4 magic + 18 header + 17 field + 1 ctype + 8 target + 1 si = 49)
    with open(filename, "r+b") as f:
        f.seek(49)
        f.write(struct.pack(">q", 250))

    print("\n[STEP 2] Attempting to read with v5 engine...")
    # The v5 engine should detect the mismatch using the meta-footer,
    # calculate the syndrome, and heal the modulus back to 251.
    reader = FSCReader(filename)

    print(f"\n[STEP 3] Verifying Modulus Recovery...")
    recovered_mod = reader.constraints[0].modulus
    print(f"Recovered Modulus: {recovered_mod}")

    assert recovered_mod == 251
    print("✓ Metadata healed successfully.")

    print("\n[STEP 4] Verifying Data Integrity...")
    # Corrupt data byte (offset 58) to test if data-healing still works with the recovered meta
    with open(filename, "r+b") as f:
        f.seek(58)
        f.write(struct.pack(">B", 0)) # Corrupt 100 -> 0

    reader2 = FSCReader(filename) # Should heal meta again
    res = reader2.verify_and_heal(0)
    print(f"Data Recovery Result: {res}")
    print(f"Recovered Value: {reader2.records[0, 0]}")

    assert res == 1
    assert reader2.records[0, 0] == 100
    print("✓ Data healed successfully using recovered metadata.")

    if os.path.exists(filename):
        os.remove(filename)

    print("\n=========================================================")
    print("  VERIFICATION COMPLETE: INDUSTRY GAP CLOSED")
    print("=========================================================")

if __name__ == "__main__":
    test_meta_healing()
