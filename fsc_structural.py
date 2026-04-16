"""
Structural FSC — Algebraic Type System
========================================
Designing data formats where the invariant IS the structure.

A format is FSC-structural iff its validity predicate implies a linear
integer constraint on its fields. Then:
  validity checking = corruption detection
  validity repair   = algebraic recovery
No external metadata needed — the format IS the invariant.
"""

from __future__ import annotations
from typing import Any, Callable, List, Optional, Tuple, Set
from abc import ABC, abstractmethod


# ══════════════════════════════════════════════════════════════════
# ABSTRACT BASE: STRUCTURAL FSC TYPE
# ══════════════════════════════════════════════════════════════════

class StructuralFSCType(ABC):
    """
    Base class for data types that embed a linear invariant.
    """
    @abstractmethod
    def valid(self) -> bool:
        """True if the instance satisfies its structural invariant."""
        pass

    @abstractmethod
    def recover(self, corrupted_field_idx: int) -> 'StructuralFSCType':
        """Recover a new valid instance by repairing the specified field."""
        pass


# ══════════════════════════════════════════════════════════════════
# MODEL 1: COMPLEMENT PAIR (DNA style)
# ══════════════════════════════════════════════════════════════════

class ComplementPair(StructuralFSCType):
    """
    Type where validity is defined by an involution f: f(primary) == complement.
    Used for DNA (A-T, G-C), differential signaling, and mirrors.
    """
    def __init__(self, primary: Any, complement_fn: Callable, inverse_fn: Optional[Callable] = None):
        self.primary = primary
        self.complement_fn = complement_fn
        self.inverse_fn = inverse_fn or complement_fn
        # The structure enforces that we store the "correct" complement at creation
        self._stored_complement = complement_fn(primary)

    def corrupt_primary(self, bad_value: Any) -> 'ComplementPair':
        """Simulate corruption of the primary field."""
        obj = ComplementPair.__new__(ComplementPair)
        obj.primary = bad_value
        obj.complement_fn = self.complement_fn
        obj.inverse_fn = self.inverse_fn
        obj._stored_complement = self._stored_complement
        return obj

    def valid(self) -> bool:
        try:
            return self.complement_fn(self.primary) == self._stored_complement
        except Exception:
            return False

    def recover(self, corrupted_field_idx: int) -> 'ComplementPair':
        if corrupted_field_idx == 0:
            # Recover primary from complement
            new_p = self.inverse_fn(self._stored_complement)
            return ComplementPair(new_p, self.complement_fn, self.inverse_fn)
        # If complement is corrupted, we just return a new valid pair from current primary
        return ComplementPair(self.primary, self.complement_fn, self.inverse_fn)

    def __repr__(self):
        return f"ComplementPair({'✓' if self.valid() else '✗'} p={self.primary}, c={self._stored_complement})"


# ══════════════════════════════════════════════════════════════════
# MODEL 2: PARTITION RECORD (Torus style)
# ══════════════════════════════════════════════════════════════════

class PartitionRecord(StructuralFSCType):
    """
    Type where fields must form a partition of a fixed universe.
    Used in graph embeddings where vertex arcs must use all available colors.
    """
    def __init__(self, universe: Set[Any], field_values: List[Set[Any]]):
        self.universe = universe
        self.field_values = [set(v) for v in field_values]

    def valid(self) -> bool:
        union = set()
        for fv in self.field_values:
            if union & fv: return False # Not disjoint
            union |= fv
        return union == self.universe # Must cover universe

    def recover(self, corrupted_field_idx: int) -> 'PartitionRecord':
        # missing = universe - union(other fields)
        others = set().union(*[fv for i, fv in enumerate(self.field_values) if i != corrupted_field_idx])
        new_fields = [set(fv) for fv in self.field_values]
        new_fields[corrupted_field_idx] = self.universe - others
        return PartitionRecord(self.universe, new_fields)

    def corrupt_field(self, idx: int, bad_val: Any) -> 'PartitionRecord':
        new_fields = [set(fv) for fv in self.field_values]
        new_fields[idx] = {bad_val}
        return PartitionRecord(self.universe, new_fields)


# ══════════════════════════════════════════════════════════════════
# MODEL 3: BALANCED GROUP (Ledger style)
# ══════════════════════════════════════════════════════════════════

class BalancedGroup(StructuralFSCType):
    """
    Type where a weighted sum of fields equals a fixed target.
    Used in double-entry bookkeeping and physical conservation laws.
    """
    def __init__(self, values: List[int], weights: List[int], target: int, modulus: Optional[int] = None):
        self.values = list(values)
        self.weights = list(weights)
        self.target = target
        self.modulus = modulus

    def _eval(self, vals: List[int]) -> int:
        s = sum(w * v for w, v in zip(self.weights, vals))
        return s % self.modulus if self.modulus else s

    def valid(self) -> bool:
        return self._eval(self.values) == self.target

    def recover(self, corrupted_field_idx: int) -> 'BalancedGroup':
        # target = sum(w_j * v_j) + w_i * v_i
        # v_i = (target - sum_others) * inv(w_i)
        others = sum(w * v for i, (w, v) in enumerate(zip(self.weights, self.values)) if i != corrupted_field_idx)
        diff = self.target - others
        if self.modulus:
            # Modular inverse
            recovered = (diff * pow(self.weights[corrupted_field_idx], -1, self.modulus)) % self.modulus
        else:
            recovered = diff // self.weights[corrupted_field_idx]
        new_vals = list(self.values)
        new_vals[corrupted_field_idx] = recovered
        return BalancedGroup(new_vals, self.weights, self.target, self.modulus)

    def corrupt(self, idx: int, bad_val: int) -> 'BalancedGroup':
        new_vals = list(self.values)
        new_vals[idx] = bad_val
        return BalancedGroup(new_vals, self.weights, self.target, self.modulus)


