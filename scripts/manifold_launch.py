"""
FSC: The Manifold Network - Sovereign CLI (Horizon 7)
The primary entry point for managing wallets, nodes, and governance.
"""

import sys
import os
import argparse
import json
from fsc.advanced.fsc_token import ManifoldWallet, PersistentManifoldLedger
from fsc.advanced.fsc_governance import ManifoldGovernance
from fsc.enterprise.fsc_services import ServiceRegistry

def main():
    parser = argparse.ArgumentParser(description="The Manifold Network CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Wallet Commands
    subparsers.add_parser("wallet-gen", help="Generate a new sovereign wallet")

    # Ledger Commands
    mint_parser = subparsers.add_parser("mint", help="Initial minting (Privileged)")
    mint_parser.add_argument("--address", required=True)
    mint_parser.add_argument("--amount", type=int, required=True)

    balance_parser = subparsers.add_parser("balance", help="Check address balance")
    balance_parser.add_argument("--address", required=True)

    # Staking Commands
    stake_parser = subparsers.add_parser("stake", help="Stake tokens for node eligibility")
    stake_parser.add_argument("--address", required=True)
    stake_parser.add_argument("--amount", type=int, required=True)

    unstake_parser = subparsers.add_parser("unstake", help="Unstake tokens")
    unstake_parser.add_argument("--address", required=True)
    unstake_parser.add_argument("--amount", type=int, required=True)

    # Storage Commands
    rent_parser = subparsers.add_parser("rent-storage", help="Rent data durability service")
    rent_parser.add_argument("--address", required=True)
    rent_parser.add_argument("--data-id", required=True)
    rent_parser.add_argument("--hours", type=int, required=True)

    # Governance Commands
    propose_parser = subparsers.add_parser("propose", help="Propose a parameter change")
    propose_parser.add_argument("--proposer", required=True)
    propose_parser.add_argument("--param", required=True, choices=["modulus", "base_fee", "reward_multiplier", "min_stake"])
    propose_parser.add_argument("--value", type=int, required=True)

    args = parser.parse_args()

    ledger_file = "manifold_state.fsc"
    ledger = PersistentManifoldLedger(ledger_file)
    registry = ServiceRegistry(ledger)
    gov = ManifoldGovernance(ledger)

    if args.command == "wallet-gen":
        wallet = ManifoldWallet()
        print(f"NEW SOVEREIGN WALLET GENERATED")
        print(f"Address: {wallet.address}")
        print(f"Mnemonic: {wallet.phrase}")
        print("-" * 40)
        print("KEEP THIS MNEMONIC SECURE. IT IS THE ONLY WAY TO RECOVER YOUR TOKENS.")

    elif args.command == "mint":
        ledger.mint(args.address, args.amount)
        print(f"Minted {args.amount} MNF to {args.address}")

    elif args.command == "balance":
        print(f"Address: {args.address}")
        print(f"Balance: {ledger.get_balance(args.address)} MNF")
        print(f"Staked: {ledger.staking.stakes.get(args.address, 0)} MNF")

    elif args.command == "stake":
        if ledger.stake(args.address, args.amount):
            print(f"Successfully staked {args.amount} MNF for {args.address}")
        else:
            print(f"FAILED to stake {args.amount} MNF (Insufficient balance?)")

    elif args.command == "unstake":
        if ledger.unstake(args.address, args.amount):
            print(f"Successfully unstaked {args.amount} MNF for {args.address}")
        else:
            print(f"FAILED to unstake {args.amount} MNF (Insufficient stake?)")

    elif args.command == "rent-storage":
        if registry.rent_storage(args.address, args.data_id, args.hours):
            print(f"Successfully rented storage for {args.data_id}")
        else:
            print(f"FAILED to rent storage (Insufficient balance?)")

    elif args.command == "propose":
        pid = gov.propose_parameter_change(args.proposer, args.param, args.value)
        if pid >= 0:
            print(f"Proposal {pid} created: Change {args.param} to {args.value}")
        else:
            print(f"FAILED to create proposal (Insufficient balance?)")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
