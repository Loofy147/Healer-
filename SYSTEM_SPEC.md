# FSC Universal Framework: System Specification

This document provides a comprehensive list of all classes, methods, and functions within the FSC framework.

## Module: `fsc_framework.py`

### Class: `FSCAnalyzer`
_Given a dataset, detect if a linear integer invariant exists_
- `method` **analyze**`(data: numpy.ndarray, group_size: int = 4) -> dict`
  - _Test multiple invariant hypotheses on the data._

### Class: `FSCDescriptor`
_Describes how FSC applies to a specific data format._
- `method` **__init__**`(self, name, field, n_elements, invariant_fn, recover_fn, overhead, exact=True)`
  - _Initialize self.  See help(type(self)) for accurate signature._
- `method` **encode**`(self, group)`
- `method` **recover**`(self, corrupted_group, lost_idx, invariant)`

### Class: `FSCFactory`
_Generate FSCDescriptors for common algebraic fields._
- `method` **integer_sum**`(name: str, n: int) -> fsc_framework.FSCDescriptor`
  - _Integer sum invariant: S = sum(v[0..n-1])_
- `method` **modular_sum**`(name: str, n: int, m: int) -> fsc_framework.FSCDescriptor`
  - _Modular sum: S = sum(v) mod m_
- `method` **polynomial_eval**`(name: str, k: int, p: int, eval_point: int) -> fsc_framework.FSCDescriptor`
  - _Treat data as polynomial coefficients, store one evaluation point._
- `method` **structural_mirror**`(name: str, n: int, m: int) -> fsc_framework.FSCDescriptor`
  - _Structural mirror: v[i] + v[i+n] == m._
- `method` **structural_zero_sum**`(name: str, n: int) -> fsc_framework.FSCDescriptor`
  - _Structural zero-sum: sum(v) == 0._
- `method` **weighted_sum**`(name: str, weights: list, m: Optional[int] = None) -> fsc_framework.FSCDescriptor`
  - _Weighted sum: S = sum(w[i] * v[i]) [mod m]_
- `method` **xor_sum**`(name: str, n: int) -> fsc_framework.FSCDescriptor`
  - _XOR invariant: S = v[0] ^ v[1] ^ ... ^ v[n-1]_

### Class: `FSCHealer`
_Universal FSC healing engine._
- `method` **__init__**`(self, descriptor: fsc_framework.FSCDescriptor)`
  - _Initialize self.  See help(type(self)) for accurate signature._
- `method` **encode_stream**`(self, data: list) -> tuple`
  - _Split data into groups, compute invariants._
- `method` **heal_stream**`(self, corrupted_groups: list, invariants: list, loss_mask: list) -> list`
  - _Heal corrupted groups using invariants._
- `method` **verify**`(self, original: list, healed: list) -> dict`
  - _Compare original and healed streams._

### Function: `run_all`
- `run_all`**`()`**

---

## Module: `fsc_structural.py`

### Class: `AlgebraicFormat`
_A full data format defined by multiple intersecting linear constraints._
- `method` **__init__**`(self, field_names: 'List[str]')`
  - _Initialize self.  See help(type(self)) for accurate signature._
- `method` **add_constraint**`(self, weights: 'List[int]', target: 'int', modulus: 'Optional[int]' = None, label: 'str' = '')`
- `method` **heal**`(self) -> 'Optional[dict]'`
- `method` **set_fields**`(self, values: 'dict')`
- `method` **validate**`(self) -> 'List[str]'`

### Class: `BalancedGroup`
_Type where a weighted sum of fields equals a fixed target._
- `method` **__init__**`(self, values: 'List[int]', weights: 'List[int]', target: 'int', modulus: 'Optional[int]' = None)`
  - _Initialize self.  See help(type(self)) for accurate signature._
- `method` **corrupt**`(self, idx: 'int', bad_val: 'int') -> "'BalancedGroup'"`
- `method` **recover**`(self, corrupted_field_idx: 'int') -> "'BalancedGroup'"`
  - _Recover a new valid instance by repairing the specified field._
- `method` **valid**`(self) -> 'bool'`
  - _True if the instance satisfies its structural invariant._

### Class: `ComplementPair`
_Type where validity is defined by an involution f: f(primary) == complement._
- `method` **__init__**`(self, primary: 'Any', complement_fn: 'Callable', inverse_fn: 'Optional[Callable]' = None)`
  - _Initialize self.  See help(type(self)) for accurate signature._
- `method` **corrupt_primary**`(self, bad_value: 'Any') -> "'ComplementPair'"`
  - _Simulate corruption of the primary field._
