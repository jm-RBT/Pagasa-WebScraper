import logging
import json
import sys
from ml_pipeline import render_page_to_image, get_words_from_page
from ml_table_parser import MLTableParser

logging.basicConfig(level=logging.INFO)

def debug_grid(pdf_path, page_idx=0):
    print(f"Debugging {pdf_path} Page {page_idx}")
    
    ml_parser = MLTableParser()
    
    image = render_page_to_image(pdf_path, page_idx, scale=2.0)
    img_w, img_h = image.size
    
    words = []
    page_w, page_h = 0, 0
    import pdfplumber
    try:
        with pdfplumber.open(pdf_path) as pdf:
             if page_idx < len(pdf.pages):
                 page = pdf.pages[page_idx]
                 words = page.extract_words()
                 page_w = page.width
                 page_h = page.height
    except Exception:
        pass
    
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
        
    grid = ml_parser.parse_page(image, scaled_words)
    
    print("\n--- GRID OUTPUT ---")
    for i, row in enumerate(grid):
        print(f"Row {i}: {row}")
    print("-------------------")

if __name__ == "__main__":
    debug_grid("dataset/TCB_4.pdf", 0)
