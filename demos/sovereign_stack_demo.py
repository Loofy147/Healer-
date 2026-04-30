"""
FSC: Forward Sector Correction - Sovereign Infrastructure Integration Demo
Copyright (C) 2024 FSC Core Team. All Rights Reserved.
"""

import numpy as np
from fsc.enterprise.fsc_infrastructure import SovereignInfrastructure
from fsc.storage.fsc_block import FSCVolume
from fsc.advanced.fsc_mesh import MeshNode
from fsc.enterprise.fsc_config import SovereignConfig

def run_integration_demo():
    print("━━━ SOVEREIGN INFRASTRUCTURE INTEGRATION DEMO ━━━")

    # 1. Initialize Infrastructure
    infra = SovereignInfrastructure("DEMO-INFRA-1")
    params = SovereignConfig.get_manifold_params("CORE")

    # 2. Setup Storage Volume
    # Ensure volume is initialized (blocks verified)
    vol = FSCVolume(n_blocks=10, block_size=64, modulus=params['modulus'])
    vol.write_volume(b"INITIAL_DATA_FOR_ALIGNMENT")
    infra.register_volume("primary_vol", vol)

    # 3. Setup Distributed Mesh Nodes
    nodes = [MeshNode(f"node_{i}", np.random.rand(3)) for i in range(3)]
    for node in nodes:
        infra.add_mesh_node(node)

    print(f"\n[DEMO] Infrastructure initialized with {len(infra.volumes)} volume and {len(infra.nodes)} nodes.")

    # 4. Orchestrate Health
    print("\n[DEMO] Starting infrastructure orchestration...")
    status = infra.manage_distributed_infrastructure()

    print(f"\n[DEMO] Orchestration Report:")
    for v in status['volumes']:
        print(f"  - Volume '{v['volume_id']}': Status={v['status']} (Latent Errors Found: {v['audit_details'].get('latent_errors', 0)})")

    print(f"  - Nodes Health: {status['nodes']}")
    print(f"  - System Uptime: {status['uptime']:.4f}s")

    print("\n━━━ DEMO COMPLETE ━━━")

if __name__ == "__main__":
    run_integration_demo()
