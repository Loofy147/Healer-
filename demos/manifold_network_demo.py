"""
FSC: The Manifold Network - Sovereign Decentralized Launch Demo
Showcasing "Healing-as-Mining" with ZK-Proofs and Algebraic Consensus.
"""

import numpy as np
import hashlib
from fsc.advanced.fsc_mesh import MeshNode, TopologicalSharder
from fsc.advanced.fsc_token import ManifoldLedger
from fsc.advanced.fsc_mining import HealingMiner
from fsc.core.fsc_native import is_native_available

def run_demo():
    print("▓" * 60)
    print("  THE MANIFOLD NETWORK: Sovereign Self-Healing Launch")
    print("▓" * 60)

    # 1. Initialize Sovereign Infrastructure
    print("\n[1] Initializing Manifold Ledger & Sharder...")
    ledger = ManifoldLedger()
    sharder = TopologicalSharder()

    # Add nodes to the mesh
    nodes = []
    for i in range(10):
        n = MeshNode(f"node_{i}", np.random.rand(3))
        sharder.add_node(n)
        nodes.append(n)

    print(f"  > Network live with {len(nodes)} nodes.")
    print(f"  > Native Acceleration: {'ENABLED' if is_native_available() else 'DISABLED'}")

    # 2. Data Ingress & Topological Sharding
    print("\n[2] Sharding Data into the Manifold...")
    data_id = "SOVEREIGN_BLUEPRINT_001"
    payload = b"ALGEBRAIC_IMMORTALITY_PROTOCOL_v1.0"

    # K=3 data shards, M=2 parity shards
    shards = sharder.shard_resilient(data_id, payload, k_data=3, m_parity=2)
    print(f"  > Payload sharded (3 Data + 2 Parity) across manifold coordinates.")

    # 3. Simulate Bit-Rot (Algebraic Fault)
    target_node_id = list(shards.keys())[0]
    print(f"\n[3] SIMULATING BIT-ROT on {target_node_id}...")

    # Corrupt the shard data on that node
    correct_shard_bytes = shards[target_node_id]
    corrupted_data = bytearray(correct_shard_bytes)
    corrupted_data[0] = (corrupted_data[0] + 1) % 256

    # Update the node's storage with corrupted data
    for n in nodes:
        if n.node_id == target_node_id:
            n.storage[data_id] = bytes(corrupted_data)
            break

    print(f"  > Shard on {target_node_id} is now ALGEBRAICALLY INVALID.")

    # 4. Healing-as-Mining
    print("\n[4] HEALING-AS-MINING: Node starts scrubbing...")
    miner = HealingMiner(target_node_id, ledger)

    # The miner detects the fault.
    # In a real system, the miner would reconstruct the correct shard
    # using FSC RAID from other nodes.
    # Here we simulate the successful reconstruction by passing 'correct_shard_bytes'.

    correct_shard_arr = np.frombuffer(correct_shard_bytes, dtype=np.uint8)
    original_shard_hash = hashlib.sha256(correct_shard_bytes).hexdigest()

    # Miner performs the healing and submits ZK Proof
    miner.mine_shard(np.frombuffer(corrupted_data, dtype=np.uint8),
                    original_shard_hash,
                    correct_shard_arr)

    # 5. Verify Economic Reward
    print("\n[5] VERIFYING REWARD...")
    balance = ledger.get_balance(target_node_id)
    print(f"  > Miner {target_node_id} Balance: {balance} MNF Tokens")
    print(f"  > Ledger State Root: {ledger.get_state_root()}")

    if balance > 0:
        print("\n" + "═" * 60)
        print("  SUCCESS: THE MANIFOLD NETWORK IS OPERATIONAL")
        print("  Sovereign data has been healed and incentivized.")
        print("═" * 60)
    else:
        print("\n  FAILED: Reward not issued.")

if __name__ == "__main__":
    run_demo()
