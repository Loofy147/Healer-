import numpy as np
from fsc.fsc_native import native_batch_verify_model5, is_native_available
import ctypes

def test_large_block_verification():
    if not is_native_available():
        print("Native library not available, skipping.")
        return

    from fsc.fsc_native import _lib
    # int fsc_block_seal(uint8_t* block, size_t block_size, int64_t block_id, int64_t modulus)
    fsc_block_seal = _lib.fsc_block_seal
    fsc_block_seal.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t, ctypes.c_int64, ctypes.c_int64]
    fsc_block_seal.restype = ctypes.c_int

    print("Testing SIMD verification for large blocks (64KB)...")
    block_size = 65536
    n_blocks = 5
    modulus = 251

    data = np.zeros(n_blocks * block_size, dtype=np.uint8)

    for i in range(n_blocks):
        block_ptr = data[i*block_size : (i+1)*block_size].ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))
        fsc_block_seal(block_ptr, block_size, i, modulus)

    corrupted = native_batch_verify_model5(data, n_blocks, block_size, modulus)
    print(f"Valid blocks corrupted indices: {corrupted}")
    assert len(corrupted) == 0, "Valid zero blocks failed verification"

    # Corrupt one block
    data[block_size + 10] ^= 0xFF
    corrupted = native_batch_verify_model5(data, n_blocks, block_size, modulus)
    print(f"After corruption, indices: {corrupted}")
    assert 1 in corrupted, "Failed to detect corruption in large block"

    print("✓ Large block SIMD verification successful")

if __name__ == "__main__":
    test_large_block_verification()
