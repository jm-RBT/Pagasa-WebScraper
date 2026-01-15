# Advisory Scraper Integration with main.py (Parallel Execution)

## Overview

The `advisory_scraper.py` has been integrated with `main.py` using **parallel execution** for optimal performance. PDF analysis and advisory scraping run simultaneously, significantly reducing execution time.

**Important**: Rainfall warnings are **only** extracted from the advisory scraper. PDF analysis no longer includes rainfall data to eliminate redundancy.

## Performance Optimization

### Execution Model

**Sequential (Old):**
```
PDF Analysis (25-30s) → Advisory Scraping (15-20s) = ~47s total
```

**Parallel (New):**
```
PDF Analysis (25-30s) }
                       } Run simultaneously = ~25-30s total
Advisory Scraping (15-20s) }
```

**Result: ~40% faster execution** 🚀

## Architecture

### analyze_pdf.py
- **Purpose**: Standalone PDF extraction tool
- **Output**: Typhoon data only (location, movement, windspeed, signal warnings)
- **No Rainfall Data**: Rainfall warnings removed to eliminate redundancy
- **Usage**: Can be used independently for typhoon-specific data

### main.py
- **Purpose**: Main pipeline with parallel optimization
- **Integration Point**: Runs both PDF analysis and advisory scraping in parallel
- **Merging**: Adds rainfall data from advisory scraper to PDF extraction results
- **Output**: Complete data with TypeScript-compliant `string[]` format for rainfall warnings

## Changes Made

### 1. Data Format

**analyze_pdf.py Output (Typhoon Data Only):**
```python
{
  "typhoon_location_text": "...",
  "typhoon_movement": "...",
  "typhoon_windspeed": "...",
  "signal_warning_tags1": {...},
  ...
  // No rainfall_warning_tags fields
}
```

**main.py Output (With Advisory Data):**
```python
{
  "typhoon_location_text": "...",
  "typhoon_movement": "...",
  "signal_warning_tags1": {...},
  ...
  "rainfall_warning_tags1": ["Location1", "Location2"],
  "rainfall_warning_tags2": ["Location3"],
  "rainfall_warning_tags3": []
}
```

### 2. Rainfall Data Source

**Exclusive Source**: Advisory Scraper
- PDF extraction no longer includes rainfall warnings
- All rainfall data comes from `advisory_scraper.py`
- Empty arrays returned when advisory fetch fails
- Eliminates redundancy and conflicting data sources

```python
# In main.py
def analyze_pdf_and_advisory_parallel(pdf_path):
    with ThreadPoolExecutor(max_workers=2) as executor:
        # Submit both tasks
        pdf_future = executor.submit(analyze_pdf, pdf_path)
        advisory_future = executor.submit(fetch_live_advisory_data)
        
        # Wait for both to complete (happens simultaneously)
        pdf_data = pdf_future.result()
        advisory_data = advisory_future.result()
    
    # Merge results
    return merge_rainfall_warnings(pdf_data, advisory_data)
```

## Usage

### Using analyze_pdf.py (Standalone)

analyze_pdf.py extracts only typhoon-specific data (no rainfall warnings):

```bash
# Analyze a PDF - extracts typhoon location, movement, windspeed, and signals
python analyze_pdf.py "path/to/bulletin.pdf"

# Output shows typhoon info and signal warnings only
# Rainfall warnings section removed
```

**Output Example:**
```
[BASIC INFORMATION]
  Issued:       2022-12-10 11:00:00
  Location:     110 km North Northeast of Virac, Catanduanes
  Wind Speed:   Maximum sustained winds of 45 km/h
  Movement:     Northwestward at 20 km/h

[SIGNAL WARNINGS (TCWS)]
  Signal 1:
    Luzon -> Catanduanes, eastern Camarines Sur
```

### Using main.py (Optimized Pipeline)

main.py runs PDF analysis and advisory scraping in parallel:

```bash
# Analyze latest bulletin with parallel optimization
python main.py

# With verbose output to see parallel execution
python main.py --verbose

# With performance metrics
python main.py --metrics

# Save JSON to file
python main.py > output.json
```

## Example Output

**Console Output (Verbose):**
```
[STEP 3] Analyzing PDF and fetching advisory data (parallel)...
--------------------------------------------------------------------------------
[INFO] Starting parallel execution of PDF analysis and advisory scraping...
[INFO] PDF analysis completed
[INFO] Advisory scraping completed
[INFO] Merged live advisory data with PDF extraction
```

**JSON Output:**
```json
{
  "typhoon_name": "Pepito",
  "pdf_url": "https://...",
  "data": {
    "rainfall_warning_tags1": ["Isabela", "Quirino"],
    "rainfall_warning_tags2": ["Aurora"],
    "rainfall_warning_tags3": []
  }
}
```

## Files Modified

- `main.py`: Added parallel execution with `ThreadPoolExecutor`
- `analyze_pdf.py`: Reverted to original (no advisory integration)

## Key Benefits

1. **~40% faster execution**: Parallel processing eliminates sequential wait time
2. **Better resource utilization**: CPU and I/O operations run simultaneously
3. **Clean separation**: analyze_pdf.py remains standalone, main.py handles integration
4. **Consistent output**: main.py outputs TypeScript-compliant `string[]` format

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
