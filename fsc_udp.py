import socket
import struct
import time
import random
import threading
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

        # Calculate XOR parity
        # Assume all payloads are same length for simplicity
        max_len = max(len(p) for p in payloads)
        parity = bytearray(max_len)

        for i, payload in enumerate(payloads):
            # Send Data Packet
            header = struct.pack(HEADER_FORMAT, MAGIC, self.seq, self.group_id, 0)
            self.sock.sendto(header + payload, self.target)

            # XOR into parity
            for b in range(len(payload)):
                parity[b] ^= payload[b]

            self.seq += 1

        # Send FSC Parity Packet
        header = struct.pack(HEADER_FORMAT, MAGIC, self.seq, self.group_id, 1)
        self.sock.sendto(header + bytes(parity), self.target)
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
        """Receive packets and heal losses."""
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

                # Attempt healing
                self._try_heal(group_id)
        except socket.timeout:
            pass

    def _try_heal(self, group_id: int):
        g = self.groups[group_id]
        # A group is "Data Size + 1 Parity"
        # If we have (Data Size) packets total, and parity is present, exactly 1 data is missing.
        # Or if we have (Data Size) packets total, and parity is missing, nothing to heal.

        data_count = len(g["data"])
        if g["parity"] is not None and data_count == self.group_size - 1:
            # Exactly one data packet lost!
            # Find missing seq
            # In our simple demo, seqs in group are [group_id*(N+1) ... (group_id+1)*(N+1)-1]
            base_seq = group_id * (self.group_size + 1)
            expected_seqs = range(base_seq, base_seq + self.group_size)
            missing_seq = next(s for s in expected_seqs if s not in g["data"])

            # Heal via XOR
            recovered = bytearray(g["parity"])
            for payload in g["data"].values():
                for b in range(len(payload)):
                    recovered[b] ^= payload[b]

            g["data"][missing_seq] = bytes(recovered)
            self.recovered_count += 1
            print(f"  [FSC-UDP] Healed lost packet seq={missing_seq} in group={group_id}")

# ── SIMULATION ─────────────────────────────────────────────────────

def run_simulation():
    PORT = 9999
    GROUP_SIZE = 5
    N_GROUPS = 10

    receiver = FSCUDPReceiver(PORT, GROUP_SIZE)
    sender = FSCUDPSender("127.0.0.1", PORT, GROUP_SIZE)

    # Run receiver in background
    # We expect N_GROUPS * (GROUP_SIZE + 1) packets total
    expected_total = N_GROUPS * (GROUP_SIZE + 1)
    rx_thread = threading.Thread(target=receiver.listen, args=(expected_total,))
    rx_thread.start()

    time.sleep(0.1)

    # Simulate sender with probabilistic loss
    # We'll manually drop some packets to guarantee recovery works
    loss_indices = [3, 15, 27, 33, 50] # Random-ish

    print(f"Sending {N_GROUPS} groups (window={GROUP_SIZE}) with simulated loss...")

    all_payloads = []
    for g in range(N_GROUPS):
        group_payloads = [f"Data packet {g}:{i}".encode().ljust(32, b".") for i in range(GROUP_SIZE)]
        all_payloads.extend(group_payloads)

        # We manually handle the "send with loss" logic here instead of sender.send_group
        parity = bytearray(32)
        for i, payload in enumerate(group_payloads):
            seq = g * (GROUP_SIZE + 1) + i
            for b in range(len(payload)): parity[b] ^= payload[b]

            if seq not in loss_indices:
                header = struct.pack(HEADER_FORMAT, MAGIC, seq, g, 0)
                sender.sock.sendto(header + payload, sender.target)
            else:
                print(f"  [SIM] Dropping packet seq={seq}")

        # Parity packet
        p_seq = g * (GROUP_SIZE + 1) + GROUP_SIZE
        if p_seq not in loss_indices:
            header = struct.pack(HEADER_FORMAT, MAGIC, p_seq, g, 1)
            sender.sock.sendto(header + bytes(parity), sender.target)
        else:
             print(f"  [SIM] Dropping parity seq={p_seq}")

    rx_thread.join()

    print("\nSimulation Results:")
    print(f"  Total packets sent (incl. parity): {expected_total}")
    print(f"  Total packets received:            {receiver.total_received}")
    print(f"  Total packets recovered:           {receiver.recovered_count}")

    # Verify exact recovery
    success = True
    for g_id, g in receiver.groups.items():
        for i in range(GROUP_SIZE):
            seq = g_id * (GROUP_SIZE + 1) + i
            original = f"Data packet {g_id}:{i}".encode().ljust(32, b".")
            if seq not in g["data"] or g["data"][seq] != original:
                print(f"  ✗ Recovery failed for seq={seq}")
                success = False

    if success:
        print("  ✓ ALL lost packets recovered exactly.")

if __name__ == "__main__":
    run_simulation()
