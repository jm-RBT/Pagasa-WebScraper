import argparse
import json
import logging
import sys
import concurrent.futures
from typing import Dict, List, Any

import pdfplumber
import pypdfium2 as pdfium
from PIL import Image

from ml_table_parser import MLTableParser
from table_parser import TableParser, CONFIG, HeaderMatcher
from data_extractor import DataExtractor

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

import requests
import io
import tempfile
import os

def download_pdf(source: str) -> str:
    """Downloads PDF from URL to a temporary file and returns path."""
    if source.startswith("http"):
        logger.info(f"Downloading PDF from {source}...")
        response = requests.get(source)
        response.raise_for_status()
        
        # Create temp file
        fd, path = tempfile.mkstemp(suffix=".pdf")
        with os.fdopen(fd, 'wb') as f:
            f.write(response.content)
        return path
    return source

def get_target_pages(pdf_path: str) -> List[int]:
    """
    Scans the PDF quickly using pdfplumber to find pages that likely contain relevant tables.
    Returns 0-indexed page numbers.
    """
    target_pages = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if not text: continue
                
                # Heuristics:
                # 1. Look for "WIND SIGNALS" table
                if "WIND SIGNALS" in text.upper() or "TCWS" in text.upper():
                    target_pages.append(i)
                # 2. Look for "Forecast" / "Location"
                elif "LOCATION OF CENTER" in text.upper():
                    target_pages.append(i)
                    
    except Exception as e:
        logger.error(f"Error during pre-scan: {e}")
        
    return list(set(target_pages))

def get_words_from_page(pdf_path: str, page_index: int) -> List[Dict]:
    """
    Extracts words with bounding boxes using pdfplumber.
    """
    words = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
             if page_index < len(pdf.pages):
                 page = pdf.pages[page_index]
                 words = page.extract_words()
    except Exception:
        pass
    return words

def render_page_to_image(pdf_path: str, page_index: int, scale=2.0) -> Image.Image:
    """
    Renders a specific PDF page to valid PIL Image using pypdfium2.
    scale=2.0 roughly equals 144 DPI (72 * 2).
    """
    pdf = pdfium.PdfDocument(pdf_path)
    page = pdf[page_index]
    bitmap = page.render(scale=scale) # Returns PIL image or bitmap
    pil_image = bitmap.to_pil()
    return pil_image

def ml_parse_pipeline(source: str):
    """
    Main pipeline:
    1. Identify target pages (Fast).
    2. Rasterize & ML Parse target pages (Slow but targeted).
    3. Fallback/Integrate with Regex Parser for full structure.
    """
    # Handle download if needed
    local_path = download_pdf(source)
    is_temp = local_path != source
    
    logger.info(f"Starting ML Pipeline for: {local_path}")
    
    try:
        # 1. Pre-scan
        target_page_indices = get_target_pages(local_path)
        if not target_page_indices:
            logger.warning("No target pages found by keywords. creating full scan fallback or skipping.")
            # Optional: fallback to first 3 pages?
            target_page_indices = [0, 1, 2]
    
        logger.info(f"Target pages for ML processing: {target_page_indices}")
        
        all_tables = []
        
        # Initialize ML Parser (will lazy load deps)
        ml_parser = MLTableParser()
    
        for page_idx in target_page_indices:
            logger.info(f"Processing Page {page_idx + 1}...")
            
            # 2a. Get Image (Visual)
            # Scale 2.0 (approx 150 DPI) is good balance for speed/acc
            image = render_page_to_image(local_path, page_idx, scale=2.0)
            img_w, img_h = image.size
            
            # 2b. Get Words (Textual) + Page Size
            words = []
            page_w, page_h = 0, 0
            try:
                with pdfplumber.open(local_path) as pdf:
                     if page_idx < len(pdf.pages):
                         page = pdf.pages[page_idx]
                         words = page.extract_words()
                         page_w = page.width
                         page_h = page.height
            except Exception:
                pass
            
            # Calculate Dynamic Scale Factors
            scale_x = img_w / page_w if page_w else 2.0
            scale_y = img_h / page_h if page_h else 2.0
            
            scaled_words = []
            for w in words:
                scaled_words.append({
                    "text": w["text"],
                    "x0": w["x0"] * scale_x,
                    "top": w["top"] * scale_y,
                    "x1": w["x1"] * scale_x,
                    "bottom": w["bottom"] * scale_y
                })
    
            # 2c. ML Inference
            # This returns a Grid of Strings (List[List[str]])
            grid = ml_parser.parse_page(image, scaled_words)
            
            if grid:
                all_tables.append({
                    "page_number": page_idx + 1,
                    "tables": [grid] # Wrap in list to match expected structure
                })
                
        # 3. Post-process
        logger.info("Structuring extracted data using DataExtractor...")
        
        # New Extractor
        extractor = DataExtractor()
        structured_result = extractor.extract_from_grids(all_tables)
        
        # Add Metadata
        structured_result["meta"]["source"] = source
        structured_result["meta"]["method"] = "ML-Hybrid-Refined"
        structured_result["meta"]["raw_grids"] = all_tables # For debug
        
        return structured_result

    finally:
        # Cleanup temp file if created
        if is_temp and os.path.exists(local_path):
            try:
                os.remove(local_path)
            except:
                pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PAGASA ML Table Parser")
    parser.add_argument("source", help="Path to PDF file")
    
    args = parser.parse_args()
    
    try:
        result = ml_parse_pipeline(args.source)
        print(json.dumps(result, indent=4, default=str))
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
