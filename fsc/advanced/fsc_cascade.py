"""
FSC: Forward Sector Correction
Copyright (C) 2024 FSC Core Team. All Rights Reserved.

PUBLIC LICENSE: GNU Affero General Public License (AGPLv3)
COMMERCIAL LICENSE: Required for proprietary/enterprise use.

PATENT PENDING: Industrial applications of these algebraic primitives
for database pages, kernel block devices, and network protocols.
"""

import random
import numpy as np
from typing import List, Dict, Set

class CascadeHealer:
    """
    Implements cross-record cascade healing.
    Records are nodes in a graph, and constraints are hyperedges.
    Fixing one field can satisfy a constraint that uniquely identifies
    and heals another field in a DIFFERENT record.
    """

    def __init__(self):
        self.records = {} # id -> list of fields
        self.constraints = [] # list of (record_indices, target, modulus)

    def add_record(self, rid: int, fields: List[int]):
        self.records[rid] = list(fields)

    def add_constraint(self, involved: List[tuple], target: int, modulus: int = None):
        """
        involved: list of (record_id, field_index)
        """
        self.constraints.append({
            'involved': involved,
            'target': target,
            'modulus': modulus
        })

    def get_value(self, rid, fidx):
        return self.records[rid][fidx]

    def set_value(self, rid, fidx, val):
        self.records[rid][fidx] = val

    def heal_cascade(self, known_corrupted: Set[tuple]):
        """
        known_corrupted: set of (rid, fidx)
        """
        corrupted = set(known_corrupted)
        healed_any = True

        print(f"Starting cascade healing for {len(corrupted)} corrupted fields...")

        # Optimization: Pre-calculate current sums for all constraints to enable O(1) residual calculation
        constraint_sums = []
        for c in self.constraints:
            s = sum(self.get_value(rid, fidx) for rid, fidx in c['involved'])
            constraint_sums.append(s)

        while healed_any and corrupted:
            healed_any = False

            for i, c in enumerate(self.constraints):
                # Find how many corrupted fields are in this constraint
                involved_corrupted = [p for p in c['involved'] if p in corrupted]

                if len(involved_corrupted) == 1:
                    # EXACTLY one corrupted field in this constraint! We can heal it.
                    target_p = involved_corrupted[0]
                    rid, fidx = target_p

                    # O(1) residual calculation:
                    # target = (sum_others + recovered_val) % modulus
                    # current_sum = sum_others + corrupted_val
                    # recovered_val = target - (current_sum - corrupted_val)

                    corrupted_val = self.get_value(rid, fidx)
                    current_sum = constraint_sums[i]
                    sum_others = current_sum - corrupted_val

                    if c['modulus']:
                        recovered = (c['target'] - sum_others) % c['modulus']
                    else:
                        recovered = c['target'] - sum_others

                    # Update value and sum
                    self.set_value(rid, fidx, recovered)
                    constraint_sums[i] = c['target'] # By definition, the constraint is now satisfied

                    # Also need to update OTHER constraints that involve this field!
                    # For simplicity in this O(N) loop, we just update the sums for any constraint sharing this field.
                    for j, other_c in enumerate(self.constraints):
                        if i != j and target_p in other_c['involved']:
                            constraint_sums[j] += (recovered - corrupted_val)

                    corrupted.remove(target_p)
                    healed_any = True
                    print(f"  [CASCADE] Healed ({rid}, {fidx}) via constraint: sum({c['involved']}) = {c['target']}")
                    break # Restart scan with updated corrupted set

        return len(corrupted) == 0

def demo():
    print("━━ CROSS-RECORD CASCADE HEALING DEMO ━━")
    healer = CascadeHealer()
    healer.add_record(0, [2, 3, 5])
    healer.add_record(1, [5, 7, 8])
    healer.add_record(2, [8, 10, 12])
    healer.add_constraint([(0,0), (0,1), (0,2)], 10)
    healer.add_constraint([(1,0), (1,1), (1,2)], 20)
    healer.add_constraint([(2,0), (2,1), (2,2)], 30)
    healer.add_constraint([(0,2), (1,0)], 10)
    healer.add_constraint([(1,2), (2,0)], 16)
    corrupted_indices = [(0,2), (1,0), (1,1), (1,2), (2,0)]
    for rid, fidx in corrupted_indices: healer.set_value(rid, fidx, 0)
    success = healer.heal_cascade(set(corrupted_indices))
    print(f"\nHealing result: {'SUCCESS' if success else 'FAILURE'}")
    assert healer.records[0] == [2, 3, 5]
    assert healer.records[1] == [5, 7, 8]
    assert healer.records[2] == [8, 10, 12]

if __name__ == "__main__":
    demo()
