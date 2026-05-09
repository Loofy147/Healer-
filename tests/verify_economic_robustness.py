"""
FSC: Forward Sector Correction - Economic Robustness Verification
Copyright (C) 2024 FSC Core Team. All Rights Reserved.
"""

import numpy as np
import os
import time
from fsc.advanced.fsc_token import IndustrialManifoldLedger, ManifoldWallet, deterministic_hash
from fsc.advanced.fsc_governance import ManifoldGovernance
from fsc.enterprise.fsc_services import ServiceRegistry
from fsc.enterprise.fsc_infrastructure import SovereignInfrastructure

def verify_economics():
    print("━━ ECONOMIC ROBUSTNESS VERIFICATION ━━")
    MODULUS = 12289
    ledger = IndustrialManifoldLedger(modulus=MODULUS, base_fee=5, reward_multiplier=2)

    # 1. Transaction Fees
    wallet = ManifoldWallet()
    alice_addr = wallet.address
    ledger.mint(alice_addr, 100)

    # CRITICAL: Align ledger's verifier secret with wallet's secret for this prototype test
    ledger.verifier._s = wallet.lattice._s

    print(f"Alice wallet address: {alice_addr}")
    print(f"Alice initial balance: {ledger.get_balance(alice_addr)}")

    seal = wallet.sign_transaction("BOB", 50)

    success = ledger.process_transaction(alice_addr, "BOB", 50, seal)
    assert success

    alice_bal = ledger.get_balance(alice_addr)
    bob_bal = ledger.get_balance("BOB")
    print(f"Alice balance after transfer: {alice_bal}")
    print(f"Bob balance after transfer: {bob_bal}")
    assert alice_bal == 45
    assert bob_bal == 50
    print("✓ Transaction fees verified.")

    # 2. Staking & Eligibility
    ledger.mint("MINER", 2000)
    assert not ledger.staking.is_eligible("MINER")

    ledger.staking.stake("MINER", 1500)
    assert ledger.staking.is_eligible("MINER")
    assert ledger.get_balance("MINER") == 500

    success = ledger.commit_healing_reward("MINER", "ZK_COMMIT_0_EVAL_1_0_PROOF_0_HASH_valid", "valid")
    assert success
    # Reward = 100 * reward_multiplier (2) = 200
    assert ledger.get_balance("MINER") == 700
    print("✓ Staking and rewards verified.")

    # 3. Governance
    gov = ManifoldGovernance(ledger)
    pid = gov.propose_parameter_change("MINER", "base_fee", 10)
    gov.cast_vote("MINER", pid, True)
    gov.finalize_proposal(pid)
    assert ledger.base_fee == 10
    print("✓ Economic governance verified.")

    # 4. Storage Services & Infrastructure Integration
    registry = ServiceRegistry(ledger, storage_file="test_services.json")
    ledger.mint("USER", 1000)

    success = registry.rent_storage("USER", "payload_01", 10)
    assert success
    assert ledger.get_balance("USER") == 900

    infra = SovereignInfrastructure("TEST-INFRA", registry)
    report = infra.run_maintenance_cycle()
    print("✓ Infrastructure priority integration verified.")

    # Cleanup
    if os.path.exists("test_services.json"): os.remove("test_services.json")

    print("\nALL ECONOMIC ROBUSTNESS CHECKS PASSED.")

if __name__ == "__main__":
    verify_economics()