- `method` **recover**`(self, corrupted_field_idx: 'int') -> "'ComplementPair'"`
  - _Recover a new valid instance by repairing the specified field._
- `method` **valid**`(self) -> 'bool'`
  - _True if the instance satisfies its structural invariant._

### Class: `FiberRecord`
_Type where the invariant is derived from the record's POSITION in a stream._
- `method` **__init__**`(self, values: 'List[int]', m: 'int', position: 'int')`
  - _Initialize self.  See help(type(self)) for accurate signature._
- `method` **corrupt**`(self, idx: 'int', bad_val: 'int') -> "'FiberRecord'"`
- `method` **recover**`(self, corrupted_field_idx: 'int') -> "'FiberRecord'"`
  - _Recover a new valid instance by repairing the specified field._
- `method` **valid**`(self) -> 'bool'`
  - _True if the instance satisfies its structural invariant._

### Class: `PartitionRecord`
_Type where fields must form a partition of a fixed universe._
- `method` **__init__**`(self, universe: 'Set[Any]', field_values: 'List[Set[Any]]')`
  - _Initialize self.  See help(type(self)) for accurate signature._
- `method` **corrupt_field**`(self, idx: 'int', bad_val: 'Any') -> "'PartitionRecord'"`
- `method` **recover**`(self, corrupted_field_idx: 'int') -> "'PartitionRecord'"`
  - _Recover a new valid instance by repairing the specified field._
- `method` **valid**`(self) -> 'bool'`
  - _True if the instance satisfies its structural invariant._

### Class: `StructuralFSCType`
_Base class for data types that embed a linear invariant._
- `method` **recover**`(self, corrupted_field_idx: 'int') -> "'StructuralFSCType'"`
  - _Recover a new valid instance by repairing the specified field._
- `method` **valid**`(self) -> 'bool'`
  - _True if the instance satisfies its structural invariant._

### Function: `run`
- `run`**`()`**

---

## Module: `fsc_binary.py`

### Class: `FSCField`
- `method` **__init__**`(self, name: str, ftype: str, recoverable: bool = True, weight: int = 1)`
  - _Initialize self.  See help(type(self)) for accurate signature._

### Class: `FSCReader`
- `method` **__init__**`(self, filename: str)`
  - _Initialize self.  See help(type(self)) for accurate signature._
- `method` **get_records**`(self)`
- `method` **verify_all**`(self) -> numpy.ndarray`
  - _Vectorized verification of all records. Returns boolean mask of validity._
- `method` **verify_and_heal**`(self, record_idx: int, corrupted_field_idx: int = -1) -> bool`
  - _Verify record integrity. If corrupted_field_idx is provided,_

### Class: `FSCSchema`
- `method` **__init__**`(self, fields: List[fsc_binary.FSCField])`
  - _Initialize self.  See help(type(self)) for accurate signature._

### Class: `FSCWriter`
- `method` **__init__**`(self, schema: fsc_binary.FSCSchema)`
  - _Initialize self.  See help(type(self)) for accurate signature._
- `method` **add_record**`(self, data: List[int])`
- `method` **add_records**`(self, data_matrix: Any)`
  - _Batch add records from a 2D list or NumPy array._
- `method` **write**`(self, filename: str)`

---

## Module: `fsc_network.py`

### Class: `StructuralPacket`
_A network packet with a self-healing header._
- `method` **__init__**`(self, m: int = 251)`
  - _Initialize self.  See help(type(self)) for accurate signature._
- `method` **build**`(self, src_id: int, dst_id: int)`
  - _Calculates dependent fields (seq_num, length, payload_sum)_
- `method` **verify_and_heal**`(self, header_fields: Dict[str, int]) -> Optional[Dict[str, int]]`

### Function: `demo`
- `demo`**`()`**

---

## Module: `fsc_database.py`

### Class: `StructuralTable`
_A table where every row i and column j satisfies:_
- `method` **__init__**`(self, rows: int, cols: int, m: int = 251)`
  - _Initialize self.  See help(type(self)) for accurate signature._
- `method` **corrupt**`(self, row: int, col: int, bad_val: int)`
- `method` **set_data**`(self, source_data: List[List[int]])`
  - _Populate the table and calculate the structural balance fields._
- `method` **verify_and_heal**`(self) -> List[Dict]`
  - _Scans the table for violations and heals them._

### Function: `demo`
- `demo`**`()`**

---

## Module: `fsc_storage.py`

