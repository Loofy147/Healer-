import numpy as np
import unittest
from fsc.fsc_native import is_native_available
from fsc.fsc_silicon import FSCSiliconBlackbox
from fsc.fsc_quantum import LatticeIntegrity

class TestAdvancedHorizons(unittest.TestCase):
    def test_horizon_4_gals(self):
        print("Testing Horizon 4: GALS Silicon Simulation...")
        bb = FSCSiliconBlackbox()
        sig = np.full(200, 42, dtype=np.uint8)
        # Calculate target using same weights as silicon core (1, 2, ...)
        weights = np.arange(1, 201, dtype=np.uint8)
        target = int(np.sum(sig.astype(np.int64) * weights) % 251)

        res = bb.process_signal(sig, target)
        self.assertEqual(res, "HARDWARE_VERIFIED")

        # Corrupt
        sig[10] ^= 0xAA
        res = bb.process_signal(sig, target)
        self.assertEqual(res, "HEALED_IN_SILICON")
        # Verify it was healed
        new_target = int(np.sum(sig.astype(np.int64) * weights) % 251)
        self.assertEqual(new_target, target)
        print("✓ Horizon 4 Verified")

    def test_horizon_5_quantum(self):
        print("Testing Horizon 5: Post-Quantum Lattice integrity...")
        lat = LatticeIntegrity(n=256, q=12289)
        data = np.random.randint(0, 256, 128)
        seal = lat.create_seal(data)

        self.assertTrue(lat.verify_seal(data, seal))

        # Minor bit flip
        data[0] = (data[0] + 1) % 256
        self.assertFalse(lat.verify_seal(data, seal))
        print("✓ Horizon 5 Verified")

    def test_simd_overflow_fix(self):
        print("Verifying SIMD 64-bit product correctness for large blocks...")
        if not is_native_available():
            self.skipTest("Native library not available")

        from fsc.fsc_native import _lib
        import ctypes
        fsc_block_seal = _lib.fsc_block_seal
        fsc_block_seal.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t, ctypes.c_int64, ctypes.c_int64]

        from fsc.fsc_native import native_batch_verify_model5

        # 64KB block
        size = 65536
        block = np.zeros(size, dtype=np.uint8)
        block_ptr = block.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))

        # Seal it (calculates s1, s2, s3)
        fsc_block_seal(block_ptr, size, 0, 251)

        # Verify it
        corrupted = native_batch_verify_model5(block, 1, size, 251)
        self.assertEqual(len(corrupted), 0, "SIMD verification failed for large block")
        print("✓ SIMD 64-bit Fix Verified")

if __name__ == "__main__":
    unittest.main()
