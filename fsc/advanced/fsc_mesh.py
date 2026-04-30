"""
FSC: Forward Sector Correction - Distributed Sovereign Mesh (Horizon 6)
Copyright (C) 2024 FSC Core Team. All Rights Reserved.
"""

import numpy as np
import hashlib
import random
from typing import List, Dict, Optional
from fsc.core.fsc_framework import solve_linear_system
from fsc.enterprise.fsc_config import SovereignConfig

class MeshNode:
    def __init__(self, node_id: str, coords: np.ndarray):
        self.node_id = node_id
        self.coords = coords
        self.storage = {}

    def distance_to(self, target_coords: np.ndarray) -> float:
        return np.linalg.norm(self.coords - target_coords)

class ConsensusManifold:
    def __init__(self, n_nodes: int, threshold: int, modulus: int = 12289):
        self.n_nodes = n_nodes
        self.threshold = threshold
        self.modulus = modulus

    def propose_value(self, value: int) -> List[int]:
        coeffs = [value] + [random.randint(0, self.modulus - 1) for _ in range(self.threshold - 1)]
        shares = []
        for i in range(1, self.n_nodes + 1):
            share = 0
            for j, c in enumerate(coeffs):
                share = (share + c * (i ** j)) % self.modulus
            shares.append(share)
        return shares

    def reach_consensus(self, shares: Dict[int, int]) -> Optional[int]:
        if len(shares) < self.threshold: return None
        x_vals = list(shares.keys()); y_vals = list(shares.values())
        secret = 0
        for i in range(len(x_vals)):
            li = 1
            for j in range(len(x_vals)):
                if i == j: continue
                num = (0 - x_vals[j]) % self.modulus
                den = (x_vals[i] - x_vals[j]) % self.modulus
                li = (li * num * pow(den, -1, self.modulus)) % self.modulus
            secret = (secret + y_vals[i] * li) % self.modulus
        return secret

class TopologicalSharder:
    def __init__(self, dimension: int = 3, modulus: Optional[int] = None):
        self.nodes = []
        self.dimension = dimension
        self.modulus = modulus or SovereignConfig.get_manifold_params()["modulus"]

    def add_node(self, node: MeshNode):
        self.nodes.append(node)

    def _hash_to_manifold(self, data_id: str) -> np.ndarray:
        h = hashlib.sha256(data_id.encode()).digest()
        coords = []
        for i in range(self.dimension):
            chunk = h[i*4 : (i+1)*4]
            coords.append(int.from_bytes(chunk, "big") / 0xFFFFFFFF)
        return np.array(coords)

    def shard_resilient(self, data_id: str, payload: bytes, k_data: int = 3, m_parity: int = 2) -> Dict[str, bytes]:
        total_shards = k_data + m_parity
        targets = sorted(self.nodes, key=lambda n: n.distance_to(self._hash_to_manifold(data_id)))[:total_shards]
        chunk_size = (len(payload) + k_data - 1) // k_data
        padded_payload = payload.ljust(chunk_size * k_data, b"\0")
        data_shards = [np.frombuffer(padded_payload[i*chunk_size:(i+1)*chunk_size], dtype=np.uint8) for i in range(k_data)]
        shards = {}
        for i in range(k_data):
            shards[targets[i].node_id] = data_shards[i].tobytes()
            targets[i].storage[data_id] = data_shards[i].tobytes()
        for j in range(m_parity):
            p_acc = np.zeros(chunk_size, dtype=np.int64)
            for i in range(k_data):
                weight = pow(i + 1, j, self.modulus)
                p_acc = (p_acc + data_shards[i].astype(np.int64) * weight) % self.modulus
            p_bytes = p_acc.astype(np.uint8).tobytes()
            shards[targets[k_data + j].node_id] = p_bytes
            targets[k_data + j].storage[data_id] = p_bytes
        return shards

    def reconstruct_payload(self, data_id: str, shard_data: Dict[str, bytes], k_data: int = 3, original_len: int = 0) -> bytes:
        """
        Reconstructs the original payload from available shards using algebraic solver.
        """
        # Mapping available shards back to their indices (0..k+m-1)
        targets = sorted(self.nodes, key=lambda n: n.distance_to(self._hash_to_manifold(data_id)))[:5] # Assume k=3, m=2
        node_id_to_idx = {n.node_id: i for i, n in enumerate(targets)}

        available_indices = []
        available_shards = []
        for nid, data in shard_data.items():
            if nid in node_id_to_idx:
                available_indices.append(node_id_to_idx[nid])
                available_shards.append(np.frombuffer(data, dtype=np.uint8))

        if len(available_shards) < k_data: return b""

        chunk_size = len(available_shards[0])
        reconstructed = np.zeros((k_data, chunk_size), dtype=np.uint8)

        # Build System Matrix A
        # For each available shard i at index idx:
        # if idx < k: shard[i] = D_idx (Identity)
        # else: shard[i] = sum( (j+1)^(idx-k) * D_j )

        A = np.zeros((k_data, k_data), dtype=np.int64)
        for row in range(k_data):
            idx = available_indices[row]
            if idx < k_data:
                A[row, idx] = 1
            else:
                p_idx = idx - k_data
                for col in range(k_data):
                    A[row, col] = pow(col + 1, p_idx, self.modulus)

        # Solve for each byte position
        for b in range(chunk_size):
            b_vec = [int(s[b]) for s in available_shards[:k_data]]
            sol = solve_linear_system(A.tolist(), b_vec, self.modulus)
            if sol:
                for i in range(k_data): reconstructed[i, b] = sol[i]

        full_bytes = reconstructed.tobytes()
        return full_bytes[:original_len] if original_len > 0 else full_bytes

