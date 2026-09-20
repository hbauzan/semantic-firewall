# Universal Remediation Directive: Eradication of Decimal Truncation & Numerical Mutilation

> **TARGET**: Any AI Coding Agent (Cursor, Antigravity, Claude, Copilot, Cline, Aider) operating on any ancestor, sibling, or downstream repository of the semantic firewall / coordinate inspector family.  
> **MISSION**: Audit the entire codebase, eradicate all silent decimal truncations and coward roundings, and upgrade all coordinate and embedding computations to native IEEE 754 full-mantissa precision.

---

## 1. Directive Preamble & Immediate Context

You are operating on a codebase whose core functionality relies on **high-dimensional coordinate geometry and interval membership** in dense embedding spaces ($D \in [768, 4096]$).

In this domain:
- Individual coordinate magnitudes live in the $[-0.15, +0.15]$ range ($\bar{|v|} \approx 0.025$).
- Interval boundaries $[lo_d, hi_d]$ and separation gaps between distinct semantic concepts live at scales of $10^{-4}$ to $10^{-6}$.
- **Any rounding, decimal formatting (`:.4f`, `:.6f`), or float16 casting completely erases empirical coordinate separation and corrupts scientific measurements.**

You are commanded to treat floating-point numbers with **absolute numerical purity**. No truncation is permitted for aesthetic, terminal, or disk-saving reasons.

---

## 2. Mandatory Audit & Search Protocol

Run a systematic grep across all source files (`.py`, `.js`, `.ts`, `.c`, `.cpp`, `.rs`, `.sql`) searching for the following antipatterns:

### A. Explicit Rounding Functions (PROHIBITED IN COMPUTATION)
* Python:
  ```bash
  git grep -nE "(\bround\(|\.round\(|np\.round|torch\.round)"
  ```
* JavaScript / TypeScript:
  ```bash
  git grep -nE "(Math\.round|Math\.floor|Math\.ceil|\.toFixed\(|parseFloat\(.*\.toFixed)"
  ```

### B. Lossy String Formatting & Templates (PROHIBITED IN EXPORTS)
* Python string interpolations that truncate decimals:
  ```bash
  git grep -nE '(:[0-9]*\.[0-9]+f|%[0-9]*\.[0-9]+f)'
  ```
  *(Examples of culprits: `{val:.4f}`, `{val:.6f}`, `{val:.2f}`, `%0.4f`)*
* JavaScript/TypeScript number conversions:
  ```bash
  git grep -nE '(\.toFixed\([0-9]+\)|\.toPrecision\([0-9]+\))'
  ```

### C. Premature Downcasting & Quantization
* Casting embedding tensors to half-precision (`float16` / `bfloat16`) in analytical or firewall paths:
  ```bash
  git grep -nE "(\.half\(\)|\.to\(torch\.float16\)|\.astype\(np\.float16\)|np\.float16|torch\.float16|Float16Array)"
  ```

---

## 3. Required Replacement Patterns

### Pattern 1: Python String Serialization (CSV, JSON, Logs)
❌ **WRONG (Silent Truncation)**:
```python
# Destroys interval boundaries:
formatted = f"{val:.6f}"
formatted = f"{val:.4f}"
formatted = str(round(val, 5))
```

✅ **CORRECT (Full IEEE 754 Native Mantissa)**:
```python
# Preserves all significant digits (exact round-trip IEEE 754):
formatted = f"{float(val):.17g}"
# Or native float string conversion:
formatted = str(float(val))
```

### Pattern 2: Python / NumPy Bounding Box & Coordinate Accumulation
❌ **WRONG**:
```python
lo = round(float(np.min(col)), 4)
hi = round(float(np.max(col)), 4)
gap = round(lo_b - hi_a, 6)
```

✅ **CORRECT**:
```python
# Pure float32 or float64 scalar extraction:
lo = float(np.min(col))
hi = float(np.max(col))
gap = float(lo_b - hi_a)
```

### Pattern 3: JSON Serialization
❌ **WRONG**:
```python
# Using custom encoders that round floats:
class RoundingEncoder(json.JSONEncoder):
    def iterencode(self, o, _one_shot=False): ...
```

✅ **CORRECT**:
```python
# Native Python json.dumps serializes IEEE 754 float64 with full precision by default:
json_payload = json.dumps(data, ensure_ascii=False)
```

### Pattern 4: JavaScript / TypeScript Data Parsing & WebGL Feed
❌ **WRONG**:
```typescript
const coord = parseFloat(rawString).toFixed(4);
```

✅ **CORRECT**:
```typescript
// Keep native 64-bit float in memory; cast only at WebGL buffer upload:
const coord = Number(rawString); // or parseFloat(rawString) without toFixed
glBuffer[i] = coord; // Native Float32Array handles GPU representation losslessly
```

### Pattern 5: Display-Only UI Exception (Strict Isolation)
If a human user interface requires short numbers for readability:
1. **Never mutate the underlying data object**.
2. Perform cosmetic formatting **only at the final DOM string interpolation**.
3. Accompany with an informative tooltip or caption: `Display-only rounding; engine operates on exact unrounded float`.

---

## 4. Remediation Execution Plan for the AI Agent

Follow these exact steps to remediate the target repository:

1. **Step 1: Inventory**:
   Run the search queries from Section 2 (or execute `python tools/audit_precision.py` if present). Log all occurrences.
2. **Step 2: Segregate Core vs. Cosmetic**:
   - Identify files that compute embeddings, intervals, coordinate boundaries, matrix operations, and CSV/JSON data dumps (CORE).
   - Identify purely decorative HTML/CSS or terminal progress bars (COSMETIC).
3. **Step 3: Refactor Core Files**:
   - Strip all `round()`, `:.Nf`, and lossy formatters from all CORE files.
   - Replace with native Float32/Float64 preservation (`f"{val:.17g}"`).
4. **Step 4: Regenerate Cached Datasets**:
   - If the repository has cached CSVs, JSONs, or NPZs generated with old truncated scripts, re-run the generation scripts with full precision.
5. **Step 5: Run Test Suite**:
   - Run the repository's unit and integration tests.
   - Verify that test assertions expecting rounded numbers (e.g. `assert x == 0.0256`) are updated to exact comparisons or `math.isclose(a, b, rel_tol=1e-7)`.
6. **Step 6: Verify Git Diff**:
   - Ensure no lossy casts were missed. Stage and commit with:
     `fix(precision): eradicate decimal truncation and enforce IEEE 754 full mantissa`

---

## 5. Definition of Done (DoD)

The remediation is complete when and only when:
- [ ] Zero occurrences of `round(` or `np.round` exist in mathematical decision, interval, or embedding modules.
- [ ] All exported CSVs and JSONs export full IEEE 754 mantissas (`:.17g` or native float string).
- [ ] Bounding intervals $[lo, hi]$ reflect exact empirical extrema without artificial padding or truncation.
- [ ] Entire test suite passes with zero precision warnings.