### Class: `StructuralLog`
_A log where every record is algebraically dependent on its position._
- `method` **__init__**`(self, m: int = 251, fields_per_record: int = 4)`
  - _Initialize self.  See help(type(self)) for accurate signature._
- `method` **append**`(self, data: List[int])`
  - _Append a new record. We take n-2 fields and compute the last 2_
- `method` **verify_and_heal**`(self, index: int) -> bool`
  - _Checks if the record at index is valid._

---

## Module: `fsc_domains.py`

### Class: `Ledger`
- `method` **__init__**`(self)`
  - _Initialize self.  See help(type(self)) for accurate signature._
- `method` **post**`(self, account, amount, entry_type)`
- `method` **recover_entry**`(self, corrupt_idx)`
  - _Recover a corrupted entry from the balance invariant._
- `method` **verify**`(self)`

### Function: `dna_complement`
- `dna_complement`**`(strand)`**

### Function: `gc_content`
- `gc_content`**`(strand)`**

### Function: `gf_mul`
- `gf_mul`**`(a, b)`**
  - _GF(2^8) multiplication with AES polynomial x^8+x^4+x^3+x+1._

### Function: `gf_sum`
- `gf_sum`**`(vals)`**
  - _XOR sum in GF(2^8)._

### Function: `lagrange_interp`
- `lagrange_interp`**`(points, x, p)`**

### Function: `make_ipv4_header`
- `make_ipv4_header`**`(src_ip, dst_ip, ttl=64, protocol=6, length=40)`**
  - _Build minimal IPv4 header (20 bytes), checksum=0 then compute._

### Function: `mix_column`
- `mix_column`**`(col)`**
  - _AES MixColumns on one 4-byte column._

### Function: `ones_complement_sum`
- `ones_complement_sum`**`(data: bytes) -> int`**
  - _Ones-complement sum of 16-bit words._

### Function: `poly_eval`
- `poly_eval`**`(coeffs, x, p)`**

### Function: `report`
- `report`**`(domain, ok, mechanism, example, overhead=None)`**

### Function: `stereo_encode`
- `stereo_encode`**`(L, R)`**
  - _Encode stereo to mid-side._

### Function: `stereo_recover_L`
- `stereo_recover_L`**`(M, S)`**

### Function: `stereo_recover_R`
- `stereo_recover_R`**`(M, S)`**

---

---

## Module: `fsc_multifault.py`

### Class: `MultiFaultFSC`
_k-fault tolerant FSC for a record of n integer fields._
- `method` **__init__**`(self, n_data: int, k_faults: int, p: int = 251)`
- `method` **encode**`(self, data: list) -> list`
  - _Encode data → data + k evaluation points._
- `method` **recover**`(self, record: list, corrupted_indices: list) -> list`
  - _Recover k corrupted fields from evaluation invariants._
- `method` **is_valid**`(self, record: list) -> bool`
- `method` **detect_corruptions**`(self, record: list) -> list`
  - _Identify corrupted fields by trying combinations of k faults._

---

## Module: `fsc_streaming.py`

### Class: `SlidingWindowFSC`
_FSC over a sliding window of W records._
- `method` **__init__**`(self, window_size: int, fields: List[str])`
- `method` **ingest**`(self, record: dict) -> dict`
  - _Add record and update rolling invariant._
- `method` **get_window_invariant**`(self, seq: int) -> Optional[dict]`
- `method` **recover**`(self, window_records: List[dict], lost_seq: int, invariant: dict) -> dict`

### Class: `BurstFSC`
_Handle burst loss using multiple overlapping windows._
- `method` **__init__**`(self, window_size: int, n_windows: int = 2)`
- `method` **process**`(self, record: dict) -> None`
- `method` **recover_burst**`(self, lost_seqs: List[int]) -> List[dict]`

---

## Module: `fsc_nonnumeric.py`

### Class: `SegmentFSC`
_Apply FSC to a blob by splitting into integer segments._
- `method` **__init__**`(self, segment_size: int = 8)`
- `method` **encode**`(self, data: bytes) -> dict`
- `method` **recover**`(self, corrupted: dict, seg_idx: int) -> dict`
- `method` **decode**`(self, encoded: dict) -> bytes`

### Class: `MixedRecord`
_A record with mixed types (int, str, float, bytes) encoded as integers._
- `method` **__init__**`(self, schema: list)`
- `method` **encode**`(self, record: dict) -> list`
- `method` **decode**`(self, encoded: list) -> dict`
- `method` **recover_field**`(self, encoded: list, field_idx: int) -> list`
- `method` **is_valid**`(self, encoded: list) -> bool`
