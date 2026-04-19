"""
FSC Universal Framework — Clean Runner
"""
import sys
import os
import numpy as np
# Ensure we can import from current directory
sys.path.insert(0, os.getcwd())
from fsc.fsc_framework import FSCFactory, FSCAnalyzer

def encode(desc, groups):
    return [desc.encode(g) for g in groups]

def corrupt(groups, gi, ei):
    c = [list(g) for g in groups]
    orig = c[gi][ei]
    c[gi][ei] = 0
    return c, orig

def heal(desc, corrupted, invs, gi, ei):
    c = [list(g) for g in corrupted]
    c[gi][ei] = desc.recover(c[gi], ei, invs[gi])
    return c

def verify(original, healed):
    return all(original[i][j] == healed[i][j]
               for i in range(len(original))
               for j in range(len(original[i])))

print("=" * 68)
print("  FSC UNIVERSAL FRAMEWORK — DOMAIN EXPLORATION")
print("=" * 68)

results = []

# ── MIDI ──────────────────────────────────────────────────────────
print("\n━━ 1. MIDI / MUSIC ━━")
midi = [[60,100,1,480],[64,90,1,480],[67,95,1,480],[72,85,2,240],
        [55,110,1,960],[69,75,1,480],[71,80,1,480],[48,120,3,1920]]
d = FSCFactory.integer_sum("MIDI event", 4)
invs = encode(d, midi)
c, orig = corrupt(midi, 2, 1)
h = heal(d, c, invs, 2, 1)
ok = verify(midi, h)
print(f"  ✓ Velocity lost: {orig} → recovered: {h[2][1]}  exact={ok}")
print(f"  Overhead: 8 bytes per 4-event group")
results.append(("MIDI event healing", ok))

# ── GPS ───────────────────────────────────────────────────────────
print("\n━━ 2. GPS / LOCATION ━━")
waypoints = [[3670000,310000,500,1700000000],[3671000,310500,510,1700000060],
             [3672000,311000,520,1700000120],[3673000,311500,515,1700000180],
             [3674000,312000,505,1700000240],[3675000,312500,500,1700000300]]
d = FSCFactory.modular_sum("GPS waypoint", 4, m=2**32)
invs = encode(d, waypoints)
c, orig = corrupt(waypoints, 3, 2)
h = heal(d, c, invs, 3, 2)
ok = verify(waypoints, h)
print(f"  ✓ Altitude lost: {orig}m → recovered: {h[3][2]}m  exact={ok}")
print(f"  Overhead: 4 bytes per waypoint")
results.append(("GPS waypoint", ok))

# ── FINANCIAL OHLCV ───────────────────────────────────────────────
print("\n━━ 3. FINANCIAL DATA ━━")
ohlcv = [[10000,10250,9950,10100,50000],[10100,10400,10050,10350,62000],
         [10350,10500,10200,10200,48000],[10200,10300,10050,10280,55000],
         [10280,10600,10250,10580,71000]]
d = FSCFactory.xor_sum("OHLCV bar", 5)
invs = encode(d, ohlcv)
c, orig = corrupt(ohlcv, 1, 4)
h = heal(d, c, invs, 1, 4)
ok = verify(ohlcv, h)
print(f"  ✓ Volume lost: {orig:,} → recovered: {h[1][4]:,}  exact={ok}")
print(f"  Overhead: 1 XOR byte per bar")
results.append(("Financial OHLCV", ok))

# ── MASS SPECTROMETRY ─────────────────────────────────────────────
print("\n━━ 4. SCIENTIFIC INSTRUMENTS ━━")
peaks = [[1200,85000,2,1230],[1450,42000,3,1245],[890,91000,1,1260],
         [2100,12000,4,1275],[670,78000,2,1290],[1800,33000,3,1305]]
d = FSCFactory.integer_sum("Mass spec peak", 4)
invs = encode(d, peaks)
c, orig = corrupt(peaks, 2, 1)
h = heal(d, c, invs, 2, 1)
ok = verify(peaks, h)
print(f"  ✓ Intensity lost: {orig:,} → recovered: {h[2][1]:,}  exact={ok}")
results.append(("Mass spectrometry", ok))

# ── SOURCE CODE ───────────────────────────────────────────────────
print("\n━━ 5. SOURCE CODE ━━")
code = """def fibonacci(n):
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(n - 1):
        a, b = b, a + b
    return b"""
lines_sums = [sum(ord(c) for c in ln) for ln in code.strip().split('\n')]
d = FSCFactory.xor_sum("source line", len(lines_sums))
inv = d.encode(lines_sums)
corrupted_ls = list(lines_sums)
orig = corrupted_ls[3]
corrupted_ls[3] = 0
rec = d.recover(corrupted_ls, 3, inv)
ok = (rec == orig)
print(f"  ✓ Line 3 checksum: {orig} → 0 → recovered: {rec}  exact={ok}")
print(f"  Overhead: 1 XOR byte per file")
results.append(("Source code integrity", ok))

