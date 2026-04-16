"""
FSC for Non-Numeric Data
=========================
Extending FSC to strings, blobs, mixed types.

Strategy: project any data type to the integer ring
via a structure-preserving hash, then apply FSC.

Two approaches:
1. Hash projection: h(x) → Z_p. Fast, one-directional.
   Use for DETECTION only (can verify integrity, not recover content).

2. Integer encoding: encode strings/blobs as integers (UTF-8 → bytes → int).
   Exact bidirectional. Use for RECOVERY of short strings.

3. Segment FSC: split blob into integer segments, apply FSC per segment.
   Recovers any corrupted segment exactly.
"""

import hashlib
import struct
import numpy as np


# ── HASH PROJECTION (integrity detection) ────────────────────────

def field_hash(value, p: int = 2**31 - 1) -> int:
    """Project any value to Z_p via SHA256."""
    b = str(value).encode() if not isinstance(value, bytes) else value
    h = hashlib.sha256(b).digest()
    return int.from_bytes(h[:8], 'big') % p


# ── INTEGER ENCODING (exact recovery for short strings) ──────────

def str_to_int(s: str, max_len: int = 8) -> int:
    """Encode string as integer (up to max_len bytes = 8 chars)."""
    b = s.encode('utf-8')[:max_len]
    b = b.ljust(max_len, b'\x00')
    return int.from_bytes(b, 'big')

def int_to_str(n: int, max_len: int = 8) -> str:
    """Decode integer to string."""
    b = n.to_bytes(max_len, 'big')
    return b.rstrip(b'\x00').decode('utf-8', errors='replace')


# ── SEGMENT FSC (blobs and long strings) ─────────────────────────

class SegmentFSC:
    """
    Apply FSC to a blob by splitting into integer segments.

    A blob of B bytes → B/8 segments of int64 each.
    FSC invariant = integer sum of all segments.
    Any 1 corrupted segment → recovered exactly.

    Works for: text, binary files, serialized objects,
               compressed data, audio frames, video packets.
    """

    def __init__(self, segment_size: int = 8):
        self.seg_size = segment_size

    def _to_segments(self, data: bytes) -> list:
        """Convert bytes to list of integers."""
        padded = data + b'\x00' * (-len(data) % self.seg_size)
        segs = []
        for i in range(0, len(padded), self.seg_size):
            segs.append(int.from_bytes(padded[i:i+self.seg_size], 'big'))
        return segs

    def _from_segments(self, segs: list, original_len: int) -> bytes:
        """Convert integers back to bytes."""
        result = b''
        for s in segs:
            result += s.to_bytes(self.seg_size, 'big')
        return result[:original_len]

    def encode(self, data: bytes) -> dict:
        """Encode data with FSC invariant."""
        segments  = self._to_segments(data)
        invariant = sum(segments)
        return {
            'segments':    segments,
            'invariant':   invariant,
            'original_len': len(data)
        }

    def corrupt(self, encoded: dict, seg_idx: int, bad_value: int = 0) -> dict:
        """Simulate corruption of segment seg_idx."""
        segs = list(encoded['segments'])
        segs[seg_idx] = bad_value
        return {**encoded, 'segments': segs, 'corrupted_idx': seg_idx}

    def recover(self, corrupted: dict, seg_idx: int) -> dict:
        """Recover segment seg_idx from invariant."""
        segs = list(corrupted['segments'])
        sum_others = sum(segs[j] for j in range(len(segs)) if j != seg_idx)
        segs[seg_idx] = corrupted['invariant'] - sum_others
        return {**corrupted, 'segments': segs}

    def decode(self, encoded: dict) -> bytes:
        return self._from_segments(encoded['segments'], encoded['original_len'])


# ── MIXED-TYPE RECORD FSC ─────────────────────────────────────────

class MixedRecord:
    """
    A record with mixed types (int, str, float, bytes).
    Each field is encoded as int64 via type-appropriate method.
    FSC invariant = sum of all encoded values.
    """

    ENCODERS = {
        int:   lambda v: v,
        float: lambda v: struct.unpack('>q', struct.pack('>d', v))[0],
        str:   lambda v: str_to_int(v, 8),
        bytes: lambda v: int.from_bytes(v[:8].ljust(8, b'\x00'), 'big'),
    }

    DECODERS = {
        int:   lambda v: v,
        float: lambda v: struct.unpack('>d', struct.pack('>q', v))[0],
        str:   lambda v: int_to_str(v, 8),
        bytes: lambda v: v.to_bytes(8, 'big'),
    }

    def __init__(self, schema: list):
        """schema: list of (name, type) tuples."""
        self.schema = schema

    def encode(self, record: dict) -> list:
        """Encode record fields to integers + invariant."""
        encoded = []
        for name, ftype in self.schema:
            val = record[name]
            enc = self.ENCODERS[ftype](val)
            encoded.append(enc & ((1 << 64) - 1))  # truncate to 64-bit
        invariant = sum(encoded)
        return encoded + [invariant]

    def decode(self, encoded: list) -> dict:
        """Decode integers back to original types."""
        result = {}
        for i, (name, ftype) in enumerate(self.schema):
            result[name] = self.DECODERS[ftype](encoded[i])
        return result

    def recover_field(self, encoded: list, field_idx: int) -> list:
        """Recover corrupted field using FSC invariant."""
        invariant = encoded[-1]
        sum_others = sum(encoded[j] for j in range(len(encoded)-1) if j != field_idx)
        recovered = invariant - sum_others
        result = list(encoded)
        result[field_idx] = recovered & ((1 << 64) - 1)
        return result

    def is_valid(self, encoded: list) -> bool:
        return sum(encoded[:-1]) == encoded[-1]


