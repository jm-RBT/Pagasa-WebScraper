"""
Dependency verification script for PAGASA WebScraper project.

This script verifies that all required dependencies from requirements.txt
are properly installed and importable in the current Python environment.
"""

import sys
import logging
from typing import Dict, List, Tuple, Optional

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("verifier")


def check_package_version(
    package_name: str,
    version_attr: str = "__version__"
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Attempt to import a package and retrieve its version.

    Args:
        package_name: The name of the package to import
        version_attr: The attribute name to retrieve version (default: "__version__")

    Returns:
        A tuple of (success: bool, version: Optional[str], error_msg: Optional[str])
    """
    try:
        module = __import__(package_name)
        version = getattr(module, version_attr, "unknown")
        return (True, str(version), None)
    except ImportError as e:
        return (False, None, str(e))
    except Exception as e:
        return (True, "unknown", str(e))


def verify_core_dependencies() -> Dict[str, Tuple[bool, Optional[str]]]:
    """
    Verify core dependencies: pdfplumber, requests, pandas, psutil.

    Returns:
        Dictionary mapping package names to (success: bool, version: Optional[str])
    """
    results: Dict[str, Tuple[bool, Optional[str]]] = {}
    
    logger.info("Verifying core dependencies...")
    
    # pdfplumber
    success, version, error = check_package_version("pdfplumber")
    results["pdfplumber"] = (success, version)
    if success:
        logger.info(f"✓ pdfplumber version: {version}")
    else:
        logger.error(f"✗ pdfplumber import failed: {error}")
    
    # requests
    success, version, error = check_package_version("requests")
    results["requests"] = (success, version)
    if success:
        logger.info(f"✓ requests version: {version}")
    else:
        logger.error(f"✗ requests import failed: {error}")
    
    # pandas
    success, version, error = check_package_version("pandas")
    results["pandas"] = (success, version)
    if success:
        logger.info(f"✓ pandas version: {version}")
    else:
        logger.error(f"✗ pandas import failed: {error}")
    
    # psutil
    success, version, error = check_package_version("psutil")
    results["psutil"] = (success, version)
    if success:
        logger.info(f"✓ psutil version: {version}")
    else:
        logger.error(f"✗ psutil import failed: {error}")
    
    return results


def verify_ml_dependencies() -> Dict[str, Tuple[bool, Optional[str]]]:
    """
    Verify ML dependencies: torch, transformers, pillow, pypdfium2, timm.

    Returns:
        Dictionary mapping package names to (success: bool, version: Optional[str])
    """
    results: Dict[str, Tuple[bool, Optional[str]]] = {}
    
    logger.info("Verifying ML dependencies...")
    
    # torch
    try:
        import torch
        version = torch.__version__
        results["torch"] = (True, version)
        logger.info(f"✓ torch version: {version}")
        logger.info(f"  CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            logger.info(f"  CUDA version: {torch.version.cuda}")
    except ImportError as e:
        results["torch"] = (False, None)
        logger.error(f"✗ torch import failed: {e}")
    
    # transformers
    try:
        import transformers
        from transformers import TableTransformerForObjectDetection
        version = transformers.__version__
        results["transformers"] = (True, version)
        logger.info(f"✓ transformers version: {version}")
        logger.info("  TableTransformerForObjectDetection imported successfully")
    except ImportError as e:
        results["transformers"] = (False, None)
        logger.error(f"✗ transformers import failed: {e}")
    
    # pillow (PIL)
    try:
        import PIL
        from PIL import Image
        version = PIL.__version__
        results["pillow"] = (True, version)
        logger.info(f"✓ pillow version: {version}")
    except ImportError as e:
        results["pillow"] = (False, None)
        logger.error(f"✗ pillow import failed: {e}")
    
    # pypdfium2
    try:
        import pypdfium2
        try:
            version = pypdfium2.__version__
        except AttributeError:
            try:
                version = str(pypdfium2.get_version())
            except (AttributeError, TypeError):
                version = "unknown"
        results["pypdfium2"] = (True, version)
        logger.info(f"✓ pypdfium2 version: {version}")
    except ImportError as e:
        results["pypdfium2"] = (False, None)
        logger.error(f"✗ pypdfium2 import failed: {e}")
    
    # timm
    success, version, error = check_package_version("timm")
    results["timm"] = (success, version)
    if success:
        logger.info(f"✓ timm version: {version}")
    else:
        logger.error(f"✗ timm import failed: {error}")
    
    return results


def verify() -> None:
    """
    Main verification function that checks all dependencies.

    Verifies both core and ML dependencies, logs results, and exits with
    appropriate status code (0 for success, 1 for failure).
    """
    logger.info("=" * 60)
    logger.info("PAGASA WebScraper Dependency Verification")
    logger.info("=" * 60)
    
    all_results: Dict[str, Tuple[bool, Optional[str]]] = {}
    
    # Verify core dependencies
    core_results = verify_core_dependencies()
    all_results.update(core_results)
    
    logger.info("")
    
    # Verify ML dependencies
    ml_results = verify_ml_dependencies()
    all_results.update(ml_results)
    
    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("Verification Summary")
    logger.info("=" * 60)
    
    failed_packages: List[str] = []
    successful_packages: List[str] = []
    
    for package, (success, version) in all_results.items():
        if success:
            successful_packages.append(package)
        else:
            failed_packages.append(package)
    
    logger.info(f"✓ Successfully verified: {len(successful_packages)}/{len(all_results)} packages")
    
    if failed_packages:
        logger.error(f"✗ Failed to import: {', '.join(failed_packages)}")
        logger.error("")
        logger.error("To fix missing dependencies, run:")
        logger.error("  pip install -r requirements.txt")
        logger.info("=" * 60)
        sys.exit(1)
    else:
        logger.info("✓ All dependencies are properly installed!")
        logger.info("=" * 60)
        sys.exit(0)


if __name__ == "__main__":
    verify()
