"""
Analyze a single PAGASA PDF bulletin and extract data.
This is a library module for programmatic use.
"""

from .typhoon_extraction import TyphoonBulletinExtractor
import sys
import tempfile
import requests
import hashlib
import time
import psutil
import os
from pathlib import Path
from urllib.parse import urlparse


def cpu_throttle(process, target_cpu_percent=30, sample_interval=0.1):
    """
    CPU throttling function - pauses execution if CPU usage exceeds target.
    This reduces CPU consumption while still completing the task.
    
    Args:
        process: psutil.Process object
        target_cpu_percent: Target CPU percentage (default 30%)
        sample_interval: Time between CPU checks in seconds
    """
    current_cpu = process.cpu_percent(interval=sample_interval)
    
    if current_cpu > target_cpu_percent:
        # Calculate sleep time proportional to how much we're over the target
        # More aggressive sleeping when we're further over the target
        overage_ratio = current_cpu / target_cpu_percent
        sleep_time = 0.1 * overage_ratio
        time.sleep(sleep_time)


def continuous_cpu_throttle(process, target_cpu_percent=30, check_interval=0.01):
    """
    Context manager for continuous CPU throttling during operations.
    Uses process priority (nice) and periodic monitoring to limit CPU usage.
    
    Args:
        process: psutil.Process object
        target_cpu_percent: Target CPU percentage (default 30%)
        check_interval: Time between throttle checks in seconds
    
    Usage:
        with continuous_cpu_throttle(process, target_cpu_percent=30):
            # CPU-intensive operations here
            pass
    """
    import threading
    import time
    import os
    import sys
    
    class CPUThrottler:
        def __init__(self, process, target, interval):
            self.process = process
            self.target = target
            self.interval = interval
            self.running = False
            self.thread = None
            self.original_nice = None
            
        def _throttle_loop(self):
            """Background thread that monitors CPU and introduces sleep delays"""
            while self.running:
                try:
                    cpu = self.process.cpu_percent(interval=0.02)
                    
                    if cpu > self.target:
                        # Calculate how much to sleep based on overage
                        overage = (cpu - self.target) / 100.0
                        sleep_time = 0.05 * (1 + overage * 3)  # More sleep when further over
                        time.sleep(sleep_time)
                    else:
                        time.sleep(self.interval)
                except Exception:
                    break
                    
        def __enter__(self):
            # Set process to lower priority (nice value)
            # Higher nice value = lower priority
            # This is Linux/Unix specific and safely ignored on Windows
            try:
                if sys.platform != 'win32' and hasattr(os, 'nice'):
                    # On Unix/Linux, os.nice() increments the nice value and returns new value
                    # Store current nice for potential restoration
                    current_nice = os.nice(0)  # Get current nice value
                    self.original_nice = current_nice
                    # Add 10 to nice value (lower priority)
                    os.nice(10)
            except (OSError, AttributeError):
                # Silently continue if nice is not available or permission denied
                pass
            
            # Start monitoring thread
            self.running = True
            self.thread = threading.Thread(target=self._throttle_loop, daemon=True)
            self.thread.start()
            return self
            
        def __exit__(self, *args):
            self.running = False
            if self.thread:
                self.thread.join(timeout=0.5)
            
            # Note: Restoring nice value is tricky because os.nice() is additive
            # For simplicity and to avoid issues, we skip restoration
            # The process nice value will remain at the lower priority
            # This is acceptable as the script typically exits after use
    
    return CPUThrottler(process, target_cpu_percent, check_interval)


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


def analyze_pdf(pdf_url_or_path, low_cpu_mode=False):
    """
    Analyze a PDF using the TyphoonBulletinExtractor.
    
    Args:
        pdf_url_or_path: URL or local path to PDF file
        low_cpu_mode: Whether to limit CPU usage
        
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
    process = psutil.Process(os.getpid())
    
    try:
        # Apply continuous CPU throttling if enabled
        if low_cpu_mode:
            with continuous_cpu_throttle(process, target_cpu_percent=30):
                data = extractor.extract_from_pdf(pdf_path)
        else:
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
