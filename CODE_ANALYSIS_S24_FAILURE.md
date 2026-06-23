# Code Analysis — TaiyangNews PV Price Scraper Bug Report

**Date d'analyse:** 2026-06-23  
**Tâche:** Analyser le code Python du scraper pour identifier les erreurs  
**Context:** S24 (W25-2026) scraping failure due to external causes, but code may have latent bugs

---

## Executive Summary

**5 code defects identified**, including 2 CRITICAL bugs that prevent maintenance scripts from working at all.

The main scraper (`taiyangnews_pv_scraper.py`) is generally sound, but **maintenance scripts** (`fix_missing_weeks.py`, `backfill.py`) contain import errors and unpacking bugs that would crash when executed.

**Risk Level:** ⚠️ **HIGH** — Two critical bugs block disaster recovery workflows

---

## Critical Bugs (Must Fix)

### 🔴 BUG #1: Tuple Unpacking Error in fix_missing_weeks.py

**File:** `pv-price-scraper/fix_missing_weeks.py`  
**Line:** 81  
**Severity:** 🔴 CRITICAL

**Current Code:**
```python
html = fetch_page(w, y)  # fetch_page returns tuple (html_str, url_str)
if not html:
    not_found += 1
    time.sleep(1)
    continue

image_urls = extract_image_urls(html)  # CRASH: html is a tuple, not string!
```

**Problem:**
- `fetch_page()` returns a **tuple** `(html_text, page_url)` (line 237-256 in taiyangnews_pv_scraper.py)
- Line 81 assigns the **entire tuple** to `html` instead of unpacking it
- Line 87 calls `extract_image_urls(html)` expecting a **string**, receives a **tuple**
- Result: `TypeError: expected string or bytes-like object` when function tries to parse soup from tuple

**Impact:**
- The entire `fix_missing_weeks.py` script is **non-functional** and will crash immediately
- Any attempt to repair missing week columns will fail
- This blocks disaster recovery if a week is accidentally deleted from the sheet

**Fix:**
```python
html, page_url = fetch_page(w, y)  # Proper tuple unpacking
if not html:
    not_found += 1
    time.sleep(1)
    continue
```

---

### 🔴 BUG #2: Import of Non-Existent Function in fix_missing_weeks.py

**File:** `pv-price-scraper/fix_missing_weeks.py`  
**Line:** 11  
**Severity:** 🔴 CRITICAL

**Current Code:**
```python
from taiyangnews_pv_scraper import (
    col_header, fetch_page, extract_image_urls,
    extract_prices_free,  # ← Function does NOT exist!
    normalize_with_difflib,
    get_sheet, get_existing_headers, get_canonical_products,
    upsert_week, col_index_to_letter
)
```

**Problem:**
- `extract_prices_free()` is **never defined** in `taiyangnews_pv_scraper.py`
- The actual function is `extract_prices()` (line 301)
- The import statement is **syntactically wrong** and will never work
- Result: `NameError: name 'extract_prices_free' is not defined` at line 93

**Impact:**
- Script crashes with `NameError` at runtime on line 93: `prices_raw = extract_prices_free(image_urls)`
- Even if bug #1 is fixed, bug #2 prevents execution
- Makes the fix_missing_weeks.py script **completely unusable**

**Fix:**
```python
from taiyangnews_pv_scraper import (
    col_header, fetch_page, extract_image_urls,
    extract_prices,  # ← Correct function name
    normalize_with_difflib,
    get_sheet, get_existing_headers, get_canonical_products,
    upsert_week, col_index_to_letter
)

# And then use:
prices_raw = extract_prices(image_urls)  # Line 93
```

---

## High Severity Bugs

### 🟠 BUG #3: Whitespace-Only Canonical Product Names

**File:** `pv-price-scraper/taiyangnews_pv_scraper.py`  
**Line:** 460-462  
**Severity:** 🟠 HIGH

**Current Code:**
```python
def get_canonical_products(ws) -> list:
    col_b = ws.col_values(2)
    return [p for p in col_b[2:] if p]  # ← Includes whitespace-only strings!
```

**Problem:**
- Python's truthiness check on strings (`if p`) treats `"  "` (spaces), `"\t"` (tabs), etc. as **truthy**
- These whitespace-only strings pass the filter and enter the canonical product list
- Later, `difflib.get_close_matches()` on line 428-433 compares product names against whitespace-only entries
- This causes incorrect product name normalization and potential price mapping to wrong rows

