"""
FSC Prototype: Ambisonic Audio Self-Healing
===========================================
In a 4-channel Ambisonic system (W, X, Y, Z), if the channels are derived
from a single source or a known set of sources, they maintain a linear
relationship. This prototype demonstrates exact recovery of a lost channel
(e.g., due to packet loss or speaker failure) using a per-sample invariant.
"""

import numpy as np
from fsc_framework import FSCFactory, FSCHealer

def demo_ambisonics():
    print("━━ PROTOTYPE: AMBISONIC AUDIO (4-CH) ━━")

    # 1. Simulate 4-channel Ambisonic data (W, X, Y, Z)
    # W (omni), X (front-back), Y (left-right), Z (up-down)
    # For a simple source at (theta, phi):
    # W = S * 0.707
    # X = S * cos(theta) * cos(phi)
    # Y = S * sin(theta) * cos(phi)
    # Z = S * sin(phi)

    num_samples = 1000
    S = np.random.randint(-32768, 32767, num_samples)
    theta = np.radians(45)
    phi = np.radians(0)

    W = (S * 0.707).astype(np.int16)
    X = (S * np.cos(theta) * np.cos(phi)).astype(np.int16)
    Y = (S * np.sin(theta) * np.cos(phi)).astype(np.int16)
    Z = (S * np.sin(phi)).astype(np.int16)

    data = np.vstack([W, X, Y, Z]).T # Shape (1000, 4)

    # 2. Add FSC Protection
    desc = FSCFactory.integer_sum("Ambisonic Sample", 4)
    healer = FSCHealer(desc)
    groups, invariants = healer.encode_stream(data.flatten().tolist())

    # 3. Simulate Channel Loss (e.g., Speaker 'Y' fails)
    # Each group is one sample [W, X, Y, Z]
    corrupted_groups = [list(g) for g in groups]
    for g in corrupted_groups:
        g[2] = 0 # Channel Y lost

    # 4. Recover
    loss_mask = [(i, 2) for i in range(num_samples)]
    healed_groups, n_recovered = healer.heal_stream(corrupted_groups, invariants, loss_mask)

    # 5. Verify
    verification = healer.verify(groups, healed_groups)
    print(f"Samples Processed: {num_samples}")
    print(f"Channels Recovered: {n_recovered}")
    print(f"Exact Algebraic Recovery: {verification['perfect']}")

    if verification['perfect']:
        print("✓ SUCCESS: Ambisonic channel 'Y' recovered with zero distortion.")

if __name__ == "__main__":
    demo_ambisonics()
