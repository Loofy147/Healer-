"""
Advanced Wallet Mnemonic Recovery via GF(p) Polynomials
======================================================
Traditional BIP-39 recovery relies on simple checksums.
This FSC prototype uses polynomial evaluations over GF(2053)
to allow recovery of MULTIPLE missing words (k-fault tolerance).

Example:
  A 12-word mnemonic is treated as coefficients of a polynomial.
  We store k evaluation points as the "FSC Invariant".
  Any k missing words can be exactly recovered by solving
  a linear system over the finite field.

This generalizes the 2-word algebraic recovery to arbitrary k.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from fsc_multifault import MultiFaultFSC, poly_eval, solve_linear_system

# Simplified BIP-39 word list for demo
WORDLIST = [
    "abandon", "ability", "able", "about", "above", "absent", "absorb", "abstract",
    "absurd", "abuse", "access", "accident", "account", "accuse", "achieve", "acid",
    "acoustic", "acquire", "across", "act", "action", "actor", "actress", "actual",
    "adapt", "add", "addict", "address", "adjust", "admit", "adult", "advance",
    "advice", "advisor", "advocate", "affair", "afford", "afraid", "again", "age",
    "agent", "agree", "ahead", "aim", "air", "airport", "aisle", "alarm",
    "album", "alcohol", "alert", "alien", "all", "alley", "allow", "almost",
    "alone", "alpha", "already", "also", "alter", "always", "amateur", "amazing",
    "among", "amount", "amuse", "analyst", "anchor", "ancient", "anger", "angle",
    "angry", "animal", "ankle", "announce", "annual", "another", "answer", "antenna",
    "antique", "anxiety", "any", "apart", "apology", "appear", "apple", "approve",
    "april", "arch", "arctic", "area", "arena", "argue", "arm", "armed",
    "armor", "army", "around", "arrange", "arrest", "arrive", "arrow", "art",
    "artefact", "artist", "artwork", "ask", "aspect", "assault", "asset", "assist",
    "assume", "asthma", "astonish", "athlete", "attitude", "attract", "auction", "audit",
    "august", "aunt", "author", "auto", "autumn", "average", "avocado", "avoid",
    "awake", "aware", "away", "awesome", "awful", "awkward", "axis", "baby",
    "bachelor", "bacon", "badge", "bag", "balance", "balcony", "ball", "bamboo",
    "banana", "banner", "bar", "barely", "bargain", "barrel", "barrier", "base",
    "basic", "basket", "battle", "beach", "beam", "bean", "beauty", "because"
]

class MnemonicGF:
    def __init__(self, k_faults: int = 2):
        # 2053 is the smallest prime > 2048 (BIP39 word list size)
        self.p = 2053
        self.n = 12 # 12 words
        self.k = k_faults
        self.fsc = MultiFaultFSC(self.n, self.k, self.p)

    def get_index(self, word: str) -> int:
        try:
            return WORDLIST.index(word)
        except ValueError:
            # Fallback for words not in our small demo list
            return abs(hash(word)) % 2048

    def get_word(self, idx: int) -> str:
        if 0 <= idx < len(WORDLIST):
            return WORDLIST[idx]
        return f"word_{idx}"

    def protect(self, phrase: list) -> list:
        indices = [self.get_index(w) for w in phrase]
        record = self.fsc.encode(indices)
        return record[self.n:] # Return just the k invariants

    def heal(self, phrase_with_gaps: list, invariants: list) -> list:
        indices = []
        corrupt_indices = []
        for i, w in enumerate(phrase_with_gaps):
            if w == "???":
                indices.append(0)
                corrupt_indices.append(i)
            else:
                indices.append(self.get_index(w))

        full_record = indices + invariants
        healed_record = self.fsc.recover(full_record, corrupt_indices)

        healed_phrase = list(phrase_with_gaps)
        for ci in corrupt_indices:
            healed_phrase[ci] = self.get_word(healed_record[ci])
        return healed_phrase

def demo():
    print("=" * 60)
    print("  ADVANCED WALLET RECOVERY (GF-p)")
    print("  Multi-word healing using polynomial FSC")
    print("=" * 60)

    # 3-word fault tolerance
    m_gf = MnemonicGF(k_faults=3)

    phrase = ["bacon", "actor", "adult", "advice", "agent", "agree", "album", "alert", "alpha", "animal", "ankle", "apple"]

    invariants = m_gf.protect(phrase)
    print(f"\n━━ Original 12-word Mnemonic ━━")
    print(f"  {' '.join(phrase)}")
    print(f"  FSC Invariants (3 evaluation points): {invariants}")

    # ── TRIPLE CORRUPTION ────────────────────────────────────────
    corrupt_idx = [0, 5, 11] # Lose words 1, 6, and 12
    corrupted_phrase = list(phrase)
    for ci in corrupt_idx:
        corrupted_phrase[ci] = "???"

    print(f"\n━━ TRIPLE CORRUPTION DETECTED ━━")
    print(f"  Input: {' '.join(corrupted_phrase)}")

    # ── HEALING ──────────────────────────────────────────────────
    healed_phrase = m_gf.heal(corrupted_phrase, invariants)
    print(f"\n━━ FSC HEALING ━━")
    print(f"  Healed: {' '.join(healed_phrase)}")

    ok = (healed_phrase == phrase)
    print(f"  Exact Recovery: {'✓' if ok else '✗'}")

    print(f"\n  Moment: You lose 3 words from your hardware wallet.")
    print(f"  FSC's polynomial structure over GF(p) recovers them all.")

if __name__ == "__main__":
    demo()