**Impact:**
- If the Google Sheet contains orphaned whitespace rows from previous data cleanup operations (e.g., deleted product rows that leave empty cells), these get included in canonical matching
- New products that should match to a real canonical name may incorrectly match to whitespace instead
- Subtle data corruption: prices mapped to wrong product rows with **no warning**
- Especially dangerous if a deleted product row is later re-added (sheet will have duplicate names at different rows)

**Example Failure Case:**
```python
# Current behavior:
col_b = ["Category", "Product", "Polysilicon", "", "Glass", "  ", "Wafer"]
canonical = [p for p in col_b[2:] if p]
# Result: ["Polysilicon", "  ", "Glass", "Wafer"]  # Whitespace included!

# difflib matching:
name = "Polysilicon (new variant)"
matches = difflib.get_close_matches(name, ["Polysilicon", "  ", "Glass", "Wafer"], n=1)
# Depending on difflib thresholds, might match to "  " instead of "Polysilicon"

# Price for new product stored in wrong row!
```

**Fix:**
```python
def get_canonical_products(ws) -> list:
    col_b = ws.col_values(2)
    return [p for p in col_b[2:] if p and p.strip()]  # Filter out whitespace
```

---

## Medium Severity Bugs

### 🟡 BUG #4: Regex Pattern Fails on Edge-Case Decimal Numbers

**File:** `pv-price-scraper/taiyangnews_pv_scraper.py`  
**Lines:** 400 (extract_prices), 484 (clean_units)  
**Severity:** 🟡 MEDIUM

**Current Code:**
```python
# Line 400 in extract_prices():
m = re.search(r'[0-9]+(?:[.,][0-9]+)?', str(raw_val))

# Line 484 in clean_units():
m = re.search(r'[0-9]+(?:[.,][0-9]+)?', cell)
```

**Problem:**
- The regex pattern `r'[0-9]+(?:[.,][0-9]+)?'` **requires at least one leading digit**
- It fails to match numbers starting with a decimal point (e.g., `.5`)
- It truncates trailing decimals (e.g., `5.` becomes `5` instead of `5.`)

**Impact:**
- If Claude Vision or manual entry produces edge-case formats (rare but possible with OCR errors), prices are malformed
- Example: Vision extracts `.5 RMB/W` (leading decimal), cleaned to `.5`, regex captures nothing, price becomes `None`
- Or: price cell contains `5.`, regex captures `5`, loses the decimal point

**Example Failure Case:**
```python
import re
pattern = r'[0-9]+(?:[.,][0-9]+)?'

# Failing case 1: Leading decimal
value = ".5 RMB/kg"
m = re.search(pattern, value)
print(m.group(0) if m else None)  # Output: "5" (WRONG! Should capture ".5")

# Failing case 2: Trailing decimal
value = "5. RMB/W"
m = re.search(pattern, value)
print(m.group(0) if m else None)  # Output: "5" (WRONG! Should preserve "5.")

# Working case (normal)
value = "36.5 RMB/kg"
m = re.search(pattern, value)
print(m.group(0) if m else None)  # Output: "36.5" (correct)
```

**Fix:**
```python
# Better regex that handles edge cases:
m = re.search(r'[0-9]*[.,]?[0-9]+', str(raw_val))
# OR more explicitly:
m = re.search(r'(?:[0-9]+[.,][0-9]*|[0-9]*[.,][0-9]+|[0-9]+)', str(raw_val))
```

---

## Low Severity Bugs

### 🟢 BUG #5: col_index_to_letter() Missing Input Validation

**File:** `pv-price-scraper/taiyangnews_pv_scraper.py`  
**Lines:** 164-170  
**Severity:** 🟢 LOW

**Current Code:**
```python
def col_index_to_letter(index: int) -> str:
    """Convert 1-based column index to A1-notation letter (e.g. 27 → AA)."""
    result = ""
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result
```

**Problem:**
- Function accepts `index <= 0` without raising an error
- Returns empty string `""` for invalid input (0, negative, etc.)
- Could lead to invalid cell references like `""1` or `""3` if passed to batch_update

**Impact:**
- **Currently:** No impact — all three callers (lines 487, 565, 592) always pass valid indices from column counts
- **Future risk:** If function is ever called with 0 or negative input in future refactoring, it silently fails
- Violates defensive programming principle (fail fast)

**Example:**
```python
col_index_to_letter(1)    # "A" (correct)
col_index_to_letter(27)   # "AA" (correct)
col_index_to_letter(0)    # "" (should raise ValueError)
col_index_to_letter(-5)   # "" (should raise ValueError)
```

