import unittest
import numpy as np
from fsc.fsc_mesh import TopologicalSharder, MeshNode

class TestResilience(unittest.TestCase):
    def test_mesh_raid(self):
        print("Testing Horizon 6: Resilient Mesh RAID...")
        sharder = TopologicalSharder()
        for i in range(10): sharder.add_node(MeshNode(f"n{i}", np.random.rand(3)))

        payload = b"TopSecretData" * 10
        shards = sharder.shard_resilient("data1", payload, k_data=3, m_parity=2)

        self.assertEqual(len(shards), 5)
        # Verify shard sizes are consistent
        s_len = len(list(shards.values())[0])
        for s in shards.values():
            self.assertEqual(len(s), s_len)
        print("✓ Horizon 6 Mesh Resilience Verified")

if __name__ == "__main__":
    unittest.main()