# ══════════════════════════════════════════════════════════════════
# MODEL 4: FIBER RECORD (Position-based invariant)
# ══════════════════════════════════════════════════════════════════

class FiberRecord(StructuralFSCType):
    """
    Type where the invariant is derived from the record's POSITION in a stream.
    No stored overhead. sum(values) % m == position % m.
    """
    def __init__(self, values: List[int], m: int, position: int):
        self.values = list(values)
        self.m = m
        self.position = position
        self.fiber_class = position % m

    def valid(self) -> bool:
        return sum(self.values) % self.m == self.fiber_class

    def recover(self, corrupted_field_idx: int) -> 'FiberRecord':
        others = sum(v for i, v in enumerate(self.values) if i != corrupted_field_idx)
        recovered = (self.fiber_class - others) % self.m
        new_vals = list(self.values)
        new_vals[corrupted_field_idx] = recovered
        return FiberRecord(new_vals, self.m, self.position)

    def corrupt(self, idx: int, bad_val: int) -> 'FiberRecord':
        new_vals = list(self.values)
        new_vals[idx] = bad_val
        return FiberRecord(new_vals, self.m, self.position)


# ══════════════════════════════════════════════════════════════════
# MODEL 5: ALGEBRAIC FORMAT (Schema style)
# ══════════════════════════════════════════════════════════════════

class AlgebraicFormat:
    """
    A full data format defined by multiple intersecting linear constraints.
    Allows unique identification of the corrupted field (overdetermination).
    """
    def __init__(self, field_names: List[str]):
        self.field_names = field_names
        self.n = len(field_names)
        self.constraints = []
        self.fields = {}

    def add_constraint(self, weights: List[int], target: int, modulus: Optional[int] = None, label: str = ""):
        self.constraints.append({'w': weights, 't': target, 'm': modulus, 'l': label})

    def set_fields(self, values: dict):
        self.fields = {name: values.get(name, 0) for name in self.field_names}

    def _check(self, vals: List[int], c: dict) -> bool:
        s = sum(wi * vi for wi, vi in zip(c['w'], vals))
        actual = s % c['m'] if c['m'] else s
        return actual == c['t']

    def validate(self) -> List[str]:
        v = [self.fields[n] for n in self.field_names]
        return [c['l'] for c in self.constraints if not self._check(v, c)]

    def heal(self) -> Optional[dict]:
        v = [self.fields[n] for n in self.field_names]
        repairs = []
        for i, name in enumerate(self.field_names):
            relevant = [c for c in self.constraints if c['w'][i] != 0]
            if not relevant: continue
            
            # Find a candidate value that satisfies all relevant constraints
            cands = []
            for c in relevant:
                others = sum(wi * vi for j, (wi, vi) in enumerate(zip(c['w'], v)) if j != i)
                diff = c['t'] - others
                if c['m']:
                    cands.append((diff * pow(c['w'][i], -1, c['m'])) % c['m'])
                elif diff % c['w'][i] == 0:
                    cands.append(diff // c['w'][i])
            
            if len(set(cands)) == 1:
                candidate_val = cands[0]
                test_v = list(v)
                test_v[i] = candidate_val
                # Check if this repair fixes ALL violations
                if all(self._check(test_v, c) for c in self.constraints):
                    repairs.append({'field': name, 'recovered': candidate_val, 'original_corrupt': v[i]})

        return repairs[0] if len(repairs) == 1 else None


# ══════════════════════════════════════════════════════════════════
# DEMONSTRATION
# ══════════════════════════════════════════════════════════════════

def run():
    print("=" * 68)
    print("  STRUCTURAL FSC — ALGEBRAIC TYPE SYSTEM")
    print("=" * 68)
    res = []

    # 1. DNA
    m = {0:1, 1:0, 2:3, 3:2}
    cf = lambda v: m.get(v, -1)
    orig = ComplementPair(3, cf) # G-C
    corrupt = orig.corrupt_primary(99)
    healed = corrupt.recover(0)
    res.append(("Complement Pair (DNA)", healed.valid() and healed.primary == 3))

    # 2. Partition
    pr = PartitionRecord({0,1,2}, [{0}, {1}, {2}])
    corrupt = pr.corrupt_field(1, 99)
    healed = corrupt.recover(1)
    res.append(("Partition Record (Torus)", healed.valid() and healed.field_values[1] == {1}))

    # 3. Balance
    bg = BalancedGroup([10, 5, 5], [1, -1, -1], 0)
    corrupt = bg.corrupt(0, 0)
    healed = corrupt.recover(0)
    res.append(("Balanced Group (Ledger)", healed.valid() and healed.values[0] == 10))

    # 4. Fiber
    fr = FiberRecord([5, 5, 7], 17, position=0)
    corrupt = fr.corrupt(1, 0)
    healed = corrupt.recover(1)
    res.append(("Fiber Record (Positional)", healed.valid() and healed.values[1] == 5))

    # 5. Algebraic Format
    fmt = AlgebraicFormat(["timestamp", "id", "value"])
    fmt.add_constraint([1, 1, 0], 110, label="C1: ts+id")
    fmt.add_constraint([0, 1, 1], 60,  label="C2: id+val")
    fmt.add_constraint([1, 0, 1], 150, label="C3: ts+val")
    fmt.set_fields({"timestamp": 100, "id": 10, "value": 50})

    fmt.fields["value"] = 999 # Corruption
    h = fmt.heal()
    res.append(("Algebraic Format (Schema)", h and h['recovered'] == 50))

    print("\nRESULTS:")
    for n, ok in res:
        print(f"  {'✓' if ok else '✗'} {n}")

if __name__ == "__main__":
    run()