**Fix:**
```python
def col_index_to_letter(index: int) -> str:
    """Convert 1-based column index to A1-notation letter (e.g. 27 → AA)."""
    if index < 1:
        raise ValueError(f"Column index must be >= 1, got {index}")
    result = ""
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result
```

---

## Vulnerability (Not a Bug, But Risky)

### ⚠️ Unhandled Exception Risk in backfill.py

**File:** `pv-price-scraper/backfill.py`  
**Lines:** 107-111  
**Severity:** ⚠️ MEDIUM (Architectural)

**Current Code:**
```python
prices_raw = extract_prices(image_urls)  # No try/except!
if not prices_raw:
    not_found += 1
    time.sleep(1)
    continue
```

**Problem:**
- If `extract_prices()` raises an **unhandled exception** (e.g., Claude API timeout, JSON parsing error from line 362-366), the entire backfill script crashes
- The check `if not prices_raw` only catches empty dict `{}`, not exceptions
- In `extract_prices()`, exceptions from the Claude API retry loop (lines 335-350) can bubble up uncaught

**Impact:**
- Long-running backfill operations (W1-2024 to today = ~130 weeks) crash midway
- No resume capability — must restart from scratch
- Especially risky if running overnight unattended

**Fix:**
```python
try:
    prices_raw = extract_prices(image_urls)
except Exception as e:
    logger.error(f"  [Week {w}-{y}] Extract failed: {e}")
    not_found += 1
    time.sleep(1)
    continue

if not prices_raw:
    not_found += 1
    time.sleep(1)
    continue
```

---

## Summary of All Bugs

| # | Severity | Component | Issue | Impact |
|---|----------|-----------|-------|--------|
| 1 | 🔴 CRITICAL | fix_missing_weeks.py:81 | Tuple unpacking error | Script crashes at image extraction |
| 2 | 🔴 CRITICAL | fix_missing_weeks.py:11 | Non-existent function import | Script crashes at function call |
| 3 | 🟠 HIGH | taiyangnews_pv_scraper.py:462 | Whitespace in canonical products | Silent data corruption (wrong price mapping) |
| 4 | 🟡 MEDIUM | taiyangnews_pv_scraper.py:400,484 | Regex fails on edge decimals | Malformed prices on OCR errors |
| 5 | 🟢 LOW | taiyangnews_pv_scraper.py:164 | Missing input validation | Future-proofing (no current impact) |
| — | ⚠️ MEDIUM | backfill.py:107 | Unhandled exceptions | Backfill crashes mid-run |

---

## Root Cause Analysis: Why S24 Failed

The S24 (W25-2026) scraping failure on 2026-06-22 was **NOT caused by these code bugs**, but rather by:

1. **External cause (primary):** TaiyangNews W25-2026 and W26-2026 not yet published at scrape time
2. **Infrastructure cause (secondary):** GitHub workflows disabled after repo rename on 2026-06-11, not re-enabled until after 2026-06-15

However, these code bugs make the system **fragile** if recovery is needed:
- **Bug #1 & #2** prevent using `fix_missing_weeks.py` to backfill the missing W25 data
- **Bug #3** could have silently corrupted existing data during normal operation
- **Bug #4** would fail on malformed OCR output
- **Vulnerability** could have crashed a long backfill operation

---

## Recommendations

### Immediate (Critical)
1. ✅ **Fix Bug #1** (tuple unpacking) — 2 lines
2. ✅ **Fix Bug #2** (function import) — 1 line

### High Priority
3. ✅ **Fix Bug #3** (whitespace filtering) — 1 line change

### Medium Priority  
4. ✅ **Fix Bug #4** (regex improvement) — improve pattern
5. ✅ **Add exception handling** to backfill.py — 5 lines

### Low Priority
6. ⏱️ **Fix Bug #5** (input validation) — defensive coding, future-proof

---

## Testing After Fixes

After applying fixes, run:

```bash
# Verify imports work
python -c "from pv-price-scraper.fix_missing_weeks import *"

# Run test suite
python -m pytest pv-price-scraper/test_scraper.py -v

# Test edge cases
python -c "
import re
# Test regex with edge cases
for val in ['.5', '5.', '36.5', '0.33']:
    m = re.search(r'(?:[0-9]+[.,][0-9]*|[0-9]*[.,][0-9]+|[0-9]+)', val)
    print(f'{val} -> {m.group(0) if m else None}')
"

# Test canonical products filtering
from taiyangnews_pv_scraper import get_canonical_products
# Verify no whitespace in results
```

---

**Report Generated:** 2026-06-23 — Analysis Complete

