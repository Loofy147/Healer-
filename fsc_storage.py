"""
Structural Storage — Position-Based Self-Healing
================================================
Demonstrating Model 4 (FiberRecord) for a zero-overhead log format.
Every record at index i satisfies multiple positional invariants.
This allows unique identification AND recovery of any single corrupted field.
"""

from typing import List, Optional, Dict
from fsc_structural import AlgebraicFormat

class StructuralLog:
    """
    A log where every record is algebraically dependent on its position.
    Uses an overdetermined set of positional constraints.
    """
    def __init__(self, m: int = 251, fields_per_record: int = 4):
        self.m = m
        self.fields_per_record = fields_per_record
        self.records: List[List[int]] = []

    def _get_format_for_pos(self, pos: int) -> AlgebraicFormat:
        """
        Creates an AlgebraicFormat for a specific position.
        The targets are derived from the position.
        """
        fmt = AlgebraicFormat([f"f{i}" for i in range(self.fields_per_record)])

        # Constraint 1: Simple sum mod m
        # sum(v_i) % m == pos % m
        fmt.add_constraint([1] * self.fields_per_record, pos % self.m, modulus=self.m, label="pos_sum")

        # Constraint 2: Weighted sum mod m
        # sum((i+1) * v_i) % m == (pos * 13) % m
        weights = [i + 1 for i in range(self.fields_per_record)]
        fmt.add_constraint(weights, (pos * 13) % self.m, modulus=self.m, label="pos_weighted")

        return fmt

    def append(self, data: List[int]):
        """
        Append a new record. We take n-2 fields and compute the last 2
        such that the two positional constraints are satisfied.
        """
        assert len(data) == self.fields_per_record - 2
        pos = len(self.records)

        # We need to solve:
        # 1. v_n-2 + v_n-1 = target1 - sum(v_0...v_n-3)  (mod m)
        # 2. (n-1)*v_n-2 + n*v_n-1 = target2 - sum((j+1)*v_j) (mod m)

        target1 = pos % self.m
        target2 = (pos * 13) % self.m

        s1 = sum(data) % self.m
        s2 = sum((j + 1) * data[j] for j in range(len(data))) % self.m

        rhs1 = (target1 - s1) % self.m
        rhs2 = (target2 - s2) % self.m

        # System:
        # v_a + v_b = rhs1
        # w_a*v_a + w_b*v_b = rhs2
        # where w_a = n-1, w_b = n

        wa = self.fields_per_record - 1
        wb = self.fields_per_record

        # v_a = rhs1 - v_b
        # wa*(rhs1 - v_b) + wb*v_b = rhs2
        # wa*rhs1 - wa*v_b + wb*v_b = rhs2
        # (wb - wa)*v_b = rhs2 - wa*rhs1

        denom = (wb - wa) % self.m
        inv_denom = pow(denom, -1, self.m)
        vb = ((rhs2 - wa * rhs1) * inv_denom) % self.m
        va = (rhs1 - vb) % self.m

        full_record = list(data) + [va, vb]
        self.records.append(full_record)
        return pos

    def verify_and_heal(self, index: int) -> bool:
        """
        Checks if the record at index is valid.
        If not, heals it using its structural position.
        """
        fmt = self._get_format_for_pos(index)
        fmt.set_fields({f"f{i}": v for i, v in enumerate(self.records[index])})

        violations = fmt.validate()
        if not violations:
            return True

        # print(f"  [DETECT] Record {index} invalid. Violations: {violations}")
        healed = fmt.heal()
        if healed:
            # healed['field'] is 'fi', get i
            field_name = healed['field']
            field_idx = int(field_name[1:])
            self.records[index][field_idx] = healed['recovered']
            # print(f"  [HEAL] Field {field_idx} recovered: {healed['recovered']}")
            return True

        return False

    def __repr__(self):
        return f"StructuralLog(records={len(self.records)}, m={self.m})"
