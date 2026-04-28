"""
FSC: Forward Sector Correction
Copyright (C) 2024 FSC Core Team. All Rights Reserved.
"""

import os
import mmap
import numpy as np
from typing import List, Optional, Dict
from collections import OrderedDict
from fsc.fsc_block import FSCBlock, FSCVolume

class PersistentFSCVolume:
    """
    A file-backed FSC volume using memory mapping (mmap) for zero-copy
    NVMe-optimized persistence and hierarchical self-healing.
    """
    def __init__(self, filename: str, n_blocks: int, block_size: int = 512):
        self.filename = filename
        self.n_blocks = n_blocks
        self.block_size = block_size
        self.total_size = n_blocks * block_size
        self._init_file()

        # Mmap the file directly into a NumPy buffer for zero-copy access
        self.f = open(self.filename, "r+b")
        self.mm = mmap.mmap(self.f.fileno(), self.total_size)

        # Create a NumPy view of the mapped memory
        self.data_buffer = np.frombuffer(self.mm, dtype=np.uint8)
        self.volume = FSCVolume(n_blocks, block_size, buffer=self.data_buffer)

    def _init_file(self):
        if not os.path.exists(self.filename):
            with open(self.filename, "wb") as f:
                f.write(b"\0" * self.total_size)
        elif os.path.getsize(self.filename) < self.total_size:
            with open(self.filename, "a+b") as f:
                f.write(b"\0" * (self.total_size - os.path.getsize(self.filename)))

    def write(self, data: bytes):
        """Write data to the memory-mapped volume and update parity."""
        self.volume.write_volume(data)
        self.mm.flush()

    def heal_and_sync(self) -> int:
        """Heal corruptions in the volume directly in the mapped buffer."""
        count = self.volume.heal_volume()
        if count > 0:
            self.mm.flush()
        return count

    def read(self) -> bytes:
        """Read data directly from the mapped volume."""
        return self.volume.read_volume()

    def corrupt_disk(self, block_idx: int, byte_offset: int, val: int):
        """Simulate direct disk corruption by writing to the mapped buffer."""
        self.data_buffer[block_idx * self.block_size + byte_offset] = val
        self.mm.flush()

    def close(self):
        self.mm.close()
        self.f.close()

    def __del__(self):
        try:
            self.close()
        except:
            pass
