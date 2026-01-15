# Portability and Compatibility Guide

## Python Version Compatibility

**Target:** Python 3.8.10+ (tested up to Python 3.12)

### Language Features Used
- ✅ f-strings (Python 3.6+)
- ✅ pathlib (Python 3.4+)
- ✅ Type hints in docstrings (not runtime, compatible with 3.8)
- ✅ concurrent.futures.ThreadPoolExecutor (Python 3.2+)
- ✅ contextlib.contextmanager (Python 2.5+)
- ✅ No walrus operator (:=)
- ✅ No match statements (Python 3.10+)
- ✅ No positional-only parameters (/)

## Platform Compatibility

### Linux/Ubuntu ✅
**Fully Supported** - Primary target platform

- All features work as designed
- CPU throttling uses `os.nice()` for process priority
- Path handling uses `pathlib` (cross-platform)
- All I/O operations are platform-independent

### Windows ✅
**Supported with graceful degradation**

- CPU throttling skips `os.nice()` (not available on Windows)
- All other features work identically
- Path handling via `pathlib` ensures Windows compatibility

### macOS ✅
**Supported** - Unix-like behavior

- CPU throttling works via `os.nice()`
- All features identical to Linux

## Celery Integration

### Requirements for Celery Tasks

1. **No File System Dependencies**
   - `main.py` accepts URLs or file paths as arguments
   - No hardcoded absolute paths
   - Relative paths use `Path(__file__).parent`

2. **Stateless Execution**
   - Each function call is independent
   - No shared state between calls
   - Thread-safe parallel execution

3. **Import Structure**
   ```python
   from main import analyze_pdf_and_advisory_parallel
   
   @celery_app.task
   def process_typhoon_bulletin(pdf_url):
       result = analyze_pdf_and_advisory_parallel(
           pdf_url, 
           low_cpu_mode=False,  # Set based on your needs
           verbose=False
       )
       return result
   ```

4. **Recommended Celery Configuration**
   ```python
   # In celeryconfig.py
   task_time_limit = 300  # 5 minutes max
   task_soft_time_limit = 240  # 4 minutes soft limit
   worker_prefetch_multiplier = 1  # One task at a time
   worker_max_tasks_per_child = 50  # Restart worker after 50 tasks
   ```

## Dependencies

All dependencies in `requirements.txt` are:
- ✅ Python 3.8.10+ compatible
- ✅ Available on PyPI
- ✅ Cross-platform (Linux, Windows, macOS)

### Core Dependencies
```
pdfplumber>=0.7.0,<1.0.0
requests>=2.25.0,<3.0.0
pandas>=1.3.0,<3.0.0
psutil>=5.4.0,<6.0.0
pillow>=8.0.0,<11.0.0
pypdfium2>=4.0.0,<5.0.0
beautifulsoup4>=4.9.0,<5.0.0
```

## File Structure Portability

### Standalone Usage
When copying to another project, include these files:
```
main.py
analyze_pdf.py
typhoon_extraction.py
advisory_scraper.py
scrape_bulletin.py
requirements.txt
```

### Optional Files
```
INTEGRATION_NOTES.md  # Documentation
PORTABILITY.md        # This file
```

### Not Required for Celery
```
bin/                  # Sample data
dataset/              # Test PDFs
example_*.py          # Example scripts
```

## Usage Examples

### Direct Usage (Standalone)
```bash
# Analyze from URL
python main.py https://example.com/bulletin.html

# Analyze from local file
python main.py /path/to/bulletin.html

# With low CPU mode
python main.py --low-cpu https://example.com/bulletin.html

# With metrics
python main.py --metrics https://example.com/bulletin.html
```

### Programmatic Usage (Celery)
```python
from main import analyze_pdf_and_advisory_parallel

# In your Celery task
def process_bulletin(pdf_url, use_low_cpu=False):
    try:
        data = analyze_pdf_and_advisory_parallel(
            pdf_url, 
            low_cpu_mode=use_low_cpu,
            verbose=False  # Disable stdout logging for Celery
        )
        return {
            'success': True,
            'data': data
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
```

## Platform-Specific Notes

### Ubuntu/Debian Installation
```bash
# System dependencies (if needed for PDF processing)
sudo apt-get update
sudo apt-get install -y python3-dev libpoppler-cpp-dev

# Python dependencies
pip install -r requirements.txt
```

### CPU Throttling Notes

**On Linux/Ubuntu (Recommended):**
- Uses `os.nice(10)` to lower process priority
- Background thread monitors CPU usage
- Dynamically introduces sleep delays

**On Windows:**
- `os.nice()` is skipped (not available)
- Background thread still monitors and throttles
- Less effective but still functional

**On Containers (Docker/K8s):**
- May require elevated permissions for `os.nice()`
- If permission denied, throttling continues without nice
- Set `--low-cpu` flag to enable throttling

## Thread Safety

- ✅ `ThreadPoolExecutor` is thread-safe
- ✅ No shared mutable state
- ✅ Each task uses independent file handles
- ✅ Temporary files use unique names
- ✅ stdout redirection is task-local

## Memory Considerations

**Per Task Memory Usage:**
- PDF parsing: ~50-100MB
- Advisory scraping: ~10-20MB
- **Total:** ~100-150MB per concurrent task

**Celery Worker Recommendations:**
- Limit concurrent tasks based on available memory
- Use `worker_max_tasks_per_child` to prevent memory leaks
- Monitor worker memory usage

## Testing Compatibility

```bash
# Test on Python 3.8.10
python3.8 -m py_compile main.py analyze_pdf.py typhoon_extraction.py

# Test imports
python3.8 -c "from main import analyze_pdf_and_advisory_parallel; print('✓ Imports OK')"

# Test basic functionality
python3.8 main.py --help
```

## Known Limitations

1. **Default HTML Path**
   - `main.py` defaults to `bin/PAGASA.html` if no argument provided
   - For Celery, always pass explicit URL/path arguments

2. **Random Selection**
   - `analyze_pdf.py --random` requires `dataset/pdfs/` directory
   - Not relevant for Celery tasks (pass specific PDFs)

3. **Process Priority**
   - `os.nice()` may require elevated permissions in containers
   - Fails gracefully if permissions denied

## Troubleshooting

### "ModuleNotFoundError"
```bash
pip install -r requirements.txt
```

### "Permission denied" for os.nice()
- Run without `--low-cpu` flag, or
- Grant CAP_SYS_NICE capability in containers

### Celery task timeout
- Increase `task_time_limit` in Celery config
- Consider using `--low-cpu` to reduce contention

## Contact & Support

For issues specific to Celery integration or Ubuntu deployment, ensure:
1. All dependencies are installed
2. Python version is 3.8.10 or higher
3. File paths are accessible to Celery worker
4. Network access is available for advisory scraper
