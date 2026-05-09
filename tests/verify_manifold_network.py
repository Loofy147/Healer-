"""
FSC: The Manifold Network - System Integration Verification
"""

import unittest
import os
import numpy as np
from fsc.advanced.fsc_token import PersistentManifoldLedger, ManifoldWallet
from fsc.advanced.fsc_governance import ManifoldGovernance

class TestManifoldNetwork(unittest.TestCase):
    def setUp(self):
        self.fname = "test_ledger.fsc"
        if os.path.exists(self.fname): os.remove(self.fname)
        if os.path.exists(self.fname + ".map"): os.remove(self.fname + ".map")
        self.ledger = PersistentManifoldLedger(self.fname)

    def tearDown(self):
        if os.path.exists(self.fname): os.remove(self.fname)
        if os.path.exists(self.fname + ".map"): os.remove(self.fname + ".map")

    def test_persistence_integrity(self):
        self.ledger.mint("ALICE", 123)
        self.ledger.mint("BOB", 456)

        # New ledger instance from same file
        new_ledger = PersistentManifoldLedger(self.fname)
        self.assertEqual(new_ledger.get_balance("ALICE"), 123)
        self.assertEqual(new_ledger.get_balance("BOB"), 456)

    def test_wallet_and_transaction(self):
        wallet = ManifoldWallet()
        self.ledger.mint(wallet.address, 1000)

        # We need the ledger verifier to match the wallet's lattice in this proto
        self.ledger.verifier = wallet.lattice

        seal = wallet.sign_transaction("RECIPIENT", 500)
        success = self.ledger.process_transaction(wallet.address, "RECIPIENT", 500, seal)
        self.assertTrue(success)
        self.assertEqual(self.ledger.get_balance(wallet.address), 500)
        self.assertEqual(self.ledger.get_balance("RECIPIENT"), 500)

    def test_governance(self):
        gov = ManifoldGovernance(self.ledger)
        self.ledger.mint("ALICE", 1000)
        pid = gov.propose_parameter_change("ALICE", "modulus", 12289)
        self.assertTrue(gov.cast_vote("ALICE", pid, True))
        self.assertTrue(gov.finalize_proposal(pid))

if __name__ == "__main__":
    unittest.main()
