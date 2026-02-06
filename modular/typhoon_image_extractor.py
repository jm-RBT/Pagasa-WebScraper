"""
Typhoon Image Extractor - Modular library version.

Extract typhoon track images from HTML/URL or PDF.
This module provides two methods for extracting typhoon track images:
1. From live URL/HTML by locating the image element within tcwb-{number} sections
2. From PDF files using precise page coordinates (fallback method)
"""

import io
import sys
import requests
from pathlib import Path
from typing import Optional, Tuple, Union
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import pdfplumber
from PIL import Image


class TyphoonImageExtractor:
    """Extract typhoon track images from HTML pages or PDF files"""
    
    def __init__(self):
        """Initialize the extractor"""
        pass
    
    def extract_image_from_html(
        self, 
        source: str, 
        tab_index: int = 1
    ) -> Optional[io.BytesIO]:
        """
        Extract typhoon track image from HTML page (live URL or local file).
        
        This method locates the tcwb-{tab_index} element and extracts the
        typhoon track image from within it.
        
        Args:
            source: URL or local file path to HTML content
            tab_index: Tab index number (default: 1 for first typhoon)
            
        Returns:
            BytesIO stream containing image data, or None if extraction fails
        """
        # Load HTML content
        try:
            if source.startswith('http://') or source.startswith('https://'):
                response = requests.get(source, timeout=30)
                response.raise_for_status()
                html_content = response.text
                base_url = source
            else:
                filepath = Path(source).resolve()
                if not filepath.exists():
                    print(f"[ERROR] HTML file not found: {source}", file=sys.stderr)
                    return None
                with open(filepath, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                # For local files, use the directory as base path
                base_url = None  # Will handle relative paths differently
        except Exception as e:
            print(f"[ERROR] Error loading HTML: {e}", file=sys.stderr)
            return None
        
        # Parse HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find the tab panel with id=tcwb-{tab_index}
        tab_id = f'tcwb-{tab_index}'
        tab_panel = soup.find('div', id=tab_id)
        
        if not tab_panel:
            print(f"[ERROR] Tab panel '{tab_id}' not found in HTML", file=sys.stderr)
            return None
        
        # Find the image within this tab panel
        # Look for img tag with class containing 'image-preview' or 'img-responsive'
        img_tag = tab_panel.find('img', class_=lambda x: x and ('image-preview' in x or 'img-responsive' in x))
        
        if not img_tag:
            # Fallback: find any img tag in the tab panel
            img_tag = tab_panel.find('img')
        
        if not img_tag or not img_tag.get('src'):
            print(f"[ERROR] No image found in tab panel '{tab_id}'", file=sys.stderr)
            return None
        
        # Get image URL
        img_src = img_tag.get('src')
        
        # Handle relative URLs
        if not img_src.startswith('http'):
            # For local HTML files with relative paths
            if base_url and source.startswith('http'):
                img_url = urljoin(base_url, img_src)
            else:
                # Local file: resolve relative to HTML file location
                html_dir = Path(source).resolve().parent
                img_path = html_dir / img_src
                if not img_path.exists():
                    print(f"[ERROR] Image file not found: {img_path}", file=sys.stderr)
                    return None
                # Read local image file
                with open(img_path, 'rb') as f:
                    img_data = f.read()
                return io.BytesIO(img_data)
        else:
            img_url = img_src
        
        # Download the image
        try:
            response = requests.get(img_url, timeout=30)
            response.raise_for_status()
            return io.BytesIO(response.content)
        except Exception as e:
            print(f"[ERROR] Error downloading image from {img_url}: {e}", file=sys.stderr)
            return None
    
    def extract_image_from_pdf(
        self, 
        pdf_path: str,
        page_number: int = 0
    ) -> Optional[io.BytesIO]:
        """
        Extract typhoon track image from PDF by cropping the region adjacent to
        Location/Intensity/Movement data.
        
        The typhoon track map is on the first page, on the RIGHT SIDE at the same
        vertical level as the "Location", "Intensity", and "Movement" text fields.
        
        Args:
            pdf_path: Path to PDF file
            page_number: Page number to extract from (default: 0 for first page)
            
        Returns:
            BytesIO stream containing image data, or None if extraction fails
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if page_number >= len(pdf.pages):
                    print(f"[ERROR] Page {page_number} not found in PDF", file=sys.stderr)
                    return None
                
                page = pdf.pages[page_number]
                
                try:
                    words = page.extract_words()
                    location_y = None
                    intensity_y = None
                    movement_y = None
                    
                    # Find the key text positions
                    header_bottom_y = None
                    for word in words:
                        if 'Location' in word['text'] and word['x0'] < 100:
                            location_y = word['top']
                        elif word['text'] == 'Intensity' and word['x0'] < 100:
                            intensity_y = word['top']
                        elif 'Movement' in word['text'] and word['x0'] < 150:
                            movement_y = word['top']
                        
                        # Track header/first row bottom - text in the top 150 pixels
                        if word['top'] < 150:
                            if header_bottom_y is None or word['bottom'] > header_bottom_y:
                                header_bottom_y = word['bottom']
                    
                    # Find the "TRACK AND INTENSITY FORECAST" heading to use as bottom boundary
                    forecast_heading_y = None
                    for word in words:
                        if word['text'] == 'TRACK':
                            # Check if this is part of the forecast heading
                            nearby_words = [w for w in words if abs(w['top'] - word['top']) < 5]
                            nearby_text = ' '.join([w['text'] for w in sorted(nearby_words, key=lambda x: x['x0'])])
                            if 'INTENSITY' in nearby_text and 'FORECAST' in nearby_text:
                                forecast_heading_y = word['top']
                                break
                    
                    if location_y and movement_y:
                        # Define the crop region for the track map
                        y_top = location_y
                        
                        # Bottom boundary: stop at the "TRACK AND INTENSITY FORECAST" heading
                        if forecast_heading_y:
                            y_bottom = forecast_heading_y - 5
                        else:
                            y_bottom = max(movement_y, intensity_y if intensity_y else movement_y) + 80
                        
                        # X coordinates
                        y_min = location_y - 5
                        y_max = movement_y + 50
                        
                        # Find all words in this Y range that are DATA (not labels)
                        data_words = []
                        for word in words:
                            if y_min <= word['top'] <= y_max:
                                # Skip the label words themselves
                                if word['text'] not in ['Location', 'Intensity', 'Movement']:
                                    # Only include substantial words (not punctuation)
                                    if len(word['text']) > 1:
                                        data_words.append(word)
                        
                        if data_words:
                            # Find the rightmost data value
                            rightmost_data_x = max(w['x1'] for w in data_words)
                            # Start from the right edge of the data cells, with a small margin
                            x_left = rightmost_data_x + 10
                        else:
                            # Fallback: use middle of page
                            x_left = page.width * 0.50
                        
                        x_right = page.width - 40   # Leave small margin on right
                        
                        # Crop and convert to image at higher resolution for clarity
                        cropped_region = page.crop((x_left, y_top, x_right, y_bottom))
                        pil_image = cropped_region.to_image(resolution=300)
                        
                        # Save to BytesIO
                        img_bytes = io.BytesIO()
                        pil_image.save(img_bytes, format='PNG')
                        img_bytes.seek(0)
                        
                        return img_bytes
                    
                except Exception as e:
                    print(f"[ERROR] Error using text-based positioning: {e}", file=sys.stderr)
                
                # Fallback: Try to extract from embedded images if text-based approach fails
                if page.images:
                    # Get the last (usually largest/main) image
                    img = page.images[-1]
                    
                    # Extract image using coordinates
                    x0, top, x1, bottom = img['x0'], img['top'], img['x1'], img['bottom']
                    cropped = page.crop((x0, top, x1, bottom))
                    pil_image = cropped.to_image(resolution=300)
                    
                    img_bytes = io.BytesIO()
                    pil_image.save(img_bytes, format='PNG')
                    img_bytes.seek(0)
                    
                    return img_bytes
                
                print(f"[ERROR] Could not extract image from PDF", file=sys.stderr)
                return None
                
        except Exception as e:
            print(f"[ERROR] Error extracting image from PDF: {e}", file=sys.stderr)
            return None
    
    def save_image(self, img_stream: io.BytesIO, save_path: str) -> bool:
        """
        Save image stream to file.
        
        Args:
            img_stream: BytesIO stream containing image data
            save_path: Path to save the image
            
        Returns:
            True if successful, False otherwise
        """
        try:
            img_stream.seek(0)
            with open(save_path, 'wb') as f:
                f.write(img_stream.read())
            img_stream.seek(0)  # Reset for potential reuse
            return True
        except Exception as e:
            print(f"[ERROR] Error saving image: {e}", file=sys.stderr)
            return False
    
    def extract_image(
        self,
        source: str,
        tab_index: int = 1,
        save_path: Optional[str] = None
    ) -> Union[io.BytesIO, Tuple[io.BytesIO, str], None]:
        """
        Extract typhoon track image from source (auto-detect HTML/URL vs PDF).
        
        Args:
            source: URL, HTML file path, or PDF file path
            tab_index: Tab index for HTML extraction (default: 1)
            save_path: Optional path to save image. If provided, also returns the path
            
        Returns:
            - BytesIO stream if save_path is None
            - Tuple (BytesIO stream, save_path) if save_path is provided
            - None if extraction fails
        """
        # Determine source type
        is_pdf = False
        
        if source.startswith('http://') or source.startswith('https://'):
            # Check if URL points to PDF
            if source.lower().endswith('.pdf'):
                is_pdf = True
        else:
            # Local file - check extension
            if Path(source).suffix.lower() == '.pdf':
                is_pdf = True
        
        # Extract image using appropriate method
        if is_pdf:
            img_stream = self.extract_image_from_pdf(source)
        else:
            img_stream = self.extract_image_from_html(source, tab_index)
        
        if not img_stream:
            return None
        
        # Save if requested
        if save_path:
            if self.save_image(img_stream, save_path):
                return (img_stream, save_path)
            else:
                return None
        
        return img_stream
