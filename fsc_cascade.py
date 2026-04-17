import random
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

        while healed_any and corrupted:
            healed_any = False

            for c in self.constraints:
                # Find how many corrupted fields are in this constraint
                involved_corrupted = [p for p in c['involved'] if p in corrupted]

                if len(involved_corrupted) == 1:
                    # EXACTLY one corrupted field in this constraint! We can heal it.
                    target_p = involved_corrupted[0]
                    rid, fidx = target_p

                    # Calculate sum of all OTHER fields in constraint
                    sum_others = 0
                    for orid, ofidx in c['involved']:
                        if (orid, ofidx) != target_p:
                            sum_others += self.get_value(orid, ofidx)

                    # Recover
                    if c['modulus']:
                        recovered = (c['target'] - sum_others) % c['modulus']
                    else:
                        recovered = c['target'] - sum_others

                    self.set_value(rid, fidx, recovered)
                    corrupted.remove(target_p)
                    healed_any = True
                    print(f"  [CASCADE] Healed ({rid}, {fidx}) via constraint: sum({c['involved']}) = {c['target']}")
                    break # Restart scan with updated corrupted set

        return len(corrupted) == 0

# ── DEMO ───────────────────────────────────────────────────────────

def demo():
    print("━━ CROSS-RECORD CASCADE HEALING DEMO ━━")
    healer = CascadeHealer()

    # 3 Records forming a chain through shared invariants
    # R0 [2, 3, 5]  - sum=10
    # R1 [5, 7, 8]  - sum=20
    # R2 [8, 10, 12] - sum=30

    # Links:
    # L1: R0[2] + R1[0] = 10 (shared value 5)
    # L2: R1[2] + R2[0] = 16 (shared value 8)

    healer.add_record(0, [2, 3, 5])
    healer.add_record(1, [5, 7, 8])
    healer.add_record(2, [8, 10, 12])

    # Record-level invariants (Internal)
    healer.add_constraint([(0,0), (0,1), (0,2)], 10)
    healer.add_constraint([(1,0), (1,1), (1,2)], 20)
    healer.add_constraint([(2,0), (2,1), (2,2)], 30)

    # Graph-level invariants (Cross-record)
    healer.add_constraint([(0,2), (1,0)], 10)
    healer.add_constraint([(1,2), (2,0)], 16)

    print("Initial Data:")
    print(f"  R0: {healer.records[0]}")
    print(f"  R1: {healer.records[1]}")
    print(f"  R2: {healer.records[2]}")

    # SIMULATE MASSIVE CORRUPTION (5 fields lost)
    # This renders R1 completely unrecoverable by its own internal constraint (3/3 lost)
    # Only R0 and R2 internal constraints have 1 loss.

    corrupted_indices = [(0,2), (1,0), (1,1), (1,2), (2,0)]
    for rid, fidx in corrupted_indices:
        healer.set_value(rid, fidx, 0)

    print("\nCorruption Applied (0s):")
    print(f"  R0: {healer.records[0]}")
    print(f"  R1: {healer.records[1]}")
    print(f"  R2: {healer.records[2]}")

    # HEAL
    success = healer.heal_cascade(set(corrupted_indices))

    print(f"\nHealing result: {'SUCCESS' if success else 'FAILURE'}")
    print(f"Final Data:")
    print(f"  R0: {healer.records[0]} (Exact: {healer.records[0] == [2,3,5]})")
    print(f"  R1: {healer.records[1]} (Exact: {healer.records[1] == [5,7,8]})")
    print(f"  R2: {healer.records[2]} (Exact: {healer.records[2] == [8,10,12]})")

if __name__ == "__main__":
    demo()
