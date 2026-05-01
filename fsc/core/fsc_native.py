import ctypes
import os
import numpy as np
from typing import List, Optional, Tuple

FSC_SUCCESS = 1
FSC_ERR_SINGULAR = 0
FSC_ERR_BOUNDS = -1
FSC_ERR_INVALID = -2

_lib = None
try:
    _lib_path = os.path.join(os.getcwd(), "libfsc.so")
    _lib = ctypes.CDLL(_lib_path)

    _lib.fsc_calculate_sum8.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(ctypes.c_int32), ctypes.c_size_t, ctypes.c_int64]
    _lib.fsc_calculate_sum8.restype = ctypes.c_int64

    _lib.fsc_heal_single8.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(ctypes.c_int32), ctypes.c_size_t, ctypes.c_int64, ctypes.c_int64, ctypes.c_size_t]
    _lib.fsc_heal_single8.restype = ctypes.c_uint8

    _lib.fsc_calculate_sum64.argtypes = [ctypes.POINTER(ctypes.c_int64), ctypes.POINTER(ctypes.c_int32), ctypes.c_size_t, ctypes.c_int64]
    _lib.fsc_calculate_sum64.restype = ctypes.c_int64

    _lib.fsc_heal_single64.argtypes = [ctypes.POINTER(ctypes.c_int64), ctypes.POINTER(ctypes.c_int32), ctypes.c_size_t, ctypes.c_int64, ctypes.c_int64, ctypes.c_size_t]
    _lib.fsc_heal_single64.restype = ctypes.c_int64

    _lib.fsc_heal_multi64.argtypes = [ctypes.POINTER(ctypes.c_int64), ctypes.POINTER(ctypes.c_int32), ctypes.c_size_t, ctypes.POINTER(ctypes.c_int64), ctypes.POINTER(ctypes.c_int64), ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
    _lib.fsc_heal_multi64.restype = ctypes.c_int

    _lib.fsc_heal_multi8.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(ctypes.c_int32), ctypes.c_size_t, ctypes.POINTER(ctypes.c_int64), ctypes.POINTER(ctypes.c_int64), ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
    _lib.fsc_heal_multi8.restype = ctypes.c_int

    _lib.fsc_batch_verify_model5.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t, ctypes.c_size_t, ctypes.c_int64, ctypes.POINTER(ctypes.c_size_t)]
    _lib.fsc_batch_verify_model5.restype = ctypes.c_size_t

    _lib.fsc_heal_erasure8.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t, ctypes.c_size_t, ctypes.c_size_t, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t), ctypes.c_int64]
    _lib.fsc_heal_erasure8.restype = ctypes.c_int

    _lib.fsc_audit_log.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int64]
    _lib.fsc_audit_log.restype = None

    _lib.fsc_volume_encode8.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t, ctypes.c_size_t, ctypes.c_size_t, ctypes.c_int64]
    _lib.fsc_volume_encode8.restype = ctypes.c_int

    _lib.fsc_volume_write8.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t, ctypes.c_size_t, ctypes.c_size_t, ctypes.c_int64, ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t]
    _lib.fsc_volume_write8.restype = ctypes.c_int

    _lib.fsc_silicon_verify_gate.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t, ctypes.c_int64, ctypes.c_int64]
    _lib.fsc_silicon_verify_gate.restype = ctypes.c_int

    _lib.fsc_block_seal.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t, ctypes.c_int64, ctypes.c_int64]
    _lib.fsc_block_seal.restype = ctypes.c_int

    _lib.fsc_block_verify.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t, ctypes.c_int64, ctypes.c_int64]
    _lib.fsc_block_verify.restype = ctypes.c_int

    _lib.fsc_poly_mul_avx2.argtypes = [ctypes.POINTER(ctypes.c_int64), ctypes.POINTER(ctypes.c_int64), ctypes.POINTER(ctypes.c_int64), ctypes.c_size_t, ctypes.c_int64]
    _lib.fsc_poly_mul_avx2.restype = None

except Exception as e:
    print(f"Warning: libfsc not loaded: {e}")

def is_native_available() -> bool: return _lib is not None

def native_calculate_sum8(data: np.ndarray, weights: Optional[np.ndarray], modulus: int) -> int:
    if not _lib: raise RuntimeError("Native library not loaded")
    return _lib.fsc_calculate_sum8(data.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)), weights.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)) if weights is not None else None, len(data), modulus)

def native_heal_single8(data: np.ndarray, weights: Optional[np.ndarray], target: int, modulus: int, corrupted_idx: int) -> int:
    if not _lib: raise RuntimeError("Native library not loaded")
    return _lib.fsc_heal_single8(data.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)), weights.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)) if weights is not None else None, len(data), target, modulus, corrupted_idx)

def native_calculate_sum64(data: np.ndarray, weights: Optional[np.ndarray], modulus: int) -> int:
    if not _lib: raise RuntimeError("Native library not loaded")
    return _lib.fsc_calculate_sum64(data.ctypes.data_as(ctypes.POINTER(ctypes.c_int64)), weights.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)) if weights is not None else None, len(data), modulus)

