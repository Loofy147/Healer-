"""
FSC: Forward Sector Correction
Copyright (C) 2024 FSC Core Team. All Rights Reserved.

PUBLIC LICENSE: GNU Affero General Public License (AGPLv3)
COMMERCIAL LICENSE: Required for proprietary/enterprise use.

PATENT PENDING: Industrial applications of these algebraic primitives
for database pages, kernel block devices, and network protocols.
"""

import socket
import struct
import time
import random
import threading
import numpy as np
from typing import List, Dict

# ── FSC UDP PROTOCOL SPEC ──────────────────────────────────────────
# Header: [Magic:4b][Seq:4b][Group:4b][Type:1b]
# Types: 0 = Data, 1 = FSC Parity
HEADER_FORMAT = "!4sIIB"
MAGIC = b"FSCU"

class FSCUDPSender:
    def __init__(self, target_ip: str, target_port: int, group_size: int = 5):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.target = (target_ip, target_port)
        self.group_size = group_size
        self.seq = 0
        self.group_id = 0

    def send_group(self, payloads: List[bytes]):
        """Send a group of packets + 1 FSC parity packet."""
        assert len(payloads) == self.group_size

        # Use numpy for vectorized XOR parity
        max_len = max(len(p) for p in payloads)
        payloads_np = np.zeros((self.group_size, max_len), dtype=np.uint8)
        for i, p in enumerate(payloads):
            payloads_np[i, :len(p)] = np.frombuffer(p, dtype=np.uint8)

        parity_np = np.bitwise_xor.reduce(payloads_np, axis=0)
        parity = parity_np.tobytes()

        for i, payload in enumerate(payloads):
            header = struct.pack(HEADER_FORMAT, MAGIC, self.seq, self.group_id, 0)
            self.sock.sendto(header + payload, self.target)
            self.seq += 1

        header = struct.pack(HEADER_FORMAT, MAGIC, self.seq, self.group_id, 1)
        self.sock.sendto(header + parity, self.target)
        self.seq += 1
        self.group_id += 1

class FSCUDPReceiver:
    def __init__(self, port: int, group_size: int = 5):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", port))
        self.group_size = group_size
        self.groups: Dict[int, Dict] = {}
        self.recovered_count = 0
        self.total_received = 0

    def listen(self, count: int):
        self.sock.settimeout(2.0)
        received_indices = []

        try:
            while len(received_indices) < count:
                data, addr = self.sock.recvfrom(2048)
                header = data[:struct.calcsize(HEADER_FORMAT)]
                payload = data[struct.calcsize(HEADER_FORMAT):]

                magic, seq, group_id, ptype = struct.unpack(HEADER_FORMAT, header)
                if magic != MAGIC: continue

                if group_id not in self.groups:
                    self.groups[group_id] = {"data": {}, "parity": None, "count": 0}

                g = self.groups[group_id]
                if ptype == 0:
                    g["data"][seq] = payload
                else:
                    g["parity"] = payload

                g["count"] += 1
                self.total_received += 1
                received_indices.append(seq)

                self._try_heal(group_id)
        except socket.timeout: pass

    def _try_heal(self, group_id: int):
        g = self.groups[group_id]
        data_count = len(g["data"])
        if g["parity"] is not None and data_count == self.group_size - 1:
            base_seq = group_id * (self.group_size + 1)
            expected_seqs = range(base_seq, base_seq + self.group_size)
            missing_seq = next(s for s in expected_seqs if s not in g["data"])

            # Use numpy for vectorized XOR recovery
            parity_np = np.frombuffer(g["parity"], dtype=np.uint8)
            data_list = list(g["data"].values())
            data_matrix = np.zeros((len(data_list), len(parity_np)), dtype=np.uint8)
            for i, p in enumerate(data_list):
                data_matrix[i, :len(p)] = np.frombuffer(p, dtype=np.uint8)

            recovered_np = np.bitwise_xor(parity_np, np.bitwise_xor.reduce(data_matrix, axis=0))
            g["data"][missing_seq] = recovered_np.tobytes()
            self.recovered_count += 1
            print(f"  [FSC-UDP] Healed lost packet seq={missing_seq} in group={group_id}")

def run_simulation():
    PORT = 9999
    GROUP_SIZE = 5
    N_GROUPS = 10
    receiver = FSCUDPReceiver(PORT, GROUP_SIZE)
    sender = FSCUDPSender("127.0.0.1", PORT, GROUP_SIZE)
    rx_thread = threading.Thread(target=receiver.listen, args=(N_GROUPS * (GROUP_SIZE + 1),))
    rx_thread.start()
    time.sleep(0.1)
    loss_indices = [3, 15, 27, 33, 50]
    print(f"Sending {N_GROUPS} groups with simulated loss...")
    for g in range(N_GROUPS):
        group_payloads = [f"Data packet {g}:{i}".encode().ljust(32, b".") for i in range(GROUP_SIZE)]
        parity_matrix = np.zeros((GROUP_SIZE, 32), dtype=np.uint8)
        for i, p in enumerate(group_payloads): parity_matrix[i] = np.frombuffer(p, dtype=np.uint8)
        parity = np.bitwise_xor.reduce(parity_matrix, axis=0).tobytes()
        for i, payload in enumerate(group_payloads):
            seq = g * (GROUP_SIZE + 1) + i
            if seq not in loss_indices:
                header = struct.pack(HEADER_FORMAT, MAGIC, seq, g, 0)
                sender.sock.sendto(header + payload, sender.target)
        p_seq = g * (GROUP_SIZE + 1) + GROUP_SIZE
        if p_seq not in loss_indices:
            header = struct.pack(HEADER_FORMAT, MAGIC, p_seq, g, 1)
            sender.sock.sendto(header + parity, sender.target)
    rx_thread.join()
    success = True
    for g_id, g in receiver.groups.items():
        for i in range(GROUP_SIZE):
            seq = g_id * (GROUP_SIZE + 1) + i
            original = f"Data packet {g_id}:{i}".encode().ljust(32, b".")
            if seq not in g["data"] or g["data"][seq] != original: success = False
    if success: print("  ✓ ALL lost packets recovered exactly.")

if __name__ == "__main__":
    run_simulation()
