from fsc_binary import FSCField, FSCSchema
from fsc_page import FSCPageWriter, FSCPageReader
import os

def test_2d_healing():
    print("Testing 2D Page Healing (Multiple Erasures)...")
    fields = [FSCField("f0", "INT32"), FSCField("f1", "INT32")]
    schema = FSCSchema(fields)
    # TWO independent row constraints for Auto-Localization
    schema.add_constraint([1, 1], label="sum")
    schema.add_constraint([1, 2], label="weighted_sum")

    writer = FSCPageWriter(schema, page_size=5)
    original_data = [
        [10, 20],  # Row 0
        [30, 40],  # Row 1
        [50, 60],  # Row 2
    ]
    writer.write_page(original_data, "test_2d.fsc")

    reader = FSCPageReader("test_2d.fsc")

    # Corrupt Row 0 completely (Two erasures) -> Row-wise healing fails.
    reader.data_records[0] = [0, 0]
    # Corrupt Row 1 partially (One erasure) -> Row-wise healing should fix it.
    reader.data_records[1][1] = 0

    print(f"  Corrupted Data (Row 0 lost [0,0], Row 1 corrupted [30,0]):")
    for r in reader.data_records: print(f"    {r}")

    success = reader.verify_and_heal_2d()
    healed_data = reader.get_data()

    print(f"  Healed Data:")
    for r in healed_data: print(f"    {r}")

    if success and healed_data == original_data:
        print("✓ 2D Page Healing Verified (Multi-Erasure Recovery)")
    else:
        print("✗ 2D Page Healing Failed")
        exit(1)

if __name__ == "__main__":
    test_2d_healing()
