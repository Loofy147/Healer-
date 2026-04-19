from fsc.fsc_network import StructuralPacket
import random

def test_network_healing():
    print("Testing Structural Network Protocol (Self-Healing Headers)")
    proto = StructuralPacket(m=251)

    # Simulate a stream of 50 packets
    original_headers = []
    stream = []
    for i in range(50):
        src = random.randint(1, 100)
        dst = random.randint(1, 100)
        header = proto.build(src_id=src, dst_id=dst)
        original_headers.append(header)
        stream.append(dict(header))

    print(f"Generated {len(stream)} packets.")

    # 2. Corrupt headers in transit (random single-field corruption)
    corrupted_indices = random.sample(range(50), 10)
    for idx in corrupted_indices:
        field = random.choice(proto.FIELD_NAMES)
        stream[idx][field] = (stream[idx][field] + random.randint(1, 100)) % 251
        print(f"  [TRANSIT] Packet {idx}: field '{field}' corrupted.")

    # 3. Receiver heals the stream
    healed_count = 0
    for i in range(50):
        healed = proto.verify_and_heal(stream[i])
        if healed != original_headers[i]:
             # Check if it was one of the corrupted ones
             if i in corrupted_indices:
                 print(f"  ✗ Failed to heal packet {i}")
        elif i in corrupted_indices:
             healed_count += 1

    # 4. Final validation
    matches = sum(1 for i in range(50) if stream[i] == original_headers[i])
    print(f"\nFinal Result: {matches}/50 packets match original headers.")
    print(f"Successfully healed {healed_count} corrupted packets.")

    assert matches == 50, "Network protocol failed to heal all corruptions!"
    print("✓ NETWORK HEALING VERIFIED (Structural Protcol)")

if __name__ == "__main__":
    test_network_healing()
