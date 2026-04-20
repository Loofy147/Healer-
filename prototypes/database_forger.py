"""
FSC: Forward Sector Correction
Copyright (C) 2024 FSC Core Team. All Rights Reserved.

OFFENSIVE ARSENAL: DATABASE FORGERY (Data Poisoning)
===================================================
Demonstrates using the O(1) Galois Field solver to invisibly
modify database records while maintaining bit-perfect
algebraic checksums.
"""

import numpy as np
import struct
from fsc.fsc_framework import solve_linear_system

# Modulus: Mersenne Prime p = 2^61 - 1
P = 2305843009213693951

class DatabasePage:
    def __init__(self, size=4096):
        self.size = size
        # Use Python list of ints for arbitrary precision during sum
        self.data = [0] * (size // 8)
        self.w1 = [1] * (size // 8)
        self.w2 = list(range(1, (size // 8) + 1))

    def set_balance(self, balance: int):
        self.data[10] = balance

    def get_balance(self) -> int:
        return self.data[10]

    def calculate_syndromes(self):
        s1 = sum(d * w for d, w in zip(self.data, self.w1)) % P
        s2 = sum(d * w for d, w in zip(self.data, self.w2)) % P
        return s1, s2

def gf_forge():
    print("=========================================================")
    print("  OFFENSIVE FSC: ALGEBRAIC DATABASE FORGERY ENGINE")
    print("=========================================================\n")

    page = DatabasePage()
    page.set_balance(100)

    # Random noise
    np.random.seed(42)
    noise = np.random.randint(0, 1000000, 30, dtype=np.int64)
    for i in range(30):
        page.data[20 + i] = int(noise[i])

    orig_s1, orig_s2 = page.calculate_syndromes()
    print(f"[*] Original Balance: ${page.get_balance()}")
    print(f"[*] Original Parity S1: {orig_s1}")
    print(f"[*] Original Parity S2: {orig_s2}\n")

    print("[!] INITIATING FORGERY...")
    new_balance = 9999999
    page.set_balance(new_balance)

    curr_s1, curr_s2 = page.calculate_syndromes()
    d1 = (orig_s1 - curr_s1) % P
    d2 = (orig_s2 - curr_s2) % P

    print(f"[*] Forged Balance: ${page.get_balance()}")
    print(f"[*] Parity Drift Detected: ({d1}, {d2})\n")

    idx_a, idx_b = 500, 501
    A = [
        [page.w1[idx_a], page.w1[idx_b]],
        [page.w2[idx_a], page.w2[idx_b]]
    ]
    b = [d1, d2]

    deltas = solve_linear_system(A, b, P)

    if deltas is None:
        print("[✗] ERROR: Linear system is singular.")
        return

    print(f"[*] Calculating Forgery Compensation for indices {idx_a}, {idx_b}...")
    page.data[idx_a] = (page.data[idx_a] + deltas[0]) % P
    page.data[idx_b] = (page.data[idx_b] + deltas[1]) % P

    final_s1, final_s2 = page.calculate_syndromes()

    print("\n[+] FORGERY COMPLETE.")
    print(f"[*] Final Balance: ${page.get_balance()}")
    print(f"[*] Final Parity S1: {final_s1} (Match: {final_s1 == orig_s1})")
    print(f"[*] Final Parity S2: {final_s2} (Match: {final_s2 == orig_s2})")

    if final_s1 == orig_s1 and final_s2 == orig_s2:
        print("\n[✓] SUCCESS: The database will silently accept this forged page as authentic.")
    else:
        print("\n[✗] FAILURE: Checksum mismatch.")

if __name__ == "__main__":
    gf_forge()
