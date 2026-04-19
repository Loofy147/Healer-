from fsc.fsc_binary import FSCField, FSCSchema, FSCWriter, FSCReader
import os
import random

def demo():
    print("━━ FSC BINARY FORMAT DEMO ━━")

    # 1. Define Schema
    fields = [
        FSCField("timestamp", "UINT32"),
        FSCField("device_id", "UINT16"),
        FSCField("value", "INT32"),
        FSCField("quality", "UINT8")
    ]
    schema = FSCSchema(fields)
    # Add TWO independent stored invariants for Model 5 Auto-Localization
    schema.add_constraint([1, 1, 1, 1], label="sum_all")
    schema.add_constraint([1, 2, 3, 4], label="weighted_sum")

    # 2. Generate Data
    original_data = []
    writer = FSCWriter(schema)
    for i in range(5):
        row = [1600000000 + i, 101, random.randint(20, 30), 255]
        original_data.append(row)
        writer.add_record(row)

    # 3. Write to file
    filename = "demo.fsc"
    writer.write(filename)
    print(f"Created '{filename}' with 5 records and 2 constraints.")

    # 4. Read back and verify (No corruption)
    reader = FSCReader(filename)
    loaded_data = reader.get_data()
    print(f"Read back verified (no corruption): {loaded_data == original_data}")

    # 5. Simulate CORRUPTION
    # Let's corrupt the 'value' field (index 2) of the 3rd record (index 2)
    print("\nSimulating disk corruption on record 2, field 'value'...")
    original_val = reader.records[2][2]
    reader.records[2][2] = -999999 # Corrupted value

    # 6. AUTO-HEAL (Model 5)
    print("Attempting AUTOMATIC healing (Model 5)...")
    success = reader.verify_and_heal(2)
    healed_val = reader.records[2][2]

    print(f"Healing status: {success}")
    print(f"Original Value: {original_val}")
    print(f"Healed Value:   {healed_val}")
    print(f"Recovery EXACT: {original_val == healed_val}")

    # Cleanup
    if os.path.exists(filename):
        os.remove(filename)

if __name__ == "__main__":
    demo()
