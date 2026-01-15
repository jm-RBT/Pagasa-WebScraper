# Advisory Scraper Integration with analyze_pdf.py and main.py

## Overview

The `advisory_scraper.py` has been successfully integrated with both `analyze_pdf.py` and `main.py` to provide live rainfall warning data from PAGASA advisories.

## Changes Made

### 1. Data Format Change

**Old Format (IslandGroupType):**
```typescript
rainfall_warning_tags1: {
  Luzon: string | null,
  Visayas: string | null,
  Mindanao: string | null,
  Other: string | null
}
```

**New Format (string array):**
```typescript
rainfall_warning_tags1: string[]
rainfall_warning_tags2: string[]
rainfall_warning_tags3: string[]
```

### 2. Rainfall Warning Levels

- **rainfall_warning_tags1**: Red Warning - Intense Rainfall (>200mm/24hr)
- **rainfall_warning_tags2**: Orange Warning - Heavy Rainfall (100-200mm/24hr)
- **rainfall_warning_tags3**: Yellow Warning - Moderate Rainfall (50-100mm/24hr)

### 3. Integration Flow

```
analyze_pdf.py / main.py
    ├── Extract PDF data (typhoon info, signals, rainfall)
    ├── Call advisory_scraper.scrape_and_extract()
    │   ├── Fetch live PAGASA advisory page
    │   ├── Extract rainfall warnings by level
    │   └── Return: {red: [...], orange: [...], yellow: [...]}
    ├── Merge advisory data with PDF extraction
    │   ├── If advisory data available and non-empty:
    │   │   └── Replace rainfall_warning_tags1/2/3 with live data
    │   └── Otherwise:
    │       └── Convert PDF-extracted IslandGroupType to list format
    └── Output combined result
```

## Usage

### Using analyze_pdf.py

The integration is automatic. Simply use `analyze_pdf.py` as before:

```bash
# Analyze a PDF - automatically fetches live advisory data
python analyze_pdf.py "path/to/bulletin.pdf"

# JSON output
python analyze_pdf.py "path/to/bulletin.pdf" --json
```

### Using main.py

The `main.py` script now also integrates advisory data:

```bash
# Analyze latest bulletin - automatically fetches live advisory data
python main.py

# With verbose output
python main.py --verbose

# Save JSON to file
python main.py > output.json
```

## Example Output

**Console Output:**
```
[INFO] Fetching live rainfall advisory from PAGASA...
[INFO] Successfully fetched advisory data:
  - Red warnings: 5 locations
  - Orange warnings: 8 locations
  - Yellow warnings: 12 locations
[INFO] Replaced rainfall warnings with live advisory data

[RAINFALL WARNINGS]

  Red Warning - Intense Rainfall (>200mm/24hr):
    Locations: Isabela, Quirino, Nueva Vizcaya, Aurora, Quezon

  Orange Warning - Heavy Rainfall (100-200mm/24hr):
    Locations: Pangasinan, Cagayan, Apayao, Ifugao, Mountain Province

  Yellow Warning - Moderate Rainfall (50-100mm/24hr):
    Locations: Ilocos Norte, Ilocos Sur, La Union, Benguet
```

**JSON Output:**
```json
{
  "rainfall_warning_tags1": [
    "Isabela",
    "Quirino",
    "Nueva Vizcaya",
    "Aurora",
    "Quezon"
  ],
  "rainfall_warning_tags2": [
    "Pangasinan",
    "Cagayan",
    "Apayao",
    "Ifugao",
    "Mountain Province"
  ],
  "rainfall_warning_tags3": [
    "Ilocos Norte",
    "Ilocos Sur",
    "La Union",
    "Benguet"
  ]
}
```

## Fallback Behavior

If the advisory scraper cannot fetch live data (network issues, PAGASA site down, etc.), the script automatically falls back to using rainfall data extracted from the PDF:

```
[INFO] Fetching live rainfall advisory from PAGASA...
[WARNING] Failed to fetch advisory data: ...
[INFO] Using PDF-extracted rainfall data (advisory fetch failed or returned no data)
```

The PDF-extracted data is automatically converted from the old IslandGroupType format to the new list format for consistency.

## Key Features

1. **Always fetches live data**: Advisory scraper runs on every `analyze_pdf.py` call
2. **No arguments needed**: Advisory scraper uses live PAGASA URL automatically
3. **Graceful fallback**: Uses PDF data if live fetch fails
4. **Type-safe output**: Matches TypeScript type definitions in `typhoonhubType.ts`
5. **Backward compatible**: Existing code using PDF extraction still works

## Files Modified

- `analyze_pdf.py`: Added advisory integration and new display format
- `main.py`: Added advisory integration and updated JSON output format
- `typhoonhubType.ts`: Already updated to expect `string[]` format (done previously)

## Files Unchanged

- `advisory_scraper.py`: Works independently, no changes needed
- `typhoon_extraction.py`: Continues to extract from PDFs as before
- All other scripts: No changes required

## Testing

Tested with multiple PDFs from `dataset/pdfs/` directory:
- ✅ Advisory fetch and merge works correctly
- ✅ Fallback to PDF data works when advisory unavailable
- ✅ Output format matches TypeScript types
- ✅ Display shows locations in readable format
- ✅ JSON output is valid and properly structured

## Notes

- The advisory scraper uses PAGASA's live advisory page which updates frequently
- Rainfall warnings from advisory may differ from those in older PDF bulletins
- This is expected as the advisory represents current conditions while PDFs are snapshots
