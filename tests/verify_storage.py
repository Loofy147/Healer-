from fsc.fsc_storage import StructuralLog
import random

def test_stream_healing():
    print("Testing StructuralLog Stream Healing (Zero Overhead)")
    m = 251
    log = StructuralLog(m=m, fields_per_record=6) # 4 data fields, 2 structural

    # 1. Fill log with 100 records
    originals = []
    for i in range(100):
        data = [random.randint(0, m-1) for _ in range(4)]
        log.append(data)
        originals.append(list(log.records[-1]))

    print(f"Created log with {len(log.records)} records.")

    # 2. Corrupt 10 random records at random positions
    corrupted_indices = random.sample(range(100), 10)
    for idx in corrupted_indices:
        field_idx = random.randint(0, 5)
        original_val = log.records[idx][field_idx]
        bad_val = (original_val + random.randint(1, 100)) % m
        log.records[idx][field_idx] = bad_val

    # 3. Verify and heal the entire log
    healed_count = 0
    for i in range(100):
        success = log.verify_and_heal(i)
        if not success:
             print(f"Failed to verify/heal record {i}")
        elif i in corrupted_indices:
             healed_count += 1

    # 4. Final validation
    matches = sum(1 for i in range(100) if log.records[i] == originals[i])
    print(f"\nFinal Result: {matches}/100 records match originals.")
    print(f"Successfully healed {healed_count} corrupted packets.")

    assert matches == 100, "Log failed to heal completely!"
    print("✓ STREAM HEALING VERIFIED (Zero Overhead)")

if __name__ == "__main__":
    test_stream_healing()
