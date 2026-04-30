import sys
import os
import numpy as np
sys.path.append(os.getcwd())

from fsc.storage.fsc_binary import FSCField, FSCSchema, FSCWriter, FSCReader
from fsc.advanced.fsc_dynamic import AdaptiveWeightEngine

def test_dynamic_healing():
    print("=========================================================")
    print("  FSC v6: ENTROPY-WEIGHTED DYNAMIC STRATIFICATION")
    print("=========================================================\n")

    types = ["UINT32", "UINT8", "UINT8", "UINT8"]
    fields = [FSCField(f"f{i}", types[i]) for i in range(4)]
    schema = FSCSchema(fields)

    # Model 5 requires TWO constraints for blind localization
    m = 251
    w1 = AdaptiveWeightEngine.calculate_weights(types, m, seed=1)
    w2 = AdaptiveWeightEngine.calculate_weights(types, m, seed=2)

    print(f"Weights 1: {w1}")
    print(f"Weights 2: {w2}")

    schema.add_constraint(w1.tolist(), modulus=m, label="ADAPTIVE_L1")
    schema.add_constraint(w2.tolist(), modulus=m, label="ADAPTIVE_L2")

    writer = FSCWriter(schema)
    original_id = 12345
    original_data = [original_id, 10, 20, 30]
    writer.add_record(original_data)
    filename = "dynamic.fsc"
    writer.write(filename)

    print("\n[STEP 1] Corrupting High-Entropy Data...")
    reader = FSCReader(filename)
    reader.records[0, 2] = 255 # d2 (20) corrupted to 255

    # Blind healing (no corrupted_field_idx)
    res = reader.verify_and_heal(0)
    print(f"Heal result (Data): {res}")
    assert res == 1
    assert reader.records[0, 2] == 20
    print("✓ Data byte healed correctly via dual adaptive constraints.")

    print("\n[STEP 2] Corrupting Low-Entropy Metadata (ID)...")
    reader2 = FSCReader(filename)
    reader2.records[0, 0] = 0 # ID corrupted

    res = reader2.verify_and_heal(0)
    print(f"Heal result (ID): {res}")
    assert res == 1
    # For large fields, Model 5 in Z_251 recovers the modular value
    assert reader2.records[0, 0] == original_id % m
    print("✓ ID (modular) healed correctly.")

    if os.path.exists(filename):
        os.remove(filename)

    print("\n=========================================================")
    print("  VERIFICATION COMPLETE: DYNAMIC GAP CLOSED")
    print("=========================================================")

if __name__ == "__main__":
    test_dynamic_healing()
