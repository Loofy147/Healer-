"""
FSC: Forward Sector Correction - Accelerated UDP (Horizon 3)
Copyright (C) 2024 FSC Core Team. All Rights Reserved.
"""

import socket
import struct
import threading
import numpy as np
from typing import List, Dict
from fsc.core.fsc_native import is_native_available, native_xor_reduce

HEADER_FORMAT = "!4sIIB"
MAGIC = b"FSCU"

class FSCUDPSender:
    def __init__(self, target_ip: str, target_port: int, group_size: int = 5):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.target = (target_ip, target_port)
        self.group_size = group_size
        self.seq = 0; self.group_id = 0

    def send_group(self, payloads: List[bytes]):
        max_len = max(len(p) for p in payloads)
        payloads_np = np.zeros((self.group_size, max_len), dtype=np.uint8)
        for i, p in enumerate(payloads): payloads_np[i, :len(p)] = np.frombuffer(p, dtype=np.uint8)

        if is_native_available():
            # Flat view for native reduce
            parity_np = native_xor_reduce(payloads_np.flatten(), max_len)
        else:
            parity_np = np.bitwise_xor.reduce(payloads_np, axis=0)

        parity = parity_np.tobytes()
        for payload in payloads:
            self.sock.sendto(struct.pack(HEADER_FORMAT, MAGIC, self.seq, self.group_id, 0) + payload, self.target)
            self.seq += 1
        self.sock.sendto(struct.pack(HEADER_FORMAT, MAGIC, self.seq, self.group_id, 1) + parity, self.target)
        self.seq += 1; self.group_id += 1

class FSCUDPReceiver:
    def __init__(self, port: int, group_size: int = 5):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); self.sock.bind(("0.0.0.0", port))
        self.group_size = group_size; self.groups: Dict[int, Dict] = {}; self.recovered_count = 0

    def _try_heal(self, group_id: int):
        g = self.groups[group_id]
        if g["parity"] is not None and len(g["data"]) == self.group_size - 1:
            parity_np = np.frombuffer(g["parity"], dtype=np.uint8)
            data_list = list(g["data"].values())
            data_matrix = np.zeros((len(data_list), len(parity_np)), dtype=np.uint8)
            for i, p in enumerate(data_list): data_matrix[i, :len(p)] = np.frombuffer(p, dtype=np.uint8)

            if is_native_available():
                # X ^ Y ^ Z ... parity = missing
                # Combine parity and available data for final XOR reduce
                combined = np.vstack([data_matrix, parity_np])
                recovered_np = native_xor_reduce(combined.flatten(), len(parity_np))
            else:
                recovered_np = np.bitwise_xor(parity_np, np.bitwise_xor.reduce(data_matrix, axis=0))

            self.recovered_count += 1; return recovered_np.tobytes()
        return None
