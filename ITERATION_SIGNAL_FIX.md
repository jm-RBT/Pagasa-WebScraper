# Iteration Summary - Signal Extraction Fix

## Changes Made

### 1. Fixed TCWS Signal Table Separator Handling
**Problem:** The signal parser was incorrectly handling the " - -" separator in PDF tables. This separator indicates "no content for this column" in the table structure, not a separator between regions.

**Example:**
- Raw collected: `['Batanes and the northeastern portion of - -', 'Babuyan Islands (Babuyan Is.)']`
- After joining: `'Batanes and the northeastern portion of - - Babuyan Islands'`
- OLD LOGIC: Split by " - " → Got `'Batanes and the northeastern portion of'` for Luzon (wrong!)
- NEW LOGIC: Remove " - -" markers first → Get `'Batanes and the northeastern portion of Babuyan Islands'` for Luzon (correct!)

### 2. Preserved Parenthetical Location Markers
**Finding:** The expected output includes parenthetical markers like `(Babuyan Is.)` which are abbreviations or alternate names for locations. These should be kept in the final output.

**Example:**
- Expected: `'Batanes and the northeastern portion of Babuyan Islands (Babuyan Is.)'`
- Now correctly extracting with parenthetical preserved

## Results

### Test Accuracy
```
Total tests: 39
Pass rate: 100.0%
Field accuracy: 91.5% (428/468 fields matched)
```

### Key Improvements
- ✅ Signal extraction now correctly handles " - -" table separators
- ✅ Multi-line location data properly joined
- ✅ Parenthetical location markers preserved
- ✅ Wind impact keyword filtering working correctly
- ✅ All 39 test bulletins passing

### Remaining Issues
- ~40 fields still mismatched (8.5% of total)
- Primary culprits:
  1. **Rainfall extraction incomplete**: `RainfallWarningExtractor` needs refinement to properly extract intensity levels and location boundaries
  2. **Test data quality**: Some annotations contain suspicious values (e.g., "bagong", "public" as location names)
  3. **Edge cases**: Some complex bulletin layouts may not be handled correctly

## Code Changes

### File: `typhoon_extraction_ml.py`

#### SignalWarningExtractor._parse_signal_table() (Lines 167-320)
- Added " - -" separator removal before location text processing
- Changed order: Now removes separators BEFORE splitting by " - "
- Removed aggressive parenthetical removal (keeping location abbreviations)
- Added logic to distinguish between table separators and multi-region separators

**Key logic:**
```python
# Remove " - -" table separators (they indicate "no content" for that column in table)
full_text = full_text.replace(' - - ', ' ').replace(' - -', '')

# Clean up extra whitespace
full_text = re.sub(r'\s+', ' ', full_text).strip()

# Now split by " - " only if it separates actual regions
if ' - ' in full_text:
    parts = full_text.split(' - ')
    # Assign to Luzon/Visayas/Mindanao based on position
```

## Next Steps

1. **Improve Rainfall Extraction** (HIGH PRIORITY)
   - Current implementation extracts too much text
   - Need to properly delimit rainfall statements by intensity level
   - Respect "over" keyword boundaries for location extraction

2. **Address Test Data Quality**
   - Some annotations have suspicious values
   - Should validate test data against actual PDFs before relying on them

3. **Handle Edge Cases**
   - Some bulletins have complex table layouts
   - May need region-specific parsing logic

## Validation Notes

- Tested with Henry (TC08) and Uwan (TC21) bulletins
- Both early (TCA) and late (TCB) bulletins working
- No errors or exceptions during extraction
- All test cases completing successfully

## Files Modified
- `typhoon_extraction_ml.py` - Signal table parsing fixes
- `debug_test.py` - Created new debug script to identify field-by-field mismatches

## Statistics
- Lines changed: ~50 (mostly in _parse_signal_table method)
- Test coverage: 39 bulletins, 468 fields
- Regression: None (maintained 100% pass rate)
- Improvement: Signals now correctly extracted where previously returning None/empty
