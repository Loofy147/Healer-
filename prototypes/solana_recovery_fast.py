from mnemonic import Mnemonic
from solders.keypair import Keypair
from itertools import combinations, product
import time

# The BIP39_SAMPLE from wallet_recovery.py
BIP39_SAMPLE = [
    "snack", "right", "wedding", "gun", "canal", "pet", "rescue", "hand", "scheme", "head",
    "zone", "area", "bridge", "cloud", "dance", "eagle", "forest", "glory", "house", "ice",
    "equal", "element", "vapor", "sword", "nature", "early", "lazy", "drop", "bacon", "whip",
    "blame", "write", "author", "palace"
]

DERIVATION_PATH = "m/44'/501'/0'/0'"
mnemo = Mnemonic("english")

def check_wallet(name, base_words, target):
    print(f"[*] Searching for {name} ({target})...")
    start = time.time()
    all_combos = list(combinations(range(12), 2))

    for pos1, pos2 in all_combos:
        for w1, w2 in product(BIP39_SAMPLE, repeat=2):
            test = [None] * 12
            test[pos1] = w1
            test[pos2] = w2
            idx = 0
            for i in range(12):
                if test[i] is None:
                    test[i] = base_words[idx]
                    idx += 1

            phrase_str = " ".join(test)
            if mnemo.check(phrase_str):
                seed = mnemo.to_seed(phrase_str)
                kp = Keypair.from_seed_and_derivation_path(seed, DERIVATION_PATH)
                if str(kp.pubkey()) == target:
                    print(f"[✓] FOUND {name} in {time.time()-start:.2f}s")
                    print(f"[✓] Phrase: {phrase_str}")
                    return phrase_str
    print(f"[-] {name} not found in sample space.")
    return None

if __name__ == '__main__':
    WALLET_A_WORDS = ["snack", "right", "wedding", "gun", "canal", "pet", "rescue", "hand", "scheme", "head"]
    WALLET_A_TARGET = "7jDVmS8HBdDNdtGXSxepjcktvG6FzbPurZvYUVgY7TG5"

    WALLET_B_WORDS = ["equal", "element", "vapor", "sword", "nature", "early", "lazy", "drop", "bacon", "whip"]
    WALLET_B_TARGET = "93HMaKqUW6VWLJbYCvgViKn176wUcYFq2pfXh1LHkCfj"

    check_wallet("Wallet A", WALLET_A_WORDS, WALLET_A_TARGET)
    check_wallet("Wallet B", WALLET_B_WORDS, WALLET_B_TARGET)
