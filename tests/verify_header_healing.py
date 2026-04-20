import sys
import os
sys.path.append(os.getcwd())

from fsc.fsc_binary import FSCField, FSCSchema, FSCWriter, FSCReader
import fsc.fsc_binary
import struct

def test_header_healing():
    print("Testing FSC v4 Self-Healing Header...")
    fsc.fsc_binary.FSC_COMMERCIAL_BUILD = True # To see the logs

    fields = [FSCField("val", "UINT8")]
    schema = FSCSchema(fields)
    schema.add_constraint([1], modulus=251)

    writer = FSCWriter(schema)
    writer.add_record([100])
    filename = "test_header.fsc"
    writer.write(filename)

    print("\n[STEP 1] Verifying clean file...")
    reader = FSCReader(filename)
    assert reader.records[0, 0] == 100
    print("✓ Clean file read successfully.")

    print("\n[STEP 2] Corrupting record count (nr) in header...")
    with open(filename, "r+b") as f:
        f.seek(10)
        f.write(struct.pack(">I", 9999))

    reader = FSCReader(filename)
    assert reader.records.shape[0] == 1
    assert reader.records[0, 0] == 100
    print("✓ Header healed successfully (nr recovered).")

    # RESTORE FILE for next single-fault test
    writer.write(filename)

    print("\n[STEP 3] Corrupting field count (nd) in header...")
    with open(filename, "r+b") as f:
        f.seek(5) # nd offset
        f.write(struct.pack(">H", 88))

    reader = FSCReader(filename)
    assert len(reader.data_fields) == 1
    assert reader.records[0, 0] == 100
    print("✓ Header healed successfully (nd recovered).")

    print("\n✓ FSC v4 Header Healing Verified")
    if os.path.exists(filename):
        os.remove(filename)

if __name__ == "__main__":
    test_header_healing()
