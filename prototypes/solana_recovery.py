import hashlib
import hmac
import time
import base58
from solders.keypair import Keypair
from mnemonic import Mnemonic
import multiprocessing

# Load the official dictionary
mnemo = Mnemonic("english")
wordlist = mnemo.wordlist

# The Targets
WALLET_A_WORDS = ["snack", "right", "wedding", "gun", "canal", "pet", "rescue", "hand", "scheme", "head"]
WALLET_A_PUBKEY = "7jDVmS8HBdDNdtGXSxepjcktvG6FzbPurZvYUVgY7TG5"

WALLET_B_WORDS = ["equal", "element", "vapor", "sword", "nature", "early", "lazy", "drop", "bacon", "whip"]
WALLET_B_PUBKEY = "93HMaKqUW6VWLJbYCvgViKn176wUcYFq2pfXh1LHkCfj"

DERIVATION_PATH = "m/44'/501'/0'/0'"

def derive_solana_pubkey(mnemo_obj, phrase):
    seed = mnemo_obj.to_seed(phrase)
    kp = Keypair.from_seed_and_derivation_path(seed, DERIVATION_PATH)
    return str(kp.pubkey())

def worker(args):
    base_words, target_address, start_idx, end_idx = args
    mnemo_local = Mnemonic("english")
    wordlist_local = mnemo_local.wordlist
    for i in range(start_idx, end_idx):
        w11 = wordlist_local[i]
        for j in range(2048):
            w12 = wordlist_local[j]
            test_phrase = " ".join(base_words + [w11, w12])
            if mnemo_local.check(test_phrase):
                try:
                    if derive_solana_pubkey(mnemo_local, test_phrase) == target_address:
                        return test_phrase
                except:
                    continue
    return None

def ignite_recovery(name, base_words, target):
    print(f"[*] Targeting {name}: {target}")
    start_time = time.time()

    cpu_cores = multiprocessing.cpu_count()
    chunk_size = 2048 // cpu_cores
    tasks = []
    for i in range(cpu_cores):
        s = i * chunk_size
        e = 2048 if i == cpu_cores - 1 else (i + 1) * chunk_size
        tasks.append((base_words, target, s, e))

    with multiprocessing.Pool(processes=cpu_cores) as pool:
        for result in pool.imap_unordered(worker, tasks):
            if result:
                latency = time.time() - start_time
                print(f"[✓] FOUND in {latency:.2f}s: {result}")
                pool.terminate()
                return result
    print("[-] Failed.")
    return None

if __name__ == '__main__':
    ignite_recovery("Wallet A", WALLET_A_WORDS, WALLET_A_PUBKEY)
    ignite_recovery("Wallet B", WALLET_B_WORDS, WALLET_B_PUBKEY)
