"""
FSC: Forward Sector Correction
Copyright (C) 2024 FSC Core Team. All Rights Reserved.

PUBLIC LICENSE: GNU Affero General Public License (AGPLv3)
COMMERCIAL LICENSE: Required for proprietary/enterprise use.

PATENT PENDING: Industrial applications of these algebraic primitives
for database pages, kernel block devices, and network protocols.
"""

import os
import numpy as np
from typing import List, Optional, Dict
from collections import OrderedDict
from fsc.fsc_block import FSCBlock, FSCVolume

class PersistentFSCVolume:
    """
    A file-backed FSC volume with hierarchical self-healing and LRU cache.
    Provides persistence for simulated block-level integrity with lazy loading.
    """
    def __init__(self, filename: str, n_blocks: int, block_size: int = 512, cache_size: int = 100):
        self.filename = filename
        self.n_blocks = n_blocks
        self.block_size = block_size
        self.total_size = n_blocks * block_size
        self.cache_size = cache_size
        self.cache: Dict[int, FSCBlock] = OrderedDict()
        self._init_file()
        # Internal volume tracks all block metadata but data is lazy-loaded
        self.volume = FSCVolume(n_blocks, block_size)

    def _init_file(self):
        if not os.path.exists(self.filename):
            with open(self.filename, "wb") as f:
                f.write(b"\0" * self.total_size)

    def _get_block(self, block_idx: int) -> FSCBlock:
        """Get a block, loading it into LRU cache if necessary."""
        if block_idx in self.cache:
            # Move to end (most recent)
            block = self.cache.pop(block_idx)
            self.cache[block_idx] = block
            return block

        # Load from disk
        block = self.volume.blocks[block_idx]
        with open(self.filename, "rb") as f:
            f.seek(block_idx * self.block_size)
            block.data = np.frombuffer(f.read(self.block_size), dtype=np.uint8).copy()

        # Add to cache
        self.cache[block_idx] = block
        if len(self.cache) > self.cache_size:
            # Evict oldest (syncing if needed - here we just discard as we sync on write)
            self.cache.popitem(last=False)

        return block

    def sync_block(self, block_idx: int):
        """Sync a specific block to disk."""
        if block_idx in self.cache:
            block = self.cache[block_idx]
            with open(self.filename, "r+b") as f:
                f.seek(block_idx * self.block_size)
                f.write(block.data.tobytes())

    def write(self, data: bytes):
        """Write data to volume, update parity, and sync all affected blocks."""
        # To compute volume parity, we currently need all blocks.
        # For 'production' we'd use incremental parity, but here we load all.
        for i in range(self.n_blocks):
            self._get_block(i)

        self.volume.write_volume(data)

        # Sync all blocks (could be optimized to only sync changed ones)
        with open(self.filename, "r+b") as f:
            for i in range(self.n_blocks):
                f.seek(i * self.block_size)
                f.write(self.volume.blocks[i].data.tobytes())

    def heal_and_sync(self) -> int:
        """Heal corruptions in the volume and sync fixed data to disk."""
        # Load all blocks for full volume healing
        for i in range(self.n_blocks):
            self._get_block(i)

        count = self.volume.heal_volume()
        if count > 0:
            with open(self.filename, "r+b") as f:
                for i in range(self.n_blocks):
                    f.seek(i * self.block_size)
                    f.write(self.volume.blocks[i].data.tobytes())
        return count

    def read(self) -> bytes:
        for i in range(self.n_blocks):
            self._get_block(i)
        return self.volume.read_volume()

    def corrupt_disk(self, block_idx: int, byte_offset: int, val: int):
        """Simulate direct disk corruption."""
        with open(self.filename, "r+b") as f:
            f.seek(block_idx * self.block_size + byte_offset)
            f.write(bytes([val]))
        # Evict from cache to force reload on next access
        if block_idx in self.cache:
            del self.cache[block_idx]
