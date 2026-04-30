"""
FSC: Forward Sector Correction - Infrastructure Resilience Verification
Copyright (C) 2024 FSC Core Team. All Rights Reserved.
"""

import unittest
import numpy as np
from fsc.enterprise.fsc_infrastructure import SovereignInfrastructure
from fsc.advanced.fsc_mesh import MeshNode

class TestInfraResilience(unittest.TestCase):
    def setUp(self):
        self.infra = SovereignInfrastructure("TEST-INFRA-RESILIENCE")
        self.nodes = [MeshNode(f"node_{i}", np.random.rand(3)) for i in range(5)]
        for n in self.nodes:
            self.infra.add_mesh_node(n)

    def test_config_consensus(self):
        """Verify that infrastructure can coordinate parameter changes."""
        success = self.infra.coordinate_config_change("modulus", 251)
        self.assertTrue(success)

    def test_shard_redistribution_trigger(self):
        """Verify that shard redistribution is triggered on node failure."""
        # Mock one node as unhealthy
        original_health = self.infra.coordinate_node_health()

        # Inject failure (simulation)
        def mock_verify(self, data_id): return False
        import types
        self.infra.nodes[0].verify_local_integrity = types.MethodType(mock_verify, self.infra.nodes[0])

        health = self.infra.coordinate_node_health()
        self.assertFalse(health[self.infra.nodes[0].node_id])

        success = self.infra.redistribute_resilient_shards("critical_data")
        self.assertTrue(success)

if __name__ == "__main__":
    unittest.main()
