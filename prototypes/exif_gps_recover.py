"""
FSC: Forward Sector Correction
Copyright (C) 2024 FSC Core Team. All Rights Reserved.

PUBLIC LICENSE: GNU Affero General Public License (AGPLv3)
COMMERCIAL LICENSE: Required for proprietary/enterprise use.

PATENT PENDING: Industrial applications of these algebraic primitives
for database pages, kernel block devices, and network protocols.
"""

"""
EXIF GPS Coordinate Recovery via FSC
====================================
Photos store GPS coordinates in EXIF metadata.
FSC can protect these coordinates using a weighted sum invariant.

Fields: [Lat_Deg, Lat_Min, Lat_Sec, Lon_Deg, Lon_Min, Lon_Sec]
Invariant: Σ (weight_i * value_i) mod m = 0
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

class EXIFGPSHealer:
    def __init__(self, m: int = 1000000):
        self.m = m
        self.weights = [1, 2, 3, 4, 5, 6]

    def compute_invariant(self, coords: list) -> int:
        total = sum(w * v for w, v in zip(self.weights, coords))
        return total % self.m

    def heal(self, coords: list, invariant: int, corrupt_idx: int) -> int:
        weight_c = self.weights[corrupt_idx]
        others_sum = sum(w * v for i, (w, v) in enumerate(zip(self.weights, coords)) if i != corrupt_idx)

        # (weight_c * v_c + others_sum) % m = invariant
        # weight_c * v_c = (invariant - others_sum) % m
        rhs = (invariant - others_sum) % self.m

        # Simple search for this demo (weights are small)
        for v_candidate in range(self.m):
            if (weight_c * v_candidate) % self.m == rhs:
                return v_candidate
        return -1

def demo():
    print("=" * 60)
    print("  EXIF GPS COORDINATE RECOVERY")
    print("  Protecting photo metadata with FSC")
    print("=" * 60)

    # Coordinates: 34° 03' 08" N, 118° 14' 37" W
    # Represented as [34, 3, 8, 118, 14, 37]
    gps_coords = [34, 3, 8, 118, 14, 37]

    healer = EXIFGPSHealer()
    inv = healer.compute_invariant(gps_coords)

    print("\n━━ Original GPS Metadata ━━")
    print(f"  Coordinates: {gps_coords}")
    print(f"  FSC Invariant: {inv}")

    # ── CORRUPTION ───────────────────────────────────────────────
    corrupt_idx = 3 # Lon_Deg (118)
    corrupted_coords = list(gps_coords)
    corrupted_coords[corrupt_idx] = 0 # Data stripped or corrupted

    print(f"\n━━ METADATA STRIPPED/CORRUPTED ━━")
    print(f"  Corrupted Field: Index {corrupt_idx} (Lon_Deg)")
    print(f"  Corrupted Data:  {corrupted_coords}")

    # ── FSC HEALING ──────────────────────────────────────────────
    recovered_val = healer.heal(corrupted_coords, inv, corrupt_idx)
    healed_coords = list(corrupted_coords)
    healed_coords[corrupt_idx] = recovered_val

    print(f"\n━━ FSC HEALING ━━")
    print(f"  Recovered Lon_Deg: {recovered_val}")
    print(f"  Exact Recovery:    {'✓' if recovered_val == gps_coords[corrupt_idx] else '✗'}")
    print(f"  Healed Metadata:   {healed_coords}")

    print(f"\n  Moment: GPS coordinates recovered from a single integer invariant.")
    print(f"  FSC turns metadata into a self-healing structural format.")

if __name__ == "__main__":
    demo()
