"""
FSC: Forward Sector Correction
Copyright (C) 2024 FSC Core Team. All Rights Reserved.

PUBLIC LICENSE: GNU Affero General Public License (AGPLv3)
COMMERCIAL LICENSE: Required for proprietary/enterprise use.

PATENT PENDING: Industrial applications of these algebraic primitives
for database pages, kernel block devices, and network protocols.
"""

import hashlib
import struct
import numpy as np
from typing import List, Optional, Any

def field_hash(value: Any, p: int = 2**31 - 1) -> int:
    """Project any value to Z_p via SHA256."""
    b = str(value).encode() if not isinstance(value, bytes) else value
    h = hashlib.sha256(b).digest()
    return int.from_bytes(h[:8], 'big') % p

def str_to_int(s: str, max_len: int = 8) -> int:
    b = s.encode('utf-8')[:max_len]
    b = b.ljust(max_len, b'\x00')
    return int.from_bytes(b, 'big')

def int_to_str(n: int, max_len: int = 8) -> str:
    b = n.to_bytes(max_len, 'big')
    return b.rstrip(b'\x00').decode('utf-8', errors='replace')

class SegmentFSC:
    def __init__(self, segment_size: int = 8):
        self.seg_size = segment_size

    def _to_segments(self, data: bytes) -> np.ndarray:
        padded = data + b'\x00' * (-len(data) % self.seg_size)
        return np.frombuffer(padded, dtype='>u8').astype(np.int64)

    def encode(self, data: bytes) -> dict:
        segments_np = self._to_segments(data)
        invariant = np.sum(segments_np)
        return {
            'segments': segments_np,
            'invariant': int(invariant),
            'original_len': len(data)
        }

    def recover(self, corrupted: dict, seg_idx: int) -> dict:
        segs = corrupted['segments'].copy()
        current_sum = np.sum(segs)
        # others = current_sum - corrupted_val
        others = current_sum - segs[seg_idx]
        segs[seg_idx] = corrupted['invariant'] - others
        return {**corrupted, 'segments': segs}

    def decode(self, encoded: dict) -> bytes:
        return encoded['segments'].astype('>u8').tobytes()[:encoded['original_len']]

class MixedRecord:
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
        self.schema = schema

    def encode(self, record: dict) -> np.ndarray:
        encoded = []
        for name, ftype in self.schema:
            val = record[name]
            enc = self.ENCODERS[ftype](val)
            encoded.append(enc & ((1 << 64) - 1))
        # Use numpy for invariant
        arr = np.array(encoded, dtype=np.int64)
        return np.append(arr, np.sum(arr))

    def decode(self, encoded: np.ndarray) -> dict:
        result = {}
        for i, (name, ftype) in enumerate(self.schema):
            result[name] = self.DECODERS[ftype](int(encoded[i]))
        return result

    def recover_field(self, encoded: np.ndarray, field_idx: int) -> np.ndarray:
        invariant = encoded[-1]
        current_sum = np.sum(encoded[:-1])
        others = current_sum - encoded[field_idx]
        recovered = invariant - others
        result = encoded.copy()
        result[field_idx] = recovered
        return result

    def is_valid(self, encoded: np.ndarray) -> bool:
        return int(np.sum(encoded[:-1])) == int(encoded[-1])

def run():
    print("=" * 64)
    print("  FSC FOR NON-NUMERIC DATA (OPTIMIZED)")
    print("=" * 64)

    seg_fsc = SegmentFSC(8)
    data = b"The quick brown fox jumps over the lazy dog."
    enc = seg_fsc.encode(data)
    corrupted = {**enc, 'segments': enc['segments'].copy()}
    corrupted['segments'][2] = 0
    healed = seg_fsc.recover(corrupted, 2)
    print(f"Text recovery: {seg_fsc.decode(healed) == data}")

    schema = [('ts', int), ('user', str)]
    mr = MixedRecord(schema)
    rec = {'ts': 12345, 'user': 'bolt'}
    encoded = mr.encode(rec)
    corrupted_rec = encoded.copy()
    corrupted_rec[1] = 0
    healed_rec = mr.recover_field(corrupted_rec, 1)
    print(f"Mixed recovery: {mr.decode(healed_rec) == rec}")

if __name__ == '__main__':
    run()
