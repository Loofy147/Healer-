
## 2024-04-21 - Native Bridge Security Hardening
**Vulnerability:** Lack of bounds checking and modulus validation in native C acceleration library (libfsc.so).
**Learning:** High-performance C code often omits safety checks for speed, assuming the caller (Python bridge) performs them. However, defense-in-depth requires validation at both layers to prevent memory corruption or crashes if the bridge is bypassed or misconfigured.
**Prevention:** Always validate array indices against buffer lengths and ensure divisors (moduli) are non-zero/positive before passing to native code or performing modular arithmetic.
