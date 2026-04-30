import numpy as np
from fsc.storage.fsc_binary import FSCField, FSCSchema, FSCWriter, FSCReader
from fsc.core.fsc_native import FSC_SUCCESS

def test_layered_binary():
    print("━━ LAYERED BINARY PROTECTION TEST (FSC v6) ━━")
    fields = [FSCField("id", "INT64"), FSCField("val", "INT64")]
    schema = FSCSchema(fields)
    schema.add_constraint([1, 7], modulus=251, label="C1") # Stored constraint

    writer = FSCWriter(schema)
    writer.enable_layered_protection()

    data = [[i, i*10] for i in range(5)]
    writer.add_records(data)

    filename = "layered_test.fsc"
    writer.write(filename)
    print(f"File {filename} written with layered protection.")

    reader = FSCReader(filename)
    print(f"Reader loaded version: {reader.ver}")
    assert reader.ver == 6

    valid_map = reader.verify_all_records()
    print(f"Verification map: {valid_map}")
    assert np.all(valid_map)

    # Corrupt a record and verify it fails both manifolds
    print("\nCorrupting record 2 field 1...")
    reader.records[2, 1] += 5
    valid_map_corrupt = reader.verify_all_records()
    print(f"Verification map after corruption: {valid_map_corrupt}")
    assert not valid_map_corrupt[2]

    # Heal
    print("Attempting to heal...")
    res = reader.verify_and_heal(2, corrupted_field_idx=1)
    print(f"Healing result: {res}")
    assert res == FSC_SUCCESS
    assert reader.records[2, 1] == 20
    assert np.all(reader.verify_all_records())
    print("✓ Layered healing successful.")

if __name__ == "__main__":
    test_layered_binary()
