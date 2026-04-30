import importlib
import os
import sys
import ctypes

def check_package(package_name):
    try:
        importlib.import_module(package_name)
        print(f"[OK] Package '{package_name}' is installed.")
        return True
    except ImportError:
        print(f"[FAIL] Package '{package_name}' is NOT installed.")
        return False

def check_native_library():
    lib_path = "./libfsc.so"
    if os.path.exists(lib_path):
        print(f"[OK] Native library '{lib_path}' exists.")
        try:
            ctypes.CDLL(lib_path)
            print(f"[OK] Native library '{lib_path}' can be loaded.")
            return True
        except Exception as e:
            print(f"[FAIL] Native library '{lib_path}' exists but cannot be loaded: {e}")
            return False
    else:
        print(f"[FAIL] Native library '{lib_path}' does NOT exist.")
        return False

if __name__ == "__main__":
    packages = ["numpy", "mnemonic", "solders", "PIL"]
    all_ok = True

    print("--- FSC Environment Verification ---")
    for pkg in packages:
        if not check_package(pkg):
            all_ok = False

    if not check_native_library():
        all_ok = False

    print("------------------------------------")
    if all_ok:
        print("Environment is READY.")
        sys.exit(0)
    else:
        print("Environment is INCOMPLETE.")
        sys.exit(1)
