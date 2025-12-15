from pdfplumber import open as open_pdf
from ml_pipeline import render_page_to_image, get_words_from_page
from PIL import ImageDraw
import sys

def debug_coords(pdf_path, page_idx=0):
    print(f"Visualizing coords for {pdf_path}")
    
    # Render Image
    img = render_page_to_image(pdf_path, page_idx, scale=2.0)
    draw = ImageDraw.Draw(img)
    
    # Get Words
    words = get_words_from_page(pdf_path, page_idx) # 72 DPI
    
    scale = 2.0
    
    for w in words:
        # pdfplumber: x0, top, x1, bottom
        box = [
            w['x0'] * scale,
            w['top'] * scale,
            w['x1'] * scale,
            w['bottom'] * scale
        ]
        draw.rectangle(box, outline="red", width=1)
        
    img.save("debug_vis.jpg")
    print("Saved debug_vis.jpg")

if __name__ == "__main__":
    debug_coords("dataset/TCB_4.pdf", 0)
