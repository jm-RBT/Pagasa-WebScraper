"""
Analyze a single PAGASA PDF bulletin and extract data.
This is a library module for programmatic use.
"""

from .typhoon_extraction import TyphoonBulletinExtractor
import sys
import tempfile
import requests
import hashlib
from pathlib import Path
from urllib.parse import urlparse


def calculate_file_hash(filepath):
    """Calculate SHA256 hash of a file"""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def check_pdf_for_suspicious_features(filepath):
    """Check for suspicious PDF features that may indicate malware"""
    suspicious_features = []
    content = None
    
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
        
        # Check for JavaScript in PDF (often malicious)
        if b'/JavaScript' in content or b'/JS' in content:
            suspicious_features.append("Contains JavaScript")
        
        # Check for embedded executables
        if b'/EmbeddedFile' in content:
            suspicious_features.append("Contains embedded files")
        
        # Check for OpenAction (auto-execute on open)
        if b'/OpenAction' in content:
            suspicious_features.append("Contains auto-execute actions")
        
        # Check for suspicious launch actions
        if b'/Launch' in content or b'/SubmitForm' in content:
            suspicious_features.append("Contains form/launch actions")
        
        # Check for suspicious XObjects
        if b'/XObject' in content and b'/EmbeddedFile' in content:
            suspicious_features.append("Contains suspicious embedded objects")
        
    except Exception as e:
        print(f"[ERROR] Feature check error: {e}", file=sys.stderr)
        return []
    finally:
        # Free memory explicitly
        content = None
    
    return suspicious_features


def check_pdf_safety(filepath):
    """
    Check if PDF is safe using built-in methods (no system installations required).
    Returns True if safe, False otherwise.
    """
    # 1. File size check
    file_size = Path(filepath).stat().st_size
    
    if file_size > 100 * 1024 * 1024:  # 100 MB limit
        print(f"[WARNING] Large file: {file_size:,} bytes", file=sys.stderr)
        return False
    
    # 2. PDF structure validation
    try:
        with open(filepath, 'rb') as f:
            header = f.read(4)
            if header != b'%PDF':
                print("[ERROR] Not a valid PDF file", file=sys.stderr)
                return False
    except Exception as e:
        print(f"[ERROR] PDF validation error: {e}", file=sys.stderr)
        return False
    
    # 3. Check for suspicious features
    suspicious = check_pdf_for_suspicious_features(filepath)
    if suspicious:
        print(f"[WARNING] Found suspicious features:", file=sys.stderr)
        for feature in suspicious:
            print(f"  - {feature}", file=sys.stderr)
        return False
    
    return True


def analyze_pdf(pdf_url_or_path):
    """
    Analyze a PDF using the TyphoonBulletinExtractor.
    
    Args:
        pdf_url_or_path: URL or local path to PDF file
        
    Returns:
        Dictionary of extracted data, or None on failure
    """
    # Download PDF if it's a URL (TyphoonBulletinExtractor requires local files)
    temp_file = None
    pdf_path = pdf_url_or_path
    
    if pdf_url_or_path.startswith('http://') or pdf_url_or_path.startswith('https://'):
        try:
            response = requests.get(pdf_url_or_path, timeout=30)
            response.raise_for_status()
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                tmp.write(response.content)
                temp_file = tmp.name
                pdf_path = temp_file
            
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Error downloading PDF: {e}", file=sys.stderr)
            return None
    else:
        # Verify local file exists
        if not Path(pdf_url_or_path).exists():
            print(f"[ERROR] Local file not found: {pdf_url_or_path}", file=sys.stderr)
            return None
    
    # Check PDF safety
    if not check_pdf_safety(pdf_path):
        if temp_file:
            try:
                Path(temp_file).unlink()
            except Exception:
                pass
        return None
    
    # Analyze the PDF
    extractor = TyphoonBulletinExtractor()
    
    try:
        data = extractor.extract_from_pdf(pdf_path)
        return data
    except Exception as e:
        print(f"[ERROR] Error analyzing PDF: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return None
    finally:
        del extractor
        # Clean up temporary file if we created one
        if temp_file:
            try:
                Path(temp_file).unlink()
            except Exception as e:
                print(f"[WARNING] Could not delete temp file: {e}", file=sys.stderr)
