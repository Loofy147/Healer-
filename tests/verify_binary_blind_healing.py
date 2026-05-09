import sys
import os
import numpy as np
sys.path.append(os.getcwd())

from fsc.storage.fsc_binary import FSCField, FSCSchema, FSCWriter, FSCReader
from fsc.core.fsc_native import is_native_available

def test_binary_blind_healing():
    print("Testing FSCReader Blind Multi-Fault Healing...")
    if not is_native_available():
        print("  [SKIP] Native library not available.")
        return

    filename = "blind_test.fsc"
    modulus = 251

    n_data = 10
    k_parity = 4 # Handle 2 blind errors

    fields = [FSCField(f"v{i}", "UINT8") for i in range(n_data)]
    schema = FSCSchema(fields)

    # Add constraints that match native solver expectations: (i+1)^j
    for j in range(k_parity):
        weights = [pow(i + 1, j, modulus) for i in range(n_data)]
        schema.add_constraint(weights, target=None, modulus=modulus)

    writer = FSCWriter(schema)
    original_data = np.random.randint(1, modulus, n_data).tolist()
    writer.add_record(original_data)
    writer.write(filename)

    reader = FSCReader(filename)
    reader.records[0, 2] = (reader.records[0, 2] + 10) % modulus
    reader.records[0, 7] = (reader.records[0, 7] + 25) % modulus

    print(f"  Corrupted Record 0: {reader.records[0]}")

    # 3. Attempt healing
    res = reader.verify_and_heal(0)

    if res == 1:
        healed_data = reader.records[0, :n_data].tolist()
        if healed_data == original_data:
            print("✓ Binary Blind Recovery Successful and Correct")
        else:
            print(f"✗ Binary Blind Recovery returned Success but data is incorrect")
    else:
        print(f"✗ Binary Blind Recovery Failed with code {res}")

    if os.path.exists(filename):
        os.remove(filename)

if __name__ == "__main__":
    test_binary_blind_healing()