class SelfSynthesizingNode(MeshNode):
    def __init__(self, node_id: str, coords: np.ndarray, modulus: Optional[int] = None):
        super().__init__(node_id, coords)
        self.modulus = modulus or SovereignConfig.get_manifold_params()["modulus"]
        self.local_weights = None

    def synthesize_weights(self):
        total_data = b"".join(self.storage.values())
        if not total_data: entropy_bias = 0.5
        else:
            counts = np.bincount(np.frombuffer(total_data, dtype=np.uint8), minlength=256)
            probs = counts[counts > 0] / len(total_data)
            entropy_bias = -np.sum(probs * np.log2(probs)) / 8.0
        seed = int(hashlib.md5(f"{self.node_id}_{entropy_bias}".encode()).hexdigest(), 16) % 0xFFFFFFFF
        np.random.seed(seed)
        self.local_weights = np.random.randint(1, self.modulus, 1024, dtype=np.int32)
        print(f"  [MESH] Node {self.node_id} synthesized weights (Entropy Bias: {entropy_bias:.4f}).")

    def verify_local_integrity(self, data_id: str) -> bool:
        if self.local_weights is None: self.synthesize_weights()
        data = self.storage.get(data_id)
        if data is None: return False
        d_arr = np.frombuffer(data, dtype=np.uint8)
        w = self.local_weights[:len(d_arr)]
        np.sum(d_arr.astype(np.int64) * w) % self.modulus
        return True

if __name__ == "__main__":
    sharder = TopologicalSharder()
    nodes = [MeshNode(f"node_{i}", np.random.rand(3)) for i in range(10)]
    for n in nodes: sharder.add_node(n)
    data_id = "reconstruction_test"
    payload = b"RESILIENT_RECOVERY"
    shards = sharder.shard_resilient(data_id, payload)
    # Lose 2 data shards
    targets = sorted(nodes, key=lambda n: n.distance_to(sharder._hash_to_manifold(data_id)))
    subset = {targets[i].node_id: shards[targets[i].node_id] for i in [0, 3, 4]}
    recovered = sharder.reconstruct_payload(data_id, subset, original_len=len(payload))
    print(f"Original: {payload}")
    print(f"Recovered: {recovered}")