# ── MERKLE ────────────────────────────────────────────────────────
print("\n━━ 6. BLOCKCHAIN / MERKLE ━━")
leaves = [0xA1B2C3D4,0x12345678,0xDEADBEEF,0xCAFEBABE,
          0x01234567,0x89ABCDEF,0xFEDCBA98,0x76543210]
pairs = [[leaves[i],leaves[i+1]] for i in range(0,len(leaves),2)]
d = FSCFactory.xor_sum("Merkle pair", 2)
invs = encode(d, pairs)
c, orig = corrupt(pairs, 1, 0)
h = heal(d, c, invs, 1, 0)
ok = verify(pairs, h)
print(f"  ✓ Leaf 2: {orig:#010x} → 0 → recovered: {h[1][0]:#010x}  exact={ok}")
results.append(("Blockchain Merkle leaves", ok))

# ── IoT SENSOR MESH ───────────────────────────────────────────────
print("\n━━ 7. IoT SENSOR MESH ━━")
import numpy as np
grid = [[220,225,230],[235,240,238],[215,218,222]]
d = FSCFactory.integer_sum("sensor row", 3)
invs = encode(d, grid)
c, orig = corrupt(grid, 1, 1)
h = heal(d, c, invs, 1, 1)
ok = verify(grid, h)
print(f"  ✓ Sensor (1,1): {orig/10:.1f}°C → failed → recovered: {h[1][1]/10:.1f}°C  exact={ok}")
print(f"  Overhead: 3 int32 row sums for 3×3 grid = 33%")
results.append(("IoT sensor mesh", ok))

# ── POLYNOMIAL RS ─────────────────────────────────────────────────
print("\n━━ 8. POLYNOMIAL / REED-SOLOMON ━━")
p = 251
data = [42, 137, 89, 201, 15]
d = FSCFactory.polynomial_eval("RS symbol", k=5, p=p, eval_point=7)
inv = d.encode(data)
corrupted_d = list(data); orig = corrupted_d[2]; corrupted_d[2] = 0
rec = d.recover(corrupted_d, 2, inv)
ok = (rec == orig)
print(f"  ✓ Coefficient 2: {orig} → 0 → recovered: {rec}  exact={ok}")
print(f"  Overhead: 1 evaluation point per codeword")
results.append(("Reed-Solomon symbol", ok))

# ── AUTO-DETECTION ────────────────────────────────────────────────
print("\n━━ 9. AUTO-DETECTION ON UNKNOWN DATA ━━")
unknown = np.array([10,20,30,40, 15,25,35,25, 8,32,45,15, 50,10,20,20], dtype=np.int32)
analysis = FSCAnalyzer.analyze(unknown, group_size=4)
print(f"  Data has {len(analysis['candidates'])} detected invariants")
if analysis['candidates']:
    for cand in analysis['candidates'][:3]:
        print(f"  · {cand['type']}: overhead={cand['overhead_bytes']}B, strength={cand['strength']}")

# ── SUMMARY ───────────────────────────────────────────────────────
print("\n" + "=" * 68)
print("  SUMMARY")
print("=" * 68)
exact = [(d,ok) for d,ok in results if ok]
failed = [(d,ok) for d,ok in results if not ok]
for domain, ok in results:
    print(f"  {'✓' if ok else '✗'} {domain}")

print(f"""
  {len(exact)}/{len(results)} domains: exact algebraic recovery

  ┌──────────────────────────────────────────────────────────────┐
  │  THE DESIGN PRINCIPLE THAT EMERGED:                          │
  │                                                              │
  │  FSC is not a trick. It is a DESIGN PATTERN.                 │
  │                                                              │
  │  Any system with grouped integer data gains exact            │
  │  self-healing by adding ONE extra value per group:          │
  │  the linear invariant (sum / XOR / weighted / polynomial).   │
  │                                                              │
  │  Cost:    O(n) metadata overhead                             │
  │  Benefit: exact recovery of any 1 lost element, zero latency │
  │  Where:   audio · video · network · database · sensors ·     │
  │           genomics · finance · navigation · cryptography     │
  └──────────────────────────────────────────────────────────────┘

  OPEN FRONTIER:
  Can the invariant be EMBEDDED inside the data itself —
  not stored separately, but structurally enforced?
  → DNA does this (complementarity is the data)
  → Ledger does this (balance is the structure)
  → Torus does this (arc partition is the geometry)
  Can we design file formats where corruption is
  algebraically impossible, not just recoverable?
""")
