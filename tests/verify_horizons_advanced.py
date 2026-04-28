import numpy as np
import unittest
from fsc.fsc_native import is_native_available
from fsc.fsc_silicon import FSCSiliconBlackbox
from fsc.fsc_quantum import LatticeIntegrity

class TestAdvancedHorizons(unittest.TestCase):
    def test_horizon_4_silicon_security(self):
        print("Testing Horizon 4: Silicon eFuse & PUF...")
        bb = FSCSiliconBlackbox(device_id="DEV_X")
        self.assertFalse(bb._is_locked)
        bb.lock_hardware()
        self.assertTrue(bb._is_locked)
        self.assertTrue(bb._core.efuse.is_blown(0))

        # Test PUF uniqueness
        nonce = b"challenge_001"
        sig1 = bb.get_integrity_signature(nonce)
        bb2 = FSCSiliconBlackbox(device_id="DEV_Y")
        sig2 = bb2.get_integrity_signature(nonce)
        self.assertNotEqual(sig1, sig2, "PUF signatures must be device-unique")
        print("✓ Horizon 4 Silicon Security Verified")

    def test_horizon_5_quantum(self):
        print("Testing Horizon 5: Post-Quantum Lattice integrity...")
        lat = LatticeIntegrity(n=256, q=12289)
        data = np.random.randint(0, 256, 128)
        seal = lat.create_seal(data)
        self.assertTrue(lat.verify_seal(data, seal))
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
        size = 65536
        block = np.zeros(size, dtype=np.uint8)
        fsc_block_seal(block.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)), size, 0, 251)
        corrupted = native_batch_verify_model5(block, 1, size, 251)
        self.assertEqual(len(corrupted), 0)
        print("✓ SIMD 64-bit Fix Verified")

if __name__ == "__main__":
    unittest.main()
