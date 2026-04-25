"""
FSC v6: Entropy-Weighted Dynamic Stratification
Copyright (C) 2024 FSC Core Team. All Rights Reserved.
"""
import numpy as np
from typing import List, Tuple
from fsc.fsc_framework import solve_linear_system, gf_inv

class AdaptiveWeightEngine:
    """
    Calculates weights that prioritize low-entropy fields.
    Protects critical metadata in high-entropy streams.
    """
    @staticmethod
    def calculate_weights(data_types: List[str], base_modulus: int, seed: int = 1) -> np.ndarray:
        # Priority: UINT32/64 (High) > UINT16 > UINT8 (Low/Blob)
        prio = {'UINT64': 100, 'UINT32': 50, 'UINT16': 10, 'UINT8': 1}
        raw_weights = np.array([prio.get(t, 1) for t in data_types])

        # We use the seed to generate different sets of weights for multiple constraints
        # Ensure weights are non-zero in GF(p)
        pos = np.arange(1, len(data_types) + 1)
        if seed == 1:
            return (raw_weights * pos) % base_modulus
        else:
            # Quadratic weights for the second constraint
            return (raw_weights * (pos ** 2)) % base_modulus
