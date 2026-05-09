"""
FSC: Forward Sector Correction - Manifold Governance (Horizon 7)
Copyright (C) 2024 FSC Core Team. All Rights Reserved.
"""

import numpy as np
from typing import Dict, List, Any
from fsc.advanced.fsc_token import IndustrialManifoldLedger

class ManifoldGovernance:
    """
    Manages network-wide upgrades and parameter changes via consensus.
    """
    def __init__(self, ledger: IndustrialManifoldLedger):
        self.ledger = ledger
        self.proposals: Dict[int, Dict[str, Any]] = {}
        self.proposal_count = 0

    def propose_parameter_change(self, proposer: str, parameter: str, new_value: int) -> int:
        """Proposes a change to a network parameter."""
        # Simple rule: proposer must have some tokens
        if self.ledger.get_balance(proposer) < 100:
            return -1

        prop_id = self.proposal_count
        self.proposals[prop_id] = {
            "proposer": proposer,
            "parameter": parameter,
            "new_value": new_value,
            "votes": {}, # voter -> choice (bool)
            "status": "ACTIVE"
        }
        self.proposal_count += 1
        print(f"[GOVERNANCE] Proposal {prop_id}: Change {parameter} to {new_value}.")
        return prop_id

    def cast_vote(self, voter: str, proposal_id: int, choice: bool) -> bool:
        if proposal_id not in self.proposals: return False
        prop = self.proposals[proposal_id]
        if prop["status"] != "ACTIVE": return False

        # Weighted voting: 1 token = 1 vote
        weight = self.ledger.get_balance(voter)
        if weight <= 0: return False

        prop["votes"][voter] = (choice, weight)
        return True

    def finalize_proposal(self, proposal_id: int) -> bool:
        if proposal_id not in self.proposals: return False
        prop = self.proposals[proposal_id]

        yes_votes = sum(w for choice, w in prop["votes"].values() if choice)
        no_votes = sum(w for choice, w in prop["votes"].values() if not choice)

        if yes_votes > no_votes:
            prop["status"] = "PASSED"
            print(f"[GOVERNANCE] Proposal {proposal_id} PASSED ({yes_votes} vs {no_votes}).")
            # Apply the change
            if prop["parameter"] == "modulus":
                self.ledger.modulus = prop["new_value"]
            return True
        else:
            prop["status"] = "REJECTED"
            print(f"[GOVERNANCE] Proposal {proposal_id} REJECTED.")
            return False

if __name__ == "__main__":
    from fsc.advanced.fsc_token import IndustrialManifoldLedger
    l = IndustrialManifoldLedger()
    l.mint("ALICE", 1000); l.mint("BOB", 500)

    gov = ManifoldGovernance(l)
    pid = gov.propose_parameter_change("ALICE", "modulus", 65537)
    gov.cast_vote("ALICE", pid, True)
    gov.cast_vote("BOB", pid, False)
    gov.finalize_proposal(pid)
