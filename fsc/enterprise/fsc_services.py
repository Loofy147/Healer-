"""
FSC: Forward Sector Correction - Sovereign Storage Services
Copyright (C) 2024 FSC Core Team. All Rights Reserved.
"""

import time
import json
import os
from typing import Dict, List, Optional, Any
from fsc.advanced.fsc_token import IndustrialManifoldLedger

class StorageServiceContract:
    def __init__(self, owner: str, data_id: str, duration: int, fee_paid: int):
        self.owner = owner
        self.data_id = data_id
        self.start_time = time.time()
        self.expiry = self.start_time + duration
        self.fee_paid = fee_paid
        self.status = "ACTIVE"

    def is_expired(self) -> bool:
        return time.time() > self.expiry

class ServiceRegistry:
    """
    Manages "Data Durability Contracts" where users pay MNF for storage.
    """
    def __init__(self, ledger: IndustrialManifoldLedger, storage_file: str = "services.json"):
        self.ledger = ledger
        self.storage_file = storage_file
        self.contracts: Dict[str, StorageServiceContract] = {}
        self.base_storage_rate = 10 # MNF per hour
        self._load()

    def rent_storage(self, owner: str, data_id: str, hours: int) -> bool:
        fee = hours * self.base_storage_rate
        if self.ledger.get_balance(owner) < fee:
            return False

        # Pay for storage (burning fee for simplicity in this prototype)
        self.ledger.mint(owner, -fee)

        duration = hours * 3600
        contract = StorageServiceContract(owner, data_id, duration, fee)
        self.contracts[data_id] = contract
        self._save()
        print(f"  [SERVICES] Storage rented for {data_id} by {owner} for {hours} hours.")
        return True

    def get_active_contracts(self) -> List[str]:
        active = []
        for did, contract in list(self.contracts.items()):
            if contract.is_expired():
                contract.status = "EXPIRED"
                # Keep in registry but mark expired
            else:
                active.append(did)
        return active

    def _save(self):
        data = {}
        for did, c in self.contracts.items():
            data[did] = {
                "owner": c.owner,
                "data_id": c.data_id,
                "start_time": c.start_time,
                "expiry": c.expiry,
                "fee_paid": c.fee_paid,
                "status": c.status
            }
        with open(self.storage_file, "w") as f:
            json.dump(data, f)

    def _load(self):
        if os.path.exists(self.storage_file):
            with open(self.storage_file, "r") as f:
                data = json.load(f)
                for did, d in data.items():
                    c = StorageServiceContract(d["owner"], d["data_id"], 0, d["fee_paid"])
                    c.start_time = d["start_time"]
                    c.expiry = d["expiry"]
                    c.status = d["status"]
                    self.contracts[did] = c
