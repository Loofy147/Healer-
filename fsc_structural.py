"""
FSC Structural Invariants
=========================
Moving from "storing the invariant" to "making the invariant the structure".
"""
import numpy as np

class StructuralFSC:
    """
    Demonstrates formats where corruption is algebraically detectable
    and recoverable WITHOUT external metadata.
    """

    @staticmethod
    def dna_mirror_encode(data, m=256):
        """
        Mirroring (DNA-style):
        Original data followed by its modular complement.
        Invariant: stream[i] + stream[i+n] = m
        """
        data = np.array(data)
        complement = (m - data) % m
        return np.concatenate([data, complement])

    @staticmethod
    def dna_mirror_recover(stream, lost_idx, m=256):
        n = len(stream) // 2
        if lost_idx < n:
            return (m - stream[lost_idx + n]) % m
        else:
            return (m - stream[lost_idx - n]) % m

    @staticmethod
    def ledger_balance_encode(data, group_size=4):
        """
        Zero-Sum Balancing (Ledger-style):
        Every group_size elements sum to zero.
        The last element of each group is the 'balance' element.
        """
        encoded = []
        for i in range(0, len(data), group_size - 1):
            block = list(data[i:i+group_size-1])
            # If the last chunk is smaller, we'd need padding,
            # but for this demo assume clean multiples.
            balance = -sum(block)
            block.append(balance)
            encoded.extend(block)
        return np.array(encoded, dtype=np.int64)

    @staticmethod
    def ledger_balance_recover(stream, lost_idx, group_size=4):
        start = (lost_idx // group_size) * group_size
        block = stream[start:start+group_size]
        # Invariant: sum(block) = 0
        # sum(survivors) + x = 0  => x = -sum(survivors)
        known_sum = sum(v for i, v in enumerate(block) if (start + i) != lost_idx)
        return -known_sum

def run_demo():
    print("=" * 68)
    print("  FSC STRUCTURAL INVARIANTS — BEYOND METADATA")
    print("=" * 68)

    # 1. DNA Mirroring
    print("\n━━ 1. DNA-STYLE MIRRORING ━━")
    data = [65, 84, 71, 67] # ATGC
    encoded = StructuralFSC.dna_mirror_encode(data)
    print(f"  Original: {data}")
    print(f"  Encoded:  {encoded.tolist()}")

    corrupted = encoded.copy()
    corrupted[2] = 0 # lose 'G'
    rec = StructuralFSC.dna_mirror_recover(corrupted, 2)
    print(f"  Corrupt:  {corrupted.tolist()} (idx 2 lost)")
    print(f"  Recovered: {rec} (was {encoded[2]})  exact={rec == encoded[2]}")

    # 2. Ledger Balancing
    print("\n━━ 2. LEDGER-STYLE BALANCING ━━")
    fin_data = [1000, -300, 500]
    balanced = StructuralFSC.ledger_balance_encode(fin_data, 4)
    print(f"  Financials: {fin_data}")
    print(f"  Balanced:   {balanced.tolist()} (sum={sum(balanced)})")

    corrupted_bal = balanced.copy()
    corrupted_bal[3] = 0 # lose the balance element itself
    rec_bal = StructuralFSC.ledger_balance_recover(corrupted_bal, 3, 4)
    print(f"  Corrupt:    {corrupted_bal.tolist()} (idx 3 lost)")
    print(f"  Recovered:  {rec_bal} (was {balanced[3]})  exact={rec_bal == balanced[3]}")

    print("\n" + "=" * 68)
    print("  THE KEY DIFFERENCE")
    print("=" * 68)
    print("  Metadata FSC: [Data] + [Invariant]")
    print("  Structural FSC: [Data structured TO BE the invariant]")
    print()
    print("  In structural formats, the recovery logic is a property ")
    print("  of the format's geometry, not an external 'tag'.")

if __name__ == "__main__":
    run_demo()
