"""
Structural Network Protocols — Self-Healing Packets
===================================================
Designing network headers where validity is structurally embedded.
Every field participates in multiple independent constraints.
"""

from typing import List, Optional, Dict
from fsc_structural import AlgebraicFormat

class StructuralPacket:
    """
    A network packet with a self-healing header.
    Header: [version, src_id, dst_id, seq_num, length, payload_sum]
    """
    FIELD_NAMES = ["version", "src_id", "dst_id", "seq_num", "length", "payload_sum"]

    def __init__(self, m: int = 251):
        self.m = m

    def _get_format(self) -> AlgebraicFormat:
        fmt = AlgebraicFormat(self.FIELD_NAMES)

        # Ring of constraints: each field in exactly 2 constraints
        # Intersection of any two constraints is a single field.

        # C1: version + src_id + dst_id = T1
        fmt.add_constraint([1, 1, 1, 0, 0, 0], 100, modulus=self.m, label="C1")
        # C2: dst_id + seq_num + length = T2
        fmt.add_constraint([0, 0, 1, 1, 1, 0], 150, modulus=self.m, label="C2")
        # C3: length + payload_sum + version = T3
        fmt.add_constraint([1, 0, 0, 0, 1, 1], 200, modulus=self.m, label="C3")
        # C4: src_id + seq_num + payload_sum = T4
        fmt.add_constraint([0, 1, 0, 1, 0, 1], 100, modulus=self.m, label="C4")

        return fmt

    def build(self, src_id: int, dst_id: int):
        """
        Calculates dependent fields (seq_num, length, payload_sum)
        to satisfy the 4 constraints.

        System (mod m):
        1. v + s + d = 100 (C1)  --> Restricted input!
        Actually, let's pick 2 fields and solve for others.

        Wait, we have 6 fields and 4 constraints -> 2 degrees of freedom.
        Let's pick src_id and dst_id as free.
        """
        s = src_id % self.m
        d = dst_id % self.m

        # C1: v + s + d = 100 => v = 100 - s - d
        v = (100 - s - d) % self.m

        # C3: l + p + v = 200 => l + p = 200 - v
        rhs_3 = (200 - v) % self.m

        # C2: d + seq + l = 150 => seq + l = 150 - d
        rhs_2 = (150 - d) % self.m

        # C4: s + seq + p = 100 => seq + p = 100 - s
        rhs_4 = (100 - s) % self.m

        # We have:
        # l + p = rhs3
        # seq + l = rhs2
        # seq + p = rhs4

        # (seq + l) + (seq + p) - (l + p) = 2*seq
        # rhs2 + rhs4 - rhs3 = 2*seq

        rhs_seq2 = (rhs_2 + rhs_4 - rhs_3) % self.m
        # Find seq: seq = rhs_seq2 * inv(2)
        inv2 = pow(2, -1, self.m)
        seq = (rhs_seq2 * inv2) % self.m

        # l = rhs2 - seq
        l = (rhs_2 - seq) % self.m
        # p = rhs4 - seq
        p = (rhs_4 - seq) % self.m

        return {
            "version": v,
            "src_id": s,
            "dst_id": d,
            "seq_num": seq,
            "length": l,
            "payload_sum": p
        }

    def verify_and_heal(self, header_fields: Dict[str, int]) -> Optional[Dict[str, int]]:
        fmt = self._get_format()
        fmt.set_fields(header_fields)

        violations = fmt.validate()
        if not violations:
            return header_fields

        print(f"  [NETWORK] Corruption detected. Violations: {violations}")
        healed = fmt.heal()
        if healed:
            header_fields[healed['field']] = healed['recovered']
            print(f"  [NETWORK] Field '{healed['field']}' recovered: {healed['recovered']}")
            return header_fields
        return None

def demo():
    print("━━ STRUCTURAL NETWORK PACKET DEMO ━━")
    pkt_proto = StructuralPacket()

    # 1. Build packet
    header = pkt_proto.build(src_id=10, dst_id=20)
    print(f"Valid Header: {header}")

    # 2. Test healing for each field
    for field in pkt_proto.FIELD_NAMES:
        print(f"\nCorrupting '{field}'...")
        corrupt_header = dict(header)
        corrupt_header[field] = (corrupt_header[field] + 42) % 251

        healed = pkt_proto.verify_and_heal(corrupt_header)
        if healed and healed[field] == header[field]:
            print(f"  ✓ '{field}' healed correctly.")
        else:
            print(f"  ✗ Failed to heal '{field}'.")

if __name__ == "__main__":
    demo()
