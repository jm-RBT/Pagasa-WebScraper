---
applyTo: '**/*.py'
---

# Copilot Instructions for Pagasa WebScraper

## Overview
This repository is designed for parsing, analyzing, and processing meteorological datasets from PAGASA. The codebase includes tools for data extraction, machine learning pipelines, and table parsing. The following instructions will help AI coding agents contribute effectively to this project.

## Project Structure
- **`data_extractor.py`**: Handles data extraction from raw sources.
- **`ml_pipeline.py`**: Contains machine learning workflows for processing and analyzing data.
- **`table_parser.py`**: Focuses on parsing tabular data from various formats.
- **`bin/`**: Stores intermediate processed data files.
- **`dataset/`**: Contains raw and processed datasets organized by year and storm ID.
- **`requirements.txt`**: Lists Python dependencies for the project.

## Key Conventions
1. **Python Version**: Use Python 3.8.10 for compatibility.
2. **Data Parsing**: Follow modular and reusable design patterns for parsing logic. Avoid hardcoding paths or values.
3. **ML Pipelines**: Ensure that machine learning models are trained and evaluated using reproducible scripts.
4. **File Naming**: Use descriptive and consistent names for scripts and datasets.
5. **Testing**: Write unit tests for all new functions and modules. Place tests in the same file or a dedicated `tests/` directory.

## Developer Workflows
### Setting Up the Environment
1. Create and activate a virtual environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   ```
2. Install dependencies (ensure you are using the virtual environment's pip):
   ```powershell
   .\venv\Scripts\pip install -r requirements.txt
   ```
3. Verify the installation:
   ```powershell
   python verify_install.py
   ```

### Running Scripts
- Ensure the virtual environment is activated before running any script.
- Extract data:
  ```powershell
  python data_extractor.py
  ```
- Parse tables:
  ```powershell
  python table_parser.py
  ```
- Run the ML pipeline:
  ```powershell
  python ml_pipeline.py
  ```

### Debugging
- Use `debug_coords.py` and `debug_grid.py` for debugging coordinate and grid-related issues.
- Log outputs to `bin/` for intermediate inspection.

## Integration Points
- **External Dependencies**: Ensure all dependencies are listed in `requirements.txt`.
- **Cross-Component Communication**: Scripts share data through the `bin/` directory and `dataset/` folder. Maintain consistent formats.

## Examples
### Adding a New Dataset
1. Place the dataset in the `dataset/` folder under the appropriate year and storm ID.
2. Update the parsing logic in `data_extractor.py` if necessary.

### Modifying the ML Pipeline
1. Edit `ml_pipeline.py` to include new preprocessing or model steps.
2. Test the pipeline end-to-end before committing changes.

## Behavioral Rules for AI Agents
- **DO**:
  - Follow Pythonic best practices.
  - Write clean, maintainable, and well-documented code.
  - Request explicit permission before running commands or modifying files.
- **DO NOT**:
  - Execute commands without user approval.
  - Install packages automatically.
  - Make irreversible changes without confirmation.

## Maintainer
User