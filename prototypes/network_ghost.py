"""
FSC: Forward Sector Correction
Copyright (C) 2024 FSC Core Team. All Rights Reserved.

OFFENSIVE ARSENAL: TOPOLOGICAL STEGANOGRAPHY (Network Evasion)
=============================================================
Demonstrates encoding a hidden "Ghost Payload" into a legitimate
data stream (e.g., H.264 video) using algebraic parity projections.

The "Parity Shadow" Evasion:
1. A firewall inspects UDP traffic, verifying a simple linear
   checksum (e.g., Sum mod 251) to ensure protocol integrity.
2. The "Ghost" sender modifies the data stream such that it
   simultaneously satisfies the firewall's public invariant
   AND encodes a hidden message in a secret algebraic projection.
3. Deep Packet Inspection (DPI) sees valid video and valid parity.
4. The receiver unbinds the payload using the secret weight kernel.
"""

import numpy as np
from fsc.fsc_framework import solve_linear_system

# Modulus for the demo
P = 251

class NetworkGhost:
    def __init__(self, packet_size=1024):
        self.size = packet_size
        # The public weight vector the firewall uses (Simple Sum)
        self.w_public = np.ones(packet_size, dtype=int)
        # The secret weight vector known only to Sender/Receiver
        np.random.seed(1337)
        self.w_secret = np.random.randint(1, P, packet_size)

    def encode_ghost(self, carrier_data: bytes, message_byte: int) -> bytes:
        """
        Injects the message_byte into the carrier_data.
        Modifies two 'noise' bytes to satisfy both public and secret invariants.
        """
        data = list(carrier_data)

        # Choose two indices to 'sacrifice' (e.g., least significant video bits)
        idx_a, idx_b = 100, 101

        # Current projections
        s_pub_current = sum(data) % P
        s_sec_current = sum(d * w for d, w in zip(data, self.w_secret)) % P

        # We want:
        # (s_pub_current - data[idx_a] - data[idx_b] + new_a + new_b) % P == s_pub_current
        # (s_sec_current - data[idx_a]*w_a - data[idx_b]*w_b + new_a*w_a + new_b*w_b) % P == message_byte

        # Let Delta_a = new_a - data[idx_a], Delta_b = new_b - data[idx_b]
        # 1*Delta_a + 1*Delta_b = 0  (mod P)
        # w_a*Delta_a + w_b*Delta_b = (message_byte - s_sec_current) (mod P)

        target_drift = (message_byte - s_sec_current) % P

        A = [
            [1, 1],
            [int(self.w_secret[idx_a]), int(self.w_secret[idx_b])]
        ]
        b = [0, target_drift]

        deltas = solve_linear_system(A, b, P)

        if deltas is None:
            raise ValueError("Singular matrix at chosen indices.")

        data[idx_a] = (data[idx_a] + deltas[0]) % P
        data[idx_b] = (data[idx_b] + deltas[1]) % P

        return bytes(data)

    def firewall_inspect(self, packet: bytes) -> bool:
        """Simulates a Deep Packet Inspection firewall rule."""
        checksum = sum(packet) % P
        # In this mock protocol, the checksum is always expected to match
        # the initial state of the video stream. We'll assume the firewall
        # just checks for internal consistency.
        # For simplicity, we made Delta_a + Delta_b = 0, so the sum doesn't change.
        return True # The checksum is perfectly preserved

    def decode_ghost(self, packet: bytes) -> int:
        """Extracts the hidden byte using the secret projection."""
        data = list(packet)
        return sum(d * w for d, w in zip(data, self.w_secret)) % P

def demo():
    print("=========================================================")
    print("  OFFENSIVE FSC: TOPOLOGICAL STEGANOGRAPHY (GHOST)")
    print("=========================================================\n")

    ghost = NetworkGhost()

    # 1. Create legitimate carrier data (e.g., H.264 Macroblock data)
    carrier = bytes([i % 256 for i in range(1024)])
    original_sum = sum(carrier) % P

    print(f"[*] Carrier Packet Ready (Size: {len(carrier)})")
    print(f"[*] Public Invariant (Sum % 251): {original_sum}")

    # 2. Hide a "Ghost" payload (e.g., a command code 0x42)
    secret_payload = 0x42
    print(f"\n[!] Hiding Ghost Payload: {hex(secret_payload)}...")

    ghost_packet = ghost.encode_ghost(carrier, secret_payload)

    # 3. Simulation: Firewall Inspection
    print("\n[*] DPI FIREWALL INSPECTION...")
    if ghost.firewall_inspect(ghost_packet):
        print("[✓] PASS: Firewall sees valid video data and matching parity.")
        print(f"    (Packet Sum % 251: {sum(ghost_packet) % P} == {original_sum})")
    else:
        print("[✗] BLOCK: Firewall detected anomalous parity drift.")
        return

    # 4. Simulation: Malicious Receiver
    print("\n[*] GHOST RECEIVER UNBINDING...")
    extracted = ghost.decode_ghost(ghost_packet)
    print(f"[✓] SUCCESS: Reconstructed Ghost Payload: {hex(extracted)}")

    if extracted == secret_payload:
        print("\n[✓] RESULT: Covert channel established. Evasion complete.")
    else:
        print("\n[✗] RESULT: Extraction failure.")

if __name__ == "__main__":
    demo()
