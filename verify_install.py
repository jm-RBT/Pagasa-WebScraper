import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verifier")

def verify():
    logger.info("Attempting to import ML dependencies...")
    try:
        import torch
        logger.info(f"Torch version: {torch.__version__}")
        logger.info(f"CUDA available: {torch.cuda.is_available()}")
        
        from transformers import TableTransformerForObjectDetection
        logger.info("Transformers imported successfully.")
        
        import pypdfium2
        try:
            logger.info(f"pypdfium2 version: {pypdfium2.get_version()}")
        except AttributeError:
             logger.info("pypdfium2 imported (version unknown)")
        
        logger.info("All critical dependencies installed.")
    except ImportError as e:
        logger.error(f"Import failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    verify()
