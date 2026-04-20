import sys
import os
import struct
sys.path.append(os.getcwd())

from fsc.fsc_binary import FSCField, FSCSchema, FSCWriter, FSCReader
import fsc.fsc_binary

def test_header_stress():
    print("=========================================================")
    print("  FSC v4 HEADER HEALING STRESS TEST")
    print("=========================================================\n")

    fields = [FSCField("val", "UINT8")]
    schema = FSCSchema(fields)
    # This constraint adds a 'stored_0' field because target=None
    schema.add_constraint([1], modulus=251)

    writer = FSCWriter(schema)
    writer.add_record([100])
    filename = "stress_header.fsc"
    writer.write(filename)

    # Expected: nd=1, nc=1, ns=1, nr=1
    EXPECTED = [1, 1, 1, 1]

    targets = [
        ("nd", 5, ">H", 50),
        ("nc", 7, ">H", 30),
        ("ns", 9, ">B", 10),
        ("nr", 10, ">I", 5000),
    ]

    passed = 0
    for name, offset, fmt, bad_val in targets:
        print(f"[*] Testing recovery of field: {name} (offset {offset})")

        with open(filename, "r+b") as f:
            f.seek(offset)
            f.write(struct.pack(fmt, bad_val))

        try:
            reader = FSCReader(filename)
            meta = [len(reader.data_fields), len(reader.constraints), len(reader.all_fields) - len(reader.data_fields), reader.records.shape[0]]
            if meta == EXPECTED:
                print(f"  [✓] SUCCESS: {name} recovered correctly.")
                passed += 1
            else:
                print(f"  [✗] FAILURE: {name} mismatch after healing. Meta: {meta}")
        except Exception as e:
            print(f"  [✗] ERROR: {e}")

        writer.write(filename)

    print(f"\nSummary: {passed}/{len(targets)} header fields successfully healed.")
    if os.path.exists(filename):
        os.remove(filename)

    assert passed == len(targets)

if __name__ == "__main__":
    test_header_stress()
