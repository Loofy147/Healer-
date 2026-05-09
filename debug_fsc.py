import numpy as np
from fsc.advanced.fsc_token import IndustrialManifoldLedger, ManifoldWallet, deterministic_hash

MODULUS = 12289
ledger = IndustrialManifoldLedger(modulus=MODULUS, base_fee=5, reward_multiplier=2)
wallet = ManifoldWallet()
# wallet.lattice.q is hardcoded?
print(f"Wallet Lattice Q: {wallet.lattice.q}")
print(f"Ledger Verifier Q: {ledger.verifier.q}")

alice_addr = wallet.address
ledger.mint(alice_addr, 100)

seal = wallet.sign_transaction("BOB", 50)

recipient_hash = deterministic_hash("BOB", MODULUS)
tx_payload = np.array([50, recipient_hash], dtype=np.int64)

# Test wallet's own verification
print(f"Wallet Verify: {wallet.lattice.verify_seal(tx_payload, seal)}")

# Test ledger's verification
print(f"Ledger Verify: {ledger.verifier.verify_seal(tx_payload, seal)}")
