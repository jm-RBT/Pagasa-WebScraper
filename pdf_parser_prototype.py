import argparse
import io
import json
import sys
import requests
import pdfplumber
from table_parser import TableParser

def get_pdf_bytes(source: str):
    """
    Retrieves PDF content as bytes.
    Handles both local files and URLs.
    """
    if source.startswith("http://") or source.startswith("https://"):
        response = requests.get(source, timeout=30)
        response.raise_for_status()
        return io.BytesIO(response.content)
    else:
        with open(source, 'rb') as f:
            return io.BytesIO(f.read())

def parse_pdf(source: str):
    """
    Reads the PDF, extracts table arrays, and then parses them into structural JSON.
    """
    try:
        pdf_bytes = get_pdf_bytes(source)
        
        with pdfplumber.open(pdf_bytes) as pdf:
            all_tables = []
            
            for i, page in enumerate(pdf.pages):
                # Extract tables
                tables = page.extract_tables()
                if tables:
                    all_tables.append({
                        "page_number": i + 1,
                        "tables": tables
                    })
            
            # Pass the raw table data to the TableParser
            parser = TableParser(all_tables)
            structured_result = parser.parse()
            
            # Add metadata about source
            structured_result["meta"]["source_file"] = source
            
            return structured_result
            
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PAGASA PDF Table Extractor & Parser")
    parser.add_argument("source", help="Path to PDF file or public PDF URL")
    
    args = parser.parse_args()
    
    # Configure stdout to handle utf-8
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

    result = parse_pdf(args.source)
    print(json.dumps(result, indent=4, default=str))
