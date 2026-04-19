import numpy as np
from fsc.fsc_framework import FSCFactory, FSCHealer
import time

def demo_ambisonics():
    print("━━ PROTOTYPE: AMBISONIC AUDIO (4-CH) ━━")
    num_samples = 100000
    S = np.random.randint(-32768, 32767, num_samples)
    theta, phi = np.radians(45), np.radians(0)
    W = (S * 0.707).astype(np.int16)
    X = (S * np.cos(theta) * np.cos(phi)).astype(np.int16)
    Y = (S * np.sin(theta) * np.cos(phi)).astype(np.int16)
    Z = (S * np.sin(phi)).astype(np.int16)
    data = np.vstack([W, X, Y, Z]).T

    desc = FSCFactory.integer_sum("Ambisonic Sample", 4)
    healer = FSCHealer(desc)

    t0 = time.time()
    # Flatten using numpy for speed then list
    flat_data = data.ravel().tolist()
    groups, invariants = healer.encode_stream(flat_data)
    t1 = time.time()
    print(f"  Encoded {num_samples} samples in {t1-t0:.4f}s")

    corrupted_groups = [list(g) for g in groups]
    for g in corrupted_groups: g[2] = 0
    loss_mask = [(i, 2) for i in range(num_samples)]

    t0 = time.time()
    healed_groups, n_recovered = healer.heal_stream(corrupted_groups, invariants, loss_mask)
    t1 = time.time()
    print(f"  Healed {num_samples} samples in {t1-t0:.4f}s")

    verification = healer.verify(groups, healed_groups)
    print(f"  Exact Algebraic Recovery: {verification['perfect']}")

if __name__ == "__main__":
    demo_ambisonics()
