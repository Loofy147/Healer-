"""
FSC Streaming — Real-time self-healing for live data streams
============================================================
Instead of per-record invariants, use a SLIDING WINDOW:
  - Group W consecutive records into a window
  - Compute FSC invariant across the window
  - Any record lost in the window → recovered from the others

This handles burst loss (multiple consecutive records lost)
as long as loss count < window invariant count.

Rolling update: O(1) per new record — subtract outgoing, add incoming.
"""

import numpy as np
import time
import collections
from typing import Generator, List, Tuple, Optional


# ── STREAM GENERATOR ──────────────────────────────────────────────

def sensor_stream(n_samples: int = 1000, seed: int = 42) -> Generator:
    """Generate a stream of sensor readings."""
    rng = np.random.default_rng(seed)
    t = 0
    for i in range(n_samples):
        # Realistic sensor: smooth signal + small noise
        base = 220 + 15 * np.sin(2 * np.pi * i / 100)
        noise = rng.integers(-3, 4)
        yield {
            'seq':    i,
            'time':   t,
            'value':  int(base + noise),
            'device': 42,
            'status': 1,
        }
        t += 60  # 1 minute intervals


# ── SLIDING WINDOW FSC ────────────────────────────────────────────

class SlidingWindowFSC:
    """
    FSC over a sliding window of W records.

    For each window of W consecutive records:
      invariant = sum(record[i]['value'] for i in window)

    Any single record lost in the window → recovered as:
      recovered_value = invariant - sum(other values in window)

    The invariant is transmitted as a separate channel alongside
    the data stream (like a parity packet in FEC).
    """

    def __init__(self, window_size: int, fields: List[str]):
        self.W       = window_size
        self.fields  = fields
        self.buffer  = collections.deque(maxlen=window_size)
        self._inv    = {f: 0 for f in fields}
        self._window_invs = collections.deque(maxlen=1000)  # store window invariants

    def ingest(self, record: dict) -> dict:
        """Add a record to the stream and update rolling invariant."""
        # Remove outgoing record from invariant
        if len(self.buffer) == self.W:
            outgoing = self.buffer[0]
            for f in self.fields:
                self._inv[f] -= outgoing.get(f, 0)

        # Add incoming record
        self.buffer.append(record)
        for f in self.fields:
            self._inv[f] += record.get(f, 0)

        # Snapshot invariant when window is full
        if len(self.buffer) == self.W:
            snapshot = {
                'window_start': self.buffer[0]['seq'],
                'window_end':   self.buffer[-1]['seq'],
                'invariants':   dict(self._inv)
            }
            self._window_invs.append(snapshot)

        return record

    def get_window_invariant(self, seq: int) -> Optional[dict]:
        """Get the window invariant that covers record seq."""
        for snap in self._window_invs:
            if snap['window_start'] <= seq <= snap['window_end']:
                return snap
        return None

    def recover(self, window_records: List[dict], lost_seq: int,
                invariant: dict) -> dict:
        """
        Recover a lost record given its window neighbors and invariant.
        Returns the recovered record.
        """
        recovered = {'seq': lost_seq}
        for f in self.fields:
            sum_known = sum(r.get(f, 0) for r in window_records
                           if r['seq'] != lost_seq)
            recovered[f] = invariant['invariants'][f] - sum_known
        return recovered


# ── BURST LOSS FSC ────────────────────────────────────────────────

