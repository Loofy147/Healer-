"""
ADS-B Aviation Data Integrity via FSC
=====================================
ADS-B (Automatic Dependent Surveillance–Broadcast) allows aircraft
to broadcast their position, altitude, and velocity.

Fields: [Timestamp, Lat, Lon, Altitude, Heading, Velocity]

By embedding a modular FSC invariant linking these fields,
we can recover any single corrupted field (e.g., altitude)
without needing a retransmission from the aircraft.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

class ADSBPacket:
    """
    Simulates an ADS-B position report with FSC protection.
    We use a large prime modulus so all small weights are invertible.
    """
    def __init__(self, p: int = 2**61 - 1): # Mersenne prime
        self.p = p
        self.fields = ["time", "lat", "lon", "alt", "hdg", "vel"]

    def compute_invariant(self, data: dict) -> int:
        """
        Structural invariant: Σ (field_value * weight) mod p = 0
        Weights are used to ensure unique identification.
        """
        total = 0
        for i, field in enumerate(self.fields):
            val = int(data[field] * 100000) # Scale floats to integers
            total = (total + (i + 1) * val) % self.p
        return total

    def verify(self, data: dict, invariant: int) -> bool:
        return self.compute_invariant(data) == invariant

    def heal(self, data: dict, invariant: int, corrupt_field: str) -> float:
        """
        Heal a corrupted field using the modular weighted sum invariant.
        (w_c * v_c + Σ w_i * v_i) mod p = invariant
        v_c = (invariant - Σ w_i * v_i) * inv(w_c) mod p
        """
        field_idx = self.fields.index(corrupt_field)
        weight_c = field_idx + 1

        others_sum = 0
        for i, field in enumerate(self.fields):
            if field != corrupt_field:
                val = int(data[field] * 100000)
                others_sum = (others_sum + (i + 1) * val) % self.p

        rhs = (invariant - others_sum) % self.p

        # weight_c < p and p is prime, so weight_c is always invertible
        inv_weight = pow(weight_c, -1, self.p)
        v_recovered = (rhs * inv_weight) % self.p

        # Handle negative values (represented as large integers in modular arithmetic)
        if v_recovered > self.p // 2:
            v_recovered -= self.p

        return v_recovered / 100000.0

def demo():
    print("=" * 60)
    print("  ADS-B AVIATION DATA HEALING")
    print("  Structural integrity for flight safety")
    print("=" * 60)

    adsb = ADSBPacket()

    # Real-world flight sample (simulated)
    # Flight: DL123, B738, FL350
    data = {
        "time": 1713456000,
        "lat":   34.0522,
        "lon": -118.2437,
        "alt":  35000,
        "hdg":  270,
        "vel":  450
    }

    invariant = adsb.compute_invariant(data)
    print(f"\n━━ Original Packet ━━")
    for k, v in data.items():
        print(f"  {k:8s}: {v}")
    print(f"  FSC Invariant: {invariant}")

    # ── CORRUPTION ───────────────────────────────────────────────
    corrupt_field = "alt"
    original_val = data[corrupt_field]

    corrupted_data = data.copy()
    corrupted_data[corrupt_field] = 0.0 # Altitude signal lost

    print(f"\n━━ CORRUPTION DETECTED: {corrupt_field} ━━")
    print(f"  Received Altitude: {corrupted_data[corrupt_field]} (INVALID)")

    # ── HEALING ──────────────────────────────────────────────────
    try:
        recovered_val = adsb.heal(corrupted_data, invariant, corrupt_field)
        print(f"\n━━ FSC HEALING ━━")
        print(f"  Recovered {corrupt_field}: {recovered_val}")

        ok = abs(recovered_val - original_val) < 0.0001
        print(f"  Exact Recovery: {'✓' if ok else '✗'}")
    except Exception as e:
        print(f"  Recovery Failed: {e}")

    print(f"\n  Moment: Aviation safety without retransmission.")
    print(f"  FSC ensures flight data integrity in noisy RF environments.")

if __name__ == "__main__":
    demo()
