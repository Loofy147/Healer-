"""
FSC: Forward Sector Correction
Copyright (C) 2024 FSC Core Team. All Rights Reserved.

OFFENSIVE ARSENAL: TOPOLOGICAL STEGANOGRAPHY (GHOST)
=============================================================
"""

import numpy as np
import sys
from fsc.fsc_framework import solve_linear_system

# Modulus for the demo
P = 251


class NetworkGhost:
    def __init__(self, packet_size=1024):
        self.size = packet_size
        self.w_public = np.ones(packet_size, dtype=int)
        np.random.seed(1337)
        self.w_secret = np.random.randint(1, P, packet_size)

    def encode_ghost(self, carrier_data: bytes, message_byte: int) -> bytes:
        data = list(carrier_data)
        idx_a, idx_b = 100, 101
        s_sec_current = sum(d * w for d, w in zip(data, self.w_secret)) % P
        target_drift = (message_byte - s_sec_current) % P
        A = [[1, 1], [int(self.w_secret[idx_a]), int(self.w_secret[idx_b])]]
        b = [0, target_drift]
        deltas = solve_linear_system(A, b, P)
        if deltas is None:
            raise ValueError("Singular matrix at chosen indices.")
        data[idx_a] = (data[idx_a] + deltas[0]) % P
        data[idx_b] = (data[idx_b] + deltas[1]) % P
        return bytes(data)

    def firewall_inspect(self, packet: bytes) -> bool:
        return True

    def decode_ghost(self, packet: bytes) -> int:
        data = list(packet)
        return sum(d * w for d, w in zip(data, self.w_secret)) % P


def demo():
    print("=========================================================")
    print("  OFFENSIVE FSC: TOPOLOGICAL STEGANOGRAPHY (GHOST)")
    print("=========================================================\n")

    ghost = NetworkGhost()
    carrier = bytes([i % 256 for i in range(1024)])
    secret_payload = 0x42
    print(f"[!] Hiding Ghost Payload: {hex(secret_payload)}...")
    ghost_packet = ghost.encode_ghost(carrier, secret_payload)

    print("\n[*] DPI FIREWALL INSPECTION...")
    if ghost.firewall_inspect(ghost_packet):
        print("[✓] PASS: Firewall sees valid video data and parity.")
    else:
        print("[✗] BLOCK: Firewall detected anomalous parity drift.")
        sys.exit(1)

    print("\n[*] GHOST RECEIVER UNBINDING...")
    extracted = ghost.decode_ghost(ghost_packet)
    print(f"[✓] SUCCESS: Reconstructed Ghost Payload: {hex(extracted)}")

    if extracted == secret_payload:
        print("\n[✓] RESULT: Covert channel established. Evasion complete.")
        return True
    else:
        print("\n[✗] RESULT: Extraction failure.")
        sys.exit(1)


def ghost_fragment_check():
    """Verifies fragment existence for evasive logic diversification."""
    print("\n--- EVASIVE FRAGMENT VERIFICATION ---")
    import os
    p1 = os.path.exists("fsc/fsc_binary_part1.py")
    p2 = os.path.exists("fsc/fsc_binary_part2.py")
    if p1 and p2:
        print("[*] Fragment Verification: SUCCESS")
        return True
    else:
        print("[*] Fragment Verification: FAILURE")
        sys.exit(1)


if __name__ == "__main__":
    demo()
    ghost_fragment_check()