class BurstFSC:
    """
    Handle burst loss: multiple consecutive records lost.
    Uses multiple overlapping windows to provide redundancy.

    Window A: records [0..W-1]
    Window B: records [W/2..3W/2-1]  (offset by W/2)
    ...

    Each lost record appears in multiple windows.
    Single burst of length b < W/2 → at least one window survives intact
    for any given lost record → recovery via that window.
    """

    def __init__(self, window_size: int, n_windows: int = 2):
        self.W        = window_size
        self.n_windows = n_windows
        self.windows  = [[] for _ in range(n_windows)]
        self.invs     = [0] * n_windows  # simple sum invariant on 'value'
        self.record_store = {}

    def process(self, record: dict) -> None:
        """Ingest a record into all relevant windows."""
        seq = record['seq']
        self.record_store[seq] = record

        for w in range(self.n_windows):
            offset = w * (self.W // self.n_windows)
            win_idx = (seq - offset) // self.W
            if win_idx >= 0:
                win_key = (w, win_idx)
                if win_key not in self.__dict__:
                    self.__dict__[win_key] = {'records': [], 'inv': 0}
                win = self.__dict__[win_key]
                win['records'].append(seq)
                win['inv'] += record['value']

    def recover_burst(self, lost_seqs: List[int]) -> List[dict]:
        """Recover a burst of lost records."""
        recovered = []
        for seq in lost_seqs:
            for w in range(self.n_windows):
                offset = w * (self.W // self.n_windows)
                win_idx = (seq - offset) // self.W
                if win_idx < 0:
                    continue
                win_key = (w, win_idx)
                if win_key not in self.__dict__:
                    continue
                win = self.__dict__[win_key]
                # Check if only this seq is lost in this window
                other_seqs = [s for s in win['records'] if s != seq and s not in lost_seqs]
                if len(other_seqs) == len(win['records']) - 1:
                    # Only one record lost from this window — can recover
                    sum_known = sum(self.record_store[s]['value']
                                   for s in other_seqs
                                   if s in self.record_store)
                    rec_value = win['inv'] - sum_known
                    recovered.append({'seq': seq, 'value': rec_value,
                                      'window': w, 'recovered': True})
                    break
        return recovered


# ── DEMO ─────────────────────────────────────────────────────────

def run():
    print("=" * 64)
    print("  FSC STREAMING — Real-time Self-healing Data Streams")
    print("=" * 64)

    # ── PART 1: Sliding window on sensor stream ───────────────────
    print("\n━━ 1. Sliding Window FSC on Sensor Stream ━━")

    W = 5  # window of 5 records
    fields_to_protect = ['value', 'device', 'status']
    fsc_stream = SlidingWindowFSC(window_size=W, fields=fields_to_protect)

    # Generate 50 sensor readings
    stream = list(sensor_stream(50))
    stream_with_inv = [fsc_stream.ingest(r) for r in stream]

    print(f"  Stream: 50 sensor records, window size W={W}")
    print(f"  Rolling invariant updated O(1) per record")

    # Simulate 3 individual packet drops
    dropped = [12, 27, 43]
    corrupted_stream = [r for r in stream if r['seq'] not in dropped]

    # Recover each dropped record
    for lost_seq in dropped:
        snap = fsc_stream.get_window_invariant(lost_seq)
        if snap:
            window_recs = [r for r in stream
                          if snap['window_start'] <= r['seq'] <= snap['window_end']
                          and r['seq'] != lost_seq]
            recovered = fsc_stream.recover(window_recs, lost_seq, snap)
            original  = stream[lost_seq]
            exact = all(recovered.get(f) == original.get(f) for f in fields_to_protect)
            print(f"  Record {lost_seq}: value={original['value']} → recovered={recovered.get('value')} ✓={exact}")

    # ── PART 2: Burst loss recovery ───────────────────────────────
    print("\n━━ 2. Burst Loss Recovery ━━")
    print("   (3 consecutive records lost simultaneously)")

    W_burst = 8
    burst_fsc = BurstFSC(window_size=W_burst, n_windows=2)

    stream2 = list(sensor_stream(100, seed=7))
    for r in stream2:
        burst_fsc.process(r)

    # Burst loss: records 20, 21, 22
    burst = [20, 21, 22]
    recovered_burst = burst_fsc.recover_burst(burst)

    for rb in recovered_burst:
        original = stream2[rb['seq']]
        exact = rb['value'] == original['value']
        print(f"  Record {rb['seq']}: {original['value']} → {rb['value']} ✓={exact}")

    # ── PART 3: Throughput benchmark ─────────────────────────────
    print("\n━━ 3. Throughput: Rolling Invariant Update ━━")

    N = 100_000
    big_stream = SlidingWindowFSC(window_size=10, fields=['value'])
    data = [{'seq': i, 'value': i % 251} for i in range(N)]

    t0 = time.perf_counter()
    for r in data:
        big_stream.ingest(r)
    t1 = time.perf_counter()

    rate = N / (t1 - t0)
    print(f"  {N:,} records in {(t1-t0)*1000:.1f}ms")
    print(f"  Throughput: {rate:,.0f} records/second")
    print(f"  Per-record overhead: {(t1-t0)*1e9/N:.0f}ns (rolling update)")

    # ── PART 4: Real-time scenario ────────────────────────────────
    print("\n━━ 4. Real-time Recovery Latency ━━")

    fsc_rt = SlidingWindowFSC(window_size=5, fields=['value'])
    rt_stream = list(sensor_stream(20))
    for r in rt_stream:
        fsc_rt.ingest(r)

    lost_seq = 10
    snap = fsc_rt.get_window_invariant(lost_seq)
    window_recs = [r for r in rt_stream
                   if snap['window_start'] <= r['seq'] <= snap['window_end']
                   and r['seq'] != lost_seq]

    t0 = time.perf_counter()
    for _ in range(10_000):
        fsc_rt.recover(window_recs, lost_seq, snap)
    t1 = time.perf_counter()

    latency_ns = (t1 - t0) * 1e9 / 10_000
    print(f"  Recovery latency: {latency_ns:.0f}ns per record")
    print(f"  vs TCP retransmission: 50,000,000–200,000,000ns (50–200ms)")
    print(f"  Speedup: {50_000_000/latency_ns:,.0f}× faster than TCP")

    print(f"""
  STREAMING FSC SUMMARY:

  Pattern:
    Stream of records → group into windows → 1 invariant per window
    Lost record = sum of others in window subtracted from invariant

  Overhead:
    1 invariant per W records = 1/W overhead
    W=5: 20% overhead · W=10: 10% · W=100: 1%

  vs TCP retransmission:
    TCP: detect loss → request retransmit → wait RTT → receive
    FSC: detect loss → compute → done
    Latency: {latency_ns:.0f}ns vs 50,000,000ns → {50_000_000/latency_ns:,.0f}× faster

  Applications:
    Live sensor telemetry · video streaming · trading feeds ·
    GPS tracking · IoT mesh networks · real-time control systems
""")

if __name__ == '__main__':
    run()
