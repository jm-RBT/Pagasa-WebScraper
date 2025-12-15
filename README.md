# Pagasa-WebScraper
POC for client requirement

## Setup

1. Create virtual environment:
```powershell
python -m venv .venv
```

2. Activate virtual environment:
```powershell
.\.venv\Scripts\Activate.ps1
```

3. Install dependencies:
```powershell
pip install -r requirements.txt
```

4. Verify installation:
```powershell
python verify_install.py
```

## Running Scripts

### Extract data:
```powershell
python data_extractor.py
```

### Parse tables:
```powershell
python table_parser.py
```

### Run the ML pipeline:
```powershell
python ml_pipeline.py
```


## Last terminal command
The terminal ran: powershell .venv\Scripts\Activate.ps1 (working directory: C:\_Files\Code_Files\Pagasa WebScraper)
