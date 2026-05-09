"""
FSC: Forward Sector Correction - Industrial Manifold Token & Sovereign Ledger (Horizon 7)
Copyright (C) 2024 FSC Core Team. All Rights Reserved.
"""

import numpy as np
import hashlib
import os
import json
from typing import Dict, List, Optional, Any, Tuple
from fsc.advanced.fsc_mesh import ConsensusManifold
from fsc.advanced.fsc_quantum import LatticeIntegrity, ZKHealer
from fsc.storage.fsc_database import StructuralTable
from mnemonic import Mnemonic

def deterministic_hash(val: Any, modulus: int) -> int:
    """Returns a deterministic modular integer hash."""
    h = hashlib.sha256(str(val).encode()).hexdigest()
    return int(h, 16) % modulus

class StakingManager:
    """
    Manages node collateral and handles slashing for failed integrity audits.
    """
    def __init__(self, ledger: 'IndustrialManifoldLedger', min_stake: int = 1000):
        self.ledger = ledger
        self.min_stake = min_stake
        self.stakes: Dict[str, int] = {}

    def stake(self, address: str, amount: int) -> bool:
        if self.ledger.get_balance(address) < amount:
            return False
        # Deduct from balance, add to stake
        self.ledger.mint(address, -amount)
        self.stakes[address] = self.stakes.get(address, 0) + amount
        print(f"  [STAKING] {address} staked {amount} MNF (Total: {self.stakes[address]})")
        return True

    def unstake(self, address: str, amount: int) -> bool:
        current_stake = self.stakes.get(address, 0)
        if current_stake < amount:
            return False
        self.stakes[address] -= amount
        self.ledger.mint(address, amount)
        print(f"  [STAKING] {address} unstaked {amount} MNF")
        return True

    def slash(self, address: str, penalty: int):
        current_stake = self.stakes.get(address, 0)
        actual_penalty = min(current_stake, penalty)
        self.stakes[address] -= actual_penalty
        print(f"  [SLASH] {address} slashed for {actual_penalty} MNF!")

    def is_eligible(self, address: str) -> bool:
        return self.stakes.get(address, 0) >= self.min_stake

class IndustrialManifoldLedger:
    """
    An industrially-hardened ledger using Structural FSC for its internal state.
    Every balance is protected by 2D algebraic constraints.
    """
    def __init__(self, n_nodes: int = 10, threshold: int = 4, modulus: int = 12289, max_accounts: int = 16, base_fee: int = 1, reward_multiplier: int = 1):
        self.modulus = modulus
        self.base_fee = base_fee
        self.reward_multiplier = reward_multiplier
        self.staking = StakingManager(self)
        self.consensus = ConsensusManifold(n_nodes, threshold, modulus)
        self.history: List[Dict[str, Any]] = []
        self.verifier = LatticeIntegrity(q=modulus)

        self.dim = int(np.sqrt(max_accounts))
        self.table = StructuralTable(self.dim, self.dim, m=modulus)
        self.address_map: Dict[str, Tuple[int, int]] = {}
        self.reverse_map: Dict[str, str] = {}
        self.next_idx = 0

    def _get_coords(self, address: str) -> Tuple[int, int]:
        if address not in self.address_map:
            if self.next_idx >= self.dim * self.dim:
                raise ValueError("Ledger full")
            r, c = divmod(self.next_idx, self.dim)
            self.address_map[address] = (r, c)
            self.reverse_map[str((r, c))] = address
            self.next_idx += 1
        return self.address_map[address]

    def get_balance(self, address: str) -> int:
        r, c = self._get_coords(address)
        return int(self.table.data[r, c])

    def mint(self, address: str, amount: int):
        r, c = self._get_coords(address)
        current = self.table.data[r, c]
        raw = self.table.data[:self.dim, :self.dim].copy()
        raw[r, c] = (current + amount) % self.modulus
        self.table.set_data(raw.tolist())
        self.history.append({"op": "MINT", "to": address, "amount": amount})

    def process_transaction(self, sender: str, recipient: str, amount: int, seal: np.ndarray) -> bool:
        total_deduction = amount + self.base_fee
        if self.get_balance(sender) < total_deduction: return False

        recipient_hash = deterministic_hash(recipient, self.modulus)
        tx_payload = np.array([amount, recipient_hash], dtype=np.int64)
        if not self.verifier.verify_seal(tx_payload, seal): return False

        tx_id = deterministic_hash((sender, recipient, amount, len(self.history)), self.modulus)
        shares = self.consensus.propose_value(tx_id)
        shares_dict = {i+1: shares[i] for i in range(self.consensus.threshold)}
        agreed_id = self.consensus.reach_consensus(shares_dict)

        if agreed_id != tx_id: return False

        sr, sc = self._get_coords(sender)
        rr, rc = self._get_coords(recipient)
        raw = self.table.data[:self.dim, :self.dim].copy()
        raw[sr, sc] = (raw[sr, sc] - total_deduction) % self.modulus
        raw[rr, rc] = (raw[rr, rc] + amount) % self.modulus
        self.table.set_data(raw.tolist())

        self.history.append({"op": "TRANSFER", "from": sender, "to": recipient, "amount": amount, "tx_id": tx_id})
        return True

    def commit_healing_reward(self, miner_address: str, proof: str, original_hash: str):
        healer = ZKHealer(modulus=self.modulus)
        if self.staking.is_eligible(miner_address) and healer.verify_proof(proof, original_hash):
            reward = 100 * self.reward_multiplier
            self.mint(miner_address, reward)
            return True
        return False

    def scrub_state(self) -> int:
        heals = self.table.verify_and_heal()
        return len(heals)

    def get_state_root(self) -> int:
        state_str = str(self.table.data.tolist())
        return deterministic_hash(state_str, self.modulus)

