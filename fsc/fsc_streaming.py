import collections
import time
import numpy as np
from typing import List, Optional, Dict, Iterator

def sensor_stream(n_samples: int, seed: int = 42) -> Iterator[dict]:
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
        Recover a lost record using O(1) residual calculation if current sum is available.
        """
        recovered = {'seq': lost_seq}

        # Optimization: use numpy for window sums if possible
        for f in self.fields:
            # sum_known = sum(r.get(f, 0) for r in window_records if r['seq'] != lost_seq)
            # Instead of O(W) sum, we could use a stored rolling sum if we were inside the ingest flow,
            # but for external recovery we use the invariant minus others.

            # Vectorized O(W) is still better than Python loop O(W)
            vals = np.array([r.get(f, 0) for r in window_records if r['seq'] != lost_seq], dtype=np.int64)
            sum_known = np.sum(vals)
            recovered[f] = int(invariant['invariants'][f] - sum_known)

        return recovered


# ── BURST LOSS FSC ────────────────────────────────────────────────

class BurstFSC:
    def __init__(self, window_size: int, n_windows: int = 2):
        self.W        = window_size
        self.n_windows = n_windows
        self.record_store = {}
        # Storage for window states
        self.win_states = {}

    def process(self, record: dict) -> None:
        seq = record['seq']
        self.record_store[seq] = record

        for w in range(self.n_windows):
            offset = w * (self.W // self.n_windows)
            win_idx = (seq - offset) // self.W
            if win_idx >= 0:
                win_key = (w, win_idx)
                if win_key not in self.win_states:
                    self.win_states[win_key] = {'records': [], 'inv': 0}
                win = self.win_states[win_key]
                win['records'].append(seq)
                win['inv'] += record['value']

    def recover_burst(self, lost_seqs: List[int]) -> List[dict]:
        recovered = []
        lost_set = set(lost_seqs)

        for seq in lost_seqs:
            for w in range(self.n_windows):
                offset = w * (self.W // self.n_windows)
                win_idx = (seq - offset) // self.W
                if win_idx < 0: continue

                win_key = (w, win_idx)
                if win_key not in self.win_states: continue

                win = self.win_states[win_key]
                # Check if only this seq is lost in this window
                other_seqs_in_win = [s for s in win['records'] if s != seq]
                lost_others_in_win = [s for s in other_seqs_in_win if s in lost_set]

                if not lost_others_in_win:
                    # Only one record lost from this window — O(1) residual recovery
                    # current_sum = sum(record_store[s])
                    vals = np.array([self.record_store[s]['value'] for s in other_seqs_in_win], dtype=np.int64)
                    sum_known = np.sum(vals)
                    rec_value = int(win['inv'] - sum_known)
                    recovered.append({'seq': seq, 'value': rec_value, 'window': w, 'recovered': True})
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

    stream = list(sensor_stream(50))
    for r in stream: fsc_stream.ingest(r)

    dropped = [12, 27, 43]
    for lost_seq in dropped:
        snap = fsc_stream.get_window_invariant(lost_seq)
        if snap:
            window_recs = [r for r in stream if snap['window_start'] <= r['seq'] <= snap['window_end'] and r['seq'] != lost_seq]
            recovered = fsc_stream.recover(window_recs, lost_seq, snap)
            original  = stream[lost_seq]
            exact = all(recovered.get(f) == original.get(f) for f in fields_to_protect)
            print(f"  Record {lost_seq}: value={original['value']} → recovered={recovered.get('value')} ✓={exact}")

    # ── PART 2: Burst loss recovery ───────────────────────────────
    print("\n━━ 2. Burst Loss Recovery ━━")
    burst_fsc = BurstFSC(window_size=8, n_windows=2)
    stream2 = list(sensor_stream(100, seed=7))
    for r in stream2: burst_fsc.process(r)
    burst = [20, 21, 22]
    recovered_burst = burst_fsc.recover_burst(burst)
    for rb in recovered_burst:
        original = stream2[rb['seq']]
        print(f"  Record {rb['seq']}: {original['value']} → {rb['value']} ✓={rb['value'] == original['value']}")

    # ── PART 3: Throughput ──
    N = 50_000
    big_stream = SlidingWindowFSC(window_size=10, fields=['value'])
    data = [{'seq': i, 'value': i % 251} for i in range(N)]
    t0 = time.perf_counter()
    for r in data: big_stream.ingest(r)
    t1 = time.perf_counter()
    print(f"\n━━ 3. Throughput: {N/(t1-t0):,.0f} records/s")

if __name__ == '__main__':
    run()
