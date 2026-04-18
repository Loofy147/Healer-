"""
Power Grid Self-Healing via Kirchhoff's Current Law (KCL)
=========================================================
KCL is a physical structural FSC constraint:
At any node in an electrical circuit, the sum of currents
flowing into that node is equal to the sum of currents
flowing out of that node.

Invariant: Σ I_n = 0 (with signs indicating direction)

This prototype demonstrates how physical laws act as FSC
invariants to provide zero-overhead self-healing for sensor
networks in critical infrastructure.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

class PowerGridNode:
    """
    Models a power grid substation node with multiple feeders/lines.
    Each line has a current sensor.
    """
    def __init__(self, node_id: str, line_names: list):
        self.node_id = node_id
        self.line_names = line_names
        self.n = len(line_names)

    def get_invariant(self, currents: list) -> float:
        """KCL Invariant: Sum of all currents at a node should be zero."""
        return sum(currents)

    def verify(self, currents: list, tolerance: float = 1e-6) -> bool:
        """Verify the structural integrity of the sensor readings."""
        return abs(self.get_invariant(currents)) < tolerance

    def heal(self, currents: list, corrupt_index: int) -> float:
        """
        Heal a corrupted sensor reading using the KCL invariant.
        I_corrupt = - Σ I_others
        """
        known_sum = sum(currents[i] for i in range(self.n) if i != corrupt_index)
        recovered_value = -known_sum
        return recovered_value

def demo():
    print("=" * 60)
    print("  POWER GRID SELF-HEALING (KCL)")
    print("  Physical laws as structural FSC invariants")
    print("=" * 60)

    # Substation node with 5 lines
    lines = ["Feeder-A", "Feeder-B", "Main-In", "Industrial-1", "Residential-2"]
    node = PowerGridNode("SUB-42", lines)

    # Normal operation: Main-In brings in 100A, others distribute it.
    # Currents (Amps): [Feeder-A, Feeder-B, Main-In, Ind-1, Res-2]
    # Note: Inflow is positive, outflow is negative.
    currents = [-25.5, -15.0, 100.0, -40.0, -19.5]

    print(f"\n━━ Substation {node.node_id} ━━")
    for name, val in zip(lines, currents):
        print(f"  {name:15s}: {val:6.1f} A")

    is_valid = node.verify(currents)
    print(f"\n  KCL Verification: {'✓ VALID' if is_valid else '✗ INVALID'}")
    print(f"  Invariant Sum:  {node.get_invariant(currents):.4f}")

    # ── SENSOR FAILURE ───────────────────────────────────────────
    corrupt_idx = 2  # Main-In sensor fails / reports garbage
    original_val = currents[corrupt_idx]

    corrupted_currents = list(currents)
    corrupted_currents[corrupt_idx] = 999.9  # Garbage reading

    print(f"\n━━ SENSOR FAILURE: {lines[corrupt_idx]} ━━")
    print(f"  Corrupted Reading: {corrupted_currents[corrupt_idx]:.1f} A")
    print(f"  KCL Verification:  {'✓' if node.verify(corrupted_currents) else '✗ INVALID (Corruption Detected!)'}")

    # ── FSC HEALING ──────────────────────────────────────────────
    recovered_val = node.heal(corrupted_currents, corrupt_idx)
    healed_currents = list(corrupted_currents)
    healed_currents[corrupt_idx] = recovered_val

    print(f"\n━━ FSC HEALING ━━")
    print(f"  Recovered {lines[corrupt_idx]}: {recovered_val:.1f} A")
    print(f"  Original value was: {original_val:.1f} A")

    ok = abs(recovered_val - original_val) < 1e-6
    print(f"  Exact Recovery: {'✓' if ok else '✗'}")
    print(f"  System State:   {'✓ HEALED' if node.verify(healed_currents) else '✗'}")

    print(f"\n  Moment: Kirchhoff discovered FSC in 1845.")
    print(f"  Physics isn't just descriptive; it is self-healing.")

if __name__ == "__main__":
    demo()