class PersistentManifoldLedger(IndustrialManifoldLedger):
    def __init__(self, filename: str, **kwargs):
        super().__init__(**kwargs)
        self.filename = filename
        self.map_filename = filename + ".map"
        self.staking_filename = filename + ".staking"
        self._load_from_disk()

    def _load_from_disk(self):
        if os.path.exists(self.filename) and os.path.exists(self.map_filename):
            with open(self.map_filename, "r") as f:
                data = json.load(f)
                self.address_map = data["address_map"]
                self.reverse_map = data["reverse_map"]
                self.next_idx = data["next_idx"]
            if os.path.exists(self.staking_filename):
                with open(self.staking_filename, "r") as f:
                    self.staking.stakes = json.load(f)
            with open(self.filename, "rb") as f:
                raw_bytes = f.read()
                self.table.data = np.frombuffer(raw_bytes, dtype=np.int64).reshape(self.table.data.shape).copy()
                print(f"  [LEDGER] State and Mapping loaded from {self.filename}")

    def _sync_to_disk(self):
        with open(self.filename, "wb") as f: f.write(self.table.data.tobytes())
        with open(self.map_filename, "w") as f:
            json.dump({"address_map": self.address_map, "reverse_map": self.reverse_map, "next_idx": self.next_idx}, f)
        with open(self.staking_filename, "w") as f:
            json.dump(self.staking.stakes, f)

    def mint(self, address: str, amount: int):
        super().mint(address, amount)
        self._sync_to_disk()

    def process_transaction(self, sender: str, recipient: str, amount: int, seal: np.ndarray) -> bool:
        success = super().process_transaction(sender, recipient, amount, seal)
        if success: self._sync_to_disk()
        return success

    def commit_healing_reward(self, miner_address: str, proof: str, original_hash: str):
        success = super().commit_healing_reward(miner_address, proof, original_hash)
        if success: self._sync_to_disk()
        return success

    def stake(self, address: str, amount: int) -> bool:
        success = self.staking.stake(address, amount)
        if success: self._sync_to_disk()
        return success

    def unstake(self, address: str, amount: int) -> bool:
        success = self.staking.unstake(address, amount)
        if success: self._sync_to_disk()
        return success

class ManifoldNetworkNode:
    def __init__(self, node_id: str, ledger: IndustrialManifoldLedger):
        self.node_id = node_id
        self.ledger = ledger
        self.mempool: List[Dict[str, Any]] = []

    def receive_transaction_group(self, tx_payloads: List[Dict[str, Any]]):
        print(f"  [NODE {self.node_id}] Received resilient transaction group.")
        for tx in tx_payloads: self.mempool.append(tx)
        return True

class ManifoldWallet:
    def __init__(self, phrase: Optional[str] = None):
        mnemo = Mnemonic("english")
        if phrase is None: self.phrase = mnemo.generate(strength=128)
        else: self.phrase = phrase
        seed = mnemo.to_seed(self.phrase)
        self.address = hashlib.sha256(seed).hexdigest()[:16]
        np.random.seed(int(hashlib.md5(seed).hexdigest(), 16) % 0xFFFFFFFF)
        self.lattice = LatticeIntegrity(q=12289)

    def sign_transaction(self, recipient: str, amount: int) -> np.ndarray:
        recipient_hash = deterministic_hash(recipient, 12289)
        tx_payload = np.array([amount, recipient_hash], dtype=np.int64)
        return self.lattice.create_seal(tx_payload)

def demo_persistence():
    print("\n━━ PERSISTENCE DEMO ━━")
    fname = "ledger_vault.fsc"
    if os.path.exists(fname): os.remove(fname)
    if os.path.exists(fname + ".map"): os.remove(fname + ".map")
    ledger = PersistentManifoldLedger(fname, max_accounts=16)
    ledger.mint("ALICE", 500)
    print(f"Alice balance (initial): {ledger.get_balance('ALICE')}")
    new_ledger = PersistentManifoldLedger(fname, max_accounts=16)
    print(f"Alice balance (recovered): {new_ledger.get_balance('ALICE')}")
    assert new_ledger.get_balance('ALICE') == 500
    print("✓ Persistence verified.")
    if os.path.exists(fname): os.remove(fname)
    if os.path.exists(fname + ".map"): os.remove(fname + ".map")

def demo_wallet():
    print("\n━━ WALLET DEMO ━━")
    wallet = ManifoldWallet()
    print(f"Phrase: {wallet.phrase}"); print(f"Address: {wallet.address}")
    seal = wallet.sign_transaction("BOB", 100)
    tx_payload = np.array([100, deterministic_hash("BOB", 12289)], dtype=np.int64)
    valid = wallet.lattice.verify_seal(tx_payload, seal)
    print(f"Lattice Signature Valid: {valid}"); assert valid

if __name__ == "__main__":
    demo_persistence()
    demo_wallet()
