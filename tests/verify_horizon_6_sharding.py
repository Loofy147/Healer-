import unittest
import numpy as np
from fsc.fsc_mesh import TopologicalSharder, MeshNode

class TestHorizon6(unittest.TestCase):
    def test_topological_sharding(self):
        print("Testing Horizon 6: Topological Sharding...")
        sharder = TopologicalSharder(dimension=3)
        # Add 100 nodes to ensure good distribution
        for i in range(100):
            sharder.add_node(MeshNode(f"node_{i}", np.random.rand(3)))

        data_id = "test_object_001"
        targets = sharder.get_target_nodes(data_id, k=3)

        self.assertEqual(len(targets), 3)
        # Ensure consistency: same data_id should yield same targets
        targets_again = sharder.get_target_nodes(data_id, k=3)
        self.assertEqual([n.node_id for n in targets], [n.node_id for n in targets_again])

        # Verify distance property
        manifold_pt = sharder._hash_to_manifold(data_id)
        dists = [n.distance_to(manifold_pt) for n in targets]
        self.assertTrue(all(dists[i] <= dists[i+1] for i in range(len(dists)-1)))
        print("✓ Horizon 6 Topological Sharding Verified")

if __name__ == "__main__":
    unittest.main()
