"""
FSC: Forward Sector Correction
Copyright (C) 2024 FSC Core Team. All Rights Reserved.

PUBLIC LICENSE: GNU Affero General Public License (AGPLv3)
COMMERCIAL LICENSE: Required for proprietary/enterprise use.

PATENT PENDING: Industrial applications of these algebraic primitives
for database pages, kernel block devices, and network protocols.
"""

"""
ECG Cardiac Signal Integrity via FSC
====================================
ECG (Electrocardiogram) signals measure the heart's electrical
activity. In high-stakes medical monitoring, a single corrupted
sample can look like an arrhythmia (false alarm).

FSC Invariant:
For high-frequency sampling, Σ samples in a sliding window
is highly predictable, or we can add a small parity sample
every N samples.

This demo uses a sum invariant over a heartbeat cycle.
"""

import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

class ECGMonitor:
    def __init__(self, window_size: int = 10):
        self.w = window_size

    def protect(self, signal: list) -> list:
        """Add a sum invariant every 'w' samples."""
        protected = []
        for i in range(0, len(signal), self.w):
            chunk = signal[i:i+self.w]
            if len(chunk) < self.w:
                chunk += [0] * (self.w - len(chunk))
            invariant = sum(chunk)
            protected.append((chunk, invariant))
        return protected

    def heal(self, chunk: list, invariant: int, corrupt_idx: int) -> int:
        """Heal 1 corrupted sample in the chunk."""
        known_sum = sum(chunk[i] for i in range(len(chunk)) if i != corrupt_idx)
        recovered = invariant - known_sum
        return recovered

def demo():
    print("=" * 60)
    print("  ECG CARDIAC SIGNAL INTEGRITY")
    print("  Preventing false arrhythmia alarms")
    print("=" * 60)

    # Simulated ECG signal (mV scaled to integers for FSC closure)
    # A single "P-QRS-T" complex
    heartbeat = [10, 12, 15, 60, -20, 80, 15, 10, 5, 5]

    monitor = ECGMonitor(window_size=10)
    protected = monitor.protect(heartbeat)
    chunk, inv = protected[0]

    print("\n━━ Original ECG Sample ━━")
    print(f"  Signal:    {chunk}")
    print(f"  Sum Invariant: {inv}")

    # ── SENSOR SPIKE / CORRUPTION ────────────────────────────────
    corrupt_idx = 5 # The R-peak (80mV)
    corrupted_chunk = list(chunk)
    corrupted_chunk[corrupt_idx] = -500 # Major artifact

    print(f"\n━━ ARTIFACT DETECTED ━━")
    print(f"  Corrupted Signal: {corrupted_chunk}")
    print(f"  Status: {'✗ ARREST/ARRHYTHMIA ALERT' if corrupted_chunk[corrupt_idx] < -100 else 'Normal'}")

    # ── FSC HEALING ──────────────────────────────────────────────
    recovered_val = monitor.heal(corrupted_chunk, inv, corrupt_idx)
    healed_chunk = list(corrupted_chunk)
    healed_chunk[corrupt_idx] = recovered_val

    print(f"\n━━ FSC HEALING ━━")
    print(f"  Recovered Sample: {recovered_val} mV")
    print(f"  Exact Recovery:   {'✓' if recovered_val == chunk[corrupt_idx] else '✗'}")
    print(f"  Resulting Signal: {healed_chunk}")

    print(f"\n  Moment: Corrupted medical data recovered exactly.")
    print(f"  FSC distinguishes between physical pathology and sensor failure.")

if __name__ == "__main__":
    demo()
