"""
FSC: The Manifold Network - Sovereign CLI (Horizon 7)
The primary entry point for managing wallets, nodes, and governance.
"""

import sys
import os
import argparse
from fsc.advanced.fsc_token import ManifoldWallet, PersistentManifoldLedger
from fsc.advanced.fsc_governance import ManifoldGovernance

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

    args = parser.parse_args()

    ledger_file = "manifold_state.fsc"
    ledger = PersistentManifoldLedger(ledger_file)

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

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
