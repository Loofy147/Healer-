import sys
import os
import numpy as np
sys.path.append(os.getcwd())

from fsc.advanced.fsc_mesh import MeshNode, TopologicalSharder

def test_mesh_dht():
    print("Testing Distributed Mesh DHT (Manifold Routing)...")
    sharder = TopologicalSharder(dimension=3)

    # 1. Create a network of nodes
    n_nodes = 50
    nodes = [MeshNode(f"node_{i}", np.random.rand(3)) for i in range(n_nodes)]
    for n in nodes:
        sharder.add_node(n)

    print(f"  Network initialized with {n_nodes} nodes.")

    # 2. Perform iterative lookup for data
    data_id = "sovereign_payload_alpha"
    target_manifold = sharder._hash_to_manifold(data_id)
    print(f"  Target coordinates for '{data_id}': {np.round(target_manifold, 3)}")

    closest_nodes = sharder.find_nodes_for_data(data_id, k=5)

    print(f"  Lookup returned {len(closest_nodes)} closest nodes.")
    for i, n in enumerate(closest_nodes):
        dist = n.distance_to(target_manifold)
        print(f"    [{i}] {n.node_id} - Distance: {dist:.4f}")

    # 3. Verify lookup quality (is it close to global optimum?)
    all_sorted = sorted(nodes, key=lambda n: n.distance_to(target_manifold))
    global_closest = all_sorted[:5]

    match_count = len(set(n.node_id for n in closest_nodes) & set(n.node_id for n in global_closest))
    print(f"  Overlap with global optimum: {match_count}/5")

    # 4. Shard and Reconstruct using DHT lookup
    payload = b"DHT_ALGEBRAIC_RECOVERY_SUCCESS"
    sharder.shard_resilient(data_id, payload)

    # Simulate partial network availability (use a subset of nodes found by DHT)
    subset_shards = {n.node_id: n.storage[data_id] for n in closest_nodes[:3]}
    recovered = sharder.reconstruct_payload(data_id, subset_shards, original_len=len(payload))

    print(f"  Recovered Payload: {recovered}")
    if recovered == payload:
        print("✓ Mesh DHT Verification Successful")
    else:
        print("✗ Mesh DHT Verification Failed")
        sys.exit(1)

if __name__ == "__main__":
    test_mesh_dht()
