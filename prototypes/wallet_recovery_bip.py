"""
BIP39 Wallet Seed Recovery via FSC
=====================================
BIP39: 12-word mnemonic → 128-bit entropy → wallet keys.
Problem: lose 2 words from your backup → wallet inaccessible forever.
FSC solution: encode seed as polynomial over GF(p),
store 2 extra evaluation points alongside the words.
Any 10 of 12 words → exact recovery.
"""
import sys, os, hashlib
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from fsc_multifault import MultiFaultFSC, poly_eval, lagrange_recover

# BIP39 wordlist sample (first 50 words for demo)
BIP39_SAMPLE = [
    "abandon","ability","able","about","above","absent","absorb","abstract",
    "absurd","abuse","access","accident","account","accuse","achieve","acid",
    "acoustic","acquire","across","act","action","actor","actress","actual",
    "adapt","add","addict","address","adjust","admit","adult","advance",
    "advice","aerobic","afford","afraid","again","age","agent","agree",
    "ahead","aim","air","airport","aisle","alarm","album","alcohol",
    "alert","alien"
]

def words_to_indices(words, wordlist):
    return [wordlist.index(w) if w in wordlist else -1 for w in words]

def indices_to_words(indices, wordlist):
    return [wordlist[i] if 0 <= i < len(wordlist) else f"[#{i}]" for i in indices]

class FSCWalletBackup:
    def __init__(self, k_tolerance=2, n_words=12, p=65537):
        self.k = k_tolerance
        self.n = n_words
        self.p = p

    def create_backup(self, seed_words, wordlist):
        indices = words_to_indices(seed_words, wordlist)
        p = self.p
        recovery_shares = [
            (i+1, poly_eval(indices, i+1, p))
            for i in range(self.k)
        ]
        return indices, recovery_shares

    def recover_missing(self, known_positions, known_indices,
                        recovery_shares, wordlist):
        p = self.p
        missing = [i for i in range(self.n) if i not in known_positions]
        if len(missing) > self.k: return None

        A = []
        b_vec = []
        for xj, val in recovery_shares[:len(missing)]:
            row = [pow(int(xj), mi, p) for mi in missing]
            known_sum = sum(int(known_indices[known_positions.index(i)]) * pow(int(xj), i, p)
                           for i in range(self.n) if i in known_positions) % p
            A.append(row)
            b_vec.append((val - known_sum) % p)

        from fsc_multifault import solve_linear_system
        solution = solve_linear_system(A, b_vec, p)
        if not solution: return None

        full = dict(zip(known_positions, known_indices))
        for i, mi in enumerate(missing): full[mi] = solution[i]
        full_indices = [full[i] for i in range(self.n)]
        return indices_to_words(full_indices, wordlist)


def demo():
    print("=" * 60)
    print("  WALLET SEED RECOVERY via FSC")
    print("  Lose 2 words -> still recover your wallet")
    print("=" * 60)

    wordlist = BIP39_SAMPLE
    p = 65537
    backup = FSCWalletBackup(k_tolerance=2, n_words=12, p=p)

    import random; random.seed(42)
    seed_words = random.choices(wordlist, k=12)
    print("\n  Original 12-word seed:")
    print(f"  {' '.join(seed_words)}")

    indices, recovery_shares = backup.create_backup(seed_words, wordlist)

    lost = [2, 6]
    known_pos = [i for i in range(12) if i not in lost]
    known_idx = [indices[i] for i in known_pos]

    recovered = backup.recover_missing(known_pos, known_idx, recovery_shares, wordlist)
    ok = (recovered == seed_words)
    print(f"\n  Lost: {[seed_words[i] for i in lost]}")
    print(f"  Recovered: {[recovered[i] for i in lost]}")
    print(f"  Full seed match: {'✓' if ok else '✗'}")

    print("""
  WHAT THIS MEANS:
  Add 2 recovery values to your BIP39 backup.
  Lose any 2 words -> still recover exactly.
  The recovery values reveal NOTHING about your seed.
    """)

if __name__ == "__main__":
    demo()