def native_heal_single64(data: np.ndarray, weights: Optional[np.ndarray], target: int, modulus: int, corrupted_idx: int) -> int:
    if not _lib: raise RuntimeError("Native library not loaded")
    return _lib.fsc_heal_single64(data.ctypes.data_as(ctypes.POINTER(ctypes.c_int64)), weights.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)) if weights is not None else None, len(data), target, modulus, corrupted_idx)

def native_heal_multi64(data: np.ndarray, weights: Optional[np.ndarray], targets: np.ndarray, moduli: np.ndarray, corrupted_indices: List[int]) -> bool:
    if not _lib: raise RuntimeError("Native library not loaded")
    ci_array = (ctypes.c_size_t * len(corrupted_indices))(*corrupted_indices)
    return _lib.fsc_heal_multi64(data.ctypes.data_as(ctypes.POINTER(ctypes.c_int64)), weights.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)) if weights is not None else None, len(data), targets.ctypes.data_as(ctypes.POINTER(ctypes.c_int64)), moduli.ctypes.data_as(ctypes.POINTER(ctypes.c_int64)), len(corrupted_indices), ci_array) == FSC_SUCCESS

def native_heal_multi8(data: np.ndarray, weights: Optional[np.ndarray], targets: np.ndarray, moduli: np.ndarray, corrupted_indices: List[int]) -> bool:
    if not _lib: raise RuntimeError("Native library not loaded")
    ci_array = (ctypes.c_size_t * len(corrupted_indices))(*corrupted_indices)
    return _lib.fsc_heal_multi8(data.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)), weights.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)) if weights is not None else None, len(data), targets.ctypes.data_as(ctypes.POINTER(ctypes.c_int64)), moduli.ctypes.data_as(ctypes.POINTER(ctypes.c_int64)), len(corrupted_indices), ci_array) == FSC_SUCCESS

def native_batch_verify_model5(data: np.ndarray, n_blocks: int, block_size: int, modulus: int) -> List[int]:
    if not _lib: raise RuntimeError("Native library not loaded")
    corrupted_array = (ctypes.c_size_t * n_blocks)()
    count = _lib.fsc_batch_verify_model5(data.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)), n_blocks, block_size, modulus, corrupted_array)
    return [corrupted_array[i] for i in range(count)]

def native_heal_erasure8(volume_data: np.ndarray, n_blocks: int, block_size: int, k_parity: int, bad_indices: List[int], modulus: int) -> bool:
    if not _lib: raise RuntimeError("Native library not loaded")
    bad_array = (ctypes.c_size_t * len(bad_indices))(*bad_indices)
    return _lib.fsc_heal_erasure8(volume_data.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)), n_blocks, block_size, k_parity, len(bad_indices), bad_array, modulus) == FSC_SUCCESS

def native_audit_log(event_type: str, index: int, magnitude: int):
    if _lib: _lib.fsc_audit_log(event_type.encode(), index, magnitude)

def native_volume_encode8(volume_data: np.ndarray, n_blocks: int, block_size: int, k_parity: int, modulus: int) -> bool:
    if not _lib: raise RuntimeError("Native library not loaded")
    return _lib.fsc_volume_encode8(volume_data.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)), n_blocks, block_size, k_parity, modulus) == FSC_SUCCESS

def native_volume_write8(volume_data: np.ndarray, n_blocks: int, block_size: int, k_parity: int, modulus: int, user_data: bytes) -> bool:
    if not _lib: raise RuntimeError("Native library not loaded")
    ud_array = (ctypes.c_uint8 * len(user_data)).from_buffer_copy(user_data)
    return _lib.fsc_volume_write8(volume_data.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)), n_blocks, block_size, k_parity, modulus, ud_array, len(user_data)) == FSC_SUCCESS

def native_silicon_verify_gate(data: np.ndarray, rom_weights: np.ndarray, target: int, modulus: int) -> bool:
    if not _lib: raise RuntimeError("Native library not loaded")
    return _lib.fsc_silicon_verify_gate(data.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)), rom_weights.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)), len(data), target, modulus) != 0

def native_block_seal(block: np.ndarray, block_id: int, modulus: int) -> bool:
    if not _lib: raise RuntimeError("Native library not loaded")
    return _lib.fsc_block_seal(block.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)), len(block), block_id, modulus) == FSC_SUCCESS

def native_block_verify(block: np.ndarray, block_id: int, modulus: int) -> bool:
    if not _lib: raise RuntimeError("Native library not loaded")
    return _lib.fsc_block_verify(block.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)), len(block), block_id, modulus) != 0

def native_poly_mul(a: np.ndarray, b: np.ndarray, q: int) -> np.ndarray:
    if not _lib: raise RuntimeError("Native library not loaded")
    n = len(a)
    res = np.zeros(n, dtype=np.int64)
    _lib.fsc_poly_mul_avx2(a.ctypes.data_as(ctypes.POINTER(ctypes.c_int64)), b.ctypes.data_as(ctypes.POINTER(ctypes.c_int64)), res.ctypes.data_as(ctypes.POINTER(ctypes.c_int64)), n, q)
    return res
