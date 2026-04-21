"""
FSC: Forward Sector Correction - Native Acceleration Bridge
"""

import ctypes
import os
import numpy as np
from typing import List, Optional

# Constants from libfsc.h
FSC_SUCCESS      = 1
FSC_ERR_SINGULAR = 0
FSC_ERR_BOUNDS  = -1
FSC_ERR_INVALID = -2

# Load the shared library
_LIB_PATH = os.path.join(os.getcwd(), "libfsc.so")
_lib = None
if os.path.exists(_LIB_PATH):
    try:
        _lib = ctypes.CDLL(_LIB_PATH)
    except Exception as e:
        print(f"[FSC-NATIVE] Warning: Failed to load libfsc.so: {e}")

# Define argument and return types
if _lib:
    # int64_t fsc_calculate_sum8(const uint8_t* data, const int32_t* weights, size_t n, int64_t modulus)
    _lib.fsc_calculate_sum8.argtypes = [
        ctypes.POINTER(ctypes.c_uint8),
        ctypes.POINTER(ctypes.c_int32),
        ctypes.c_size_t,
        ctypes.c_int64
    ]
    _lib.fsc_calculate_sum8.restype = ctypes.c_int64

    # uint8_t fsc_heal_single8(const uint8_t* data, const int32_t* weights, size_t n, int64_t target, int64_t modulus, size_t corrupted_idx)
    _lib.fsc_heal_single8.argtypes = [
        ctypes.POINTER(ctypes.c_uint8),
        ctypes.POINTER(ctypes.c_int32),
        ctypes.c_size_t,
        ctypes.c_int64,
        ctypes.c_int64,
        ctypes.c_size_t
    ]
    _lib.fsc_heal_single8.restype = ctypes.c_uint8

    # int64_t fsc_calculate_sum64(const int64_t* data, const int32_t* weights, size_t n, int64_t modulus)
    _lib.fsc_calculate_sum64.argtypes = [
        ctypes.POINTER(ctypes.c_int64),
        ctypes.POINTER(ctypes.c_int32),
        ctypes.c_size_t,
        ctypes.c_int64
    ]
    _lib.fsc_calculate_sum64.restype = ctypes.c_int64

    # int64_t fsc_heal_single64(const int64_t* data, const int32_t* weights, size_t n, int64_t target, int64_t modulus, size_t corrupted_idx)
    _lib.fsc_heal_single64.argtypes = [
        ctypes.POINTER(ctypes.c_int64),
        ctypes.POINTER(ctypes.c_int32),
        ctypes.c_size_t,
        ctypes.c_int64,
        ctypes.c_int64,
        ctypes.c_size_t
    ]
    _lib.fsc_heal_single64.restype = ctypes.c_int64

    # int fsc_heal_multi64(...)
    _lib.fsc_heal_multi64.argtypes = [
        ctypes.POINTER(ctypes.c_int64),
        ctypes.POINTER(ctypes.c_int32),
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_int64),
        ctypes.POINTER(ctypes.c_int64),
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_size_t)
    ]
    _lib.fsc_heal_multi64.restype = ctypes.c_int

    # int fsc_heal_multi8(...)
    _lib.fsc_heal_multi8.argtypes = [
        ctypes.POINTER(ctypes.c_uint8),
        ctypes.POINTER(ctypes.c_int32),
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_int64),
        ctypes.POINTER(ctypes.c_int64),
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_size_t)
    ]
    _lib.fsc_heal_multi8.restype = ctypes.c_int

    # void fsc_audit_log(const char* event_type, int index, int64_t magnitude)
    _lib.fsc_audit_log.argtypes = [
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_int64
    ]
    _lib.fsc_audit_log.restype = None

def is_native_available() -> bool:
    return _lib is not None

def native_calculate_sum8(data: np.ndarray, weights: Optional[np.ndarray], modulus: int) -> int:
    if not _lib: raise RuntimeError("Native library not loaded")
    data_ptr = data.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))
    weights_ptr = weights.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)) if weights is not None else None
    return _lib.fsc_calculate_sum8(data_ptr, weights_ptr, len(data), modulus)

def native_calculate_sum64(data: np.ndarray, weights: Optional[np.ndarray], modulus: int) -> int:
    if not _lib: raise RuntimeError("Native library not loaded")
    data_ptr = data.ctypes.data_as(ctypes.POINTER(ctypes.c_int64))
    weights_ptr = weights.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)) if weights is not None else None
    return _lib.fsc_calculate_sum64(data_ptr, weights_ptr, len(data), modulus)

def native_heal_single64(data: np.ndarray, weights: Optional[np.ndarray], target: int, modulus: int, corrupted_idx: int) -> int:
    if not _lib: raise RuntimeError("Native library not loaded")
    data_ptr = data.ctypes.data_as(ctypes.POINTER(ctypes.c_int64))
    weights_ptr = weights.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)) if weights is not None else None
    return _lib.fsc_heal_single64(data_ptr, weights_ptr, len(data), target, modulus, corrupted_idx)

def native_heal_multi64(data: np.ndarray, weights: Optional[np.ndarray],
                       targets: np.ndarray, moduli: np.ndarray,
                       corrupted_indices: List[int]) -> bool:
    if not _lib: raise RuntimeError("Native library not loaded")
    data_ptr = data.ctypes.data_as(ctypes.POINTER(ctypes.c_int64))
    weights_ptr = weights.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)) if weights is not None else None
    targets_ptr = targets.ctypes.data_as(ctypes.POINTER(ctypes.c_int64))
    moduli_ptr = moduli.ctypes.data_as(ctypes.POINTER(ctypes.c_int64))
    ci_array = (ctypes.c_size_t * len(corrupted_indices))(*corrupted_indices)
    res = _lib.fsc_heal_multi64(data_ptr, weights_ptr, len(data),
                                targets_ptr, moduli_ptr,
                                len(corrupted_indices), ci_array)
    return res == FSC_SUCCESS

def native_heal_multi8(data: np.ndarray, weights: Optional[np.ndarray],
                      targets: np.ndarray, moduli: np.ndarray,
                      corrupted_indices: List[int]) -> bool:
    if not _lib: raise RuntimeError("Native library not loaded")
    data_ptr = data.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))
    weights_ptr = weights.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)) if weights is not None else None
    targets_ptr = targets.ctypes.data_as(ctypes.POINTER(ctypes.c_int64))
    moduli_ptr = moduli.ctypes.data_as(ctypes.POINTER(ctypes.c_int64))
    ci_array = (ctypes.c_size_t * len(corrupted_indices))(*corrupted_indices)
    res = _lib.fsc_heal_multi8(data_ptr, weights_ptr, len(data),
                               targets_ptr, moduli_ptr,
                               len(corrupted_indices), ci_array)
    return res == FSC_SUCCESS

def native_audit_log(event_type: str, index: int, magnitude: int):
    if not _lib: return
    _lib.fsc_audit_log(event_type.encode(), index, magnitude)