# ── DEMO ─────────────────────────────────────────────────────────

def run():
    print("=" * 64)
    print("  FSC FOR NON-NUMERIC DATA")
    print("=" * 64)

    # ── 1. Text segments ─────────────────────────────────────────
    print("\n━━ 1. Text / String Segment Healing ━━")

    seg_fsc = SegmentFSC(segment_size=8)

    texts = [
        "The quick brown fox jumps over the lazy dog.",
        "Fiber-Stratified Closure heals corrupted data.",
        "Every record carries its own algebraic invariant.",
        "One subtraction recovers the lost information.",
    ]

    for text in texts[:2]:
        data   = text.encode()
        enc    = seg_fsc.encode(data)
        n_segs = len(enc['segments'])

        # Corrupt middle segment
        corrupt_idx = n_segs // 2
        corrupted   = seg_fsc.corrupt(enc, corrupt_idx)
        healed      = seg_fsc.recover(corrupted, corrupt_idx)
        recovered   = seg_fsc.decode(healed)

        ok = recovered == data
        print(f"  '{text[:40]}...' [{n_segs} segs]  ✓={ok}")

    # Stress test
    import random
    random.seed(42)
    success = 0
    for _ in range(500):
        n = random.randint(8, 256)
        data = bytes(random.randint(0, 255) for _ in range(n))
        enc  = seg_fsc.encode(data)
        ci   = random.randint(0, len(enc['segments'])-1)
        corrupted = seg_fsc.corrupt(enc, ci)
        healed    = seg_fsc.recover(corrupted, ci)
        if seg_fsc.decode(healed) == data:
            success += 1
    print(f"\n  Stress test: {success}/500 exact on random binary blobs")

    # ── 2. JSON-like records ─────────────────────────────────────
    print("\n━━ 2. Mixed-Type Record Healing ━━")

    schema = [
        ('timestamp', int),
        ('username',  str),
        ('action',    str),
        ('score',     int),
        ('ratio',     float),
    ]
    mr = MixedRecord(schema)

    records = [
        {'timestamp': 1700000100, 'username': 'alice',   'action': 'login',  'score': 9500,  'ratio': 0.95},
        {'timestamp': 1700000200, 'username': 'bob',     'action': 'upload', 'score': 7800,  'ratio': 0.88},
        {'timestamp': 1700000300, 'username': 'carol',   'action': 'search', 'score': 8200,  'ratio': 0.91},
    ]

    for rec in records:
        encoded   = mr.encode(rec)
        assert mr.is_valid(encoded)

        # Corrupt username field (index 1)
        corrupted = list(encoded)
        corrupted[1] = 0

        healed = mr.recover_field(corrupted, 1)
        decoded = mr.decode(healed)

        ok_str = decoded['username'] == rec['username']
        ok_num = decoded['score'] == rec['score']
        print(f"  user='{rec['username']}': corrupted → recovered '{decoded['username']}'  ✓str={ok_str}  ✓num={ok_num}")

    # ── 3. Binary file segments ───────────────────────────────────
    print("\n━━ 3. Binary File Self-healing ━━")

    import os
    # Simulate a small binary file (e.g., compressed data header)
    file_data = bytes(range(256)) * 4  # 1KB synthetic file

    enc = seg_fsc.encode(file_data)
    n_segs = len(enc['segments'])
    print(f"  File: {len(file_data)} bytes → {n_segs} segments of 8 bytes each")
    print(f"  Invariant: 1 int64 = 8 bytes overhead = {100*8/len(file_data):.1f}%")

    # Corrupt 1 sector (1 segment = 8 bytes)
    corrupt_idx = 16
    corrupted = seg_fsc.corrupt(enc, corrupt_idx)
    healed    = seg_fsc.recover(corrupted, corrupt_idx)
    recovered = seg_fsc.decode(healed)

    ok = recovered == file_data
    print(f"  Segment {corrupt_idx} corrupted (bytes {corrupt_idx*8}–{corrupt_idx*8+7}) → recovered  ✓={ok}")

    # ── 4. Hash-based integrity (detection only) ─────────────────
    print("\n━━ 4. Hash Projection — Any Data Type Detection ━━")

    def hash_record(fields: list, p: int = 2**31 - 1) -> int:
        """Project any record to Z_p via field hashes."""
        return sum(field_hash(f, p) for f in fields) % p

    mixed_records = [
        [1700000000, "user@example.com", [1,2,3], b'\xde\xad\xbe\xef', True],
        [42, None, {"key":"value"}, 3.14159, "hello"],
        [0, [], {}, b'', ""],
    ]

    p = 2**31 - 1
    for rec in mixed_records:
        original_hash = hash_record(rec, p)
        # Corrupt one field
        corrupted_rec = list(rec)
        corrupted_rec[2] = "TAMPERED"
        corrupted_hash = hash_record(corrupted_rec, p)
        detected = (original_hash != corrupted_hash)
        print(f"  Record {str(rec)[:45]:45s} → tamper detected: {detected}")

    print(f"""
  NON-NUMERIC FSC SUMMARY:

  Strings (short):   encode as int64, recover exactly  ≤ 8 chars
  Strings (long):    segment into int64 chunks, recover any segment
  Binary blobs:      8-byte segments, int64 invariant, exact recovery
  Mixed records:     type-encode each field, integer FSC on encodings
  Any type (detect): hash projection to Z_p, integrity detection only

  The key insight: FSC operates on the INTEGER RING.
  Any data type that can be bijectively mapped to integers
  admits exact FSC recovery. Larger types need segmentation.
  Non-invertible types (hashes, compressed data) support detection only.
""")

if __name__ == '__main__':
    run()
