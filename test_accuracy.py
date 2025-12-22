#!/usr/bin/env python
"""
Accuracy test script for PDF extraction analysis.
Compares extracted data from PDFs against ground truth annotations.
Automatically finds corresponding PDF files for each annotation.

Usage: python test_accuracy.py                          # Auto-test all annotations with PDFs
       python test_accuracy.py "<bulletin_name>"        # Test specific bulletin
       python test_accuracy.py --detailed               # Detailed field-by-field results
       python test_accuracy.py --metrics                # Show detailed accuracy metrics
       python test_accuracy.py --verbose                # Show all test results (including passes)
       python test_accuracy.py "<bulletin_name>" --detailed  # Detailed results for specific bulletin

Features:
  - Automatically matches annotation files in pdfs_annotation/ with PDFs in pdfs/
  - Compares extracted fields: location, movement, windspeed, datetime
  - Provides both test-level and field-level accuracy metrics
  - Shows similarity scores for partial matches
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, Tuple, List
from typhoon_extraction_ml import TyphoonBulletinExtractor
import difflib

# Base paths
DATASET_PATH = Path("dataset")
ANNOTATIONS_PATH = DATASET_PATH / "pdfs_annotation"
PDFS_PATH = DATASET_PATH / "pdfs"


class AnnotationMatcher:
    """Helper class to find matching PDF files for annotations"""
    
    @staticmethod
    def get_pdf_path(annotation_filename: str) -> Path:
        """
        Convert annotation filename to PDF path.
        Searches for the PDF file in the corresponding storm folder.
        Example: PAGASA_22-TC08_Henry_TCA#01.json -> dataset/pdfs/pagasa-22-TC08/PAGASA_22-TC08_Henry_TCA#01.pdf
        """
        # Remove .json extension
        base_name = annotation_filename.replace(".json", "")
        
        # Extract storm ID from annotation filename
        # Format: PAGASA_YY-TCXX_Name_TCTYPE#NUM or PAGASA_YY-XXXX_Name_TCTYPE#NUM
        parts = base_name.split("_")
        
        if len(parts) >= 2:
            # Format: PAGASA_YY-TCXX or PAGASA_YY-XXXX
            year_storm = parts[0] + "_" + parts[1]
            # Convert to folder format: pagasa-YY-TCXX
            storm_folder = "pagasa-" + year_storm.lower().replace("pagasa_", "")
            
            pdf_path = PDFS_PATH / storm_folder / (base_name + ".pdf")
            
            # If direct path doesn't exist, try searching in the folder
            if not pdf_path.exists():
                search_dir = PDFS_PATH / storm_folder
                if search_dir.exists():
                    # Try to find matching PDF in folder
                    matching_pdfs = list(search_dir.glob(f"{base_name}.pdf"))
                    if matching_pdfs:
                        return matching_pdfs[0]
            
            return pdf_path
        
        return Path()


class AccuracyTester:
    """Test extraction accuracy against ground truth annotations"""
    
    def __init__(self, verbose: bool = False, detailed: bool = False):
        self.extractor = TyphoonBulletinExtractor()
        self.verbose = verbose
        self.detailed = detailed
        self.results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "partial_matches": 0,
            "errors": 0,
            "test_details": [],
            "total_fields_matched": 0,
            "total_fields_tested": 0
        }
    
    def compare_fields(self, extracted: Dict[str, Any], ground_truth: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare extracted data with ground truth.
        Dynamically checks all fields from ground truth.
        Returns detailed comparison results.
        """
        comparison = {
            "field_results": {},
            "match_count": 0,
            "total_fields": 0,
            "exact_matches": [],
            "simple_fields": [],  # Non-nested fields
            "nested_fields": []   # Nested dict/list fields
        }
        
        # Get all keys from ground truth
        for field, ground_truth_value in ground_truth.items():
            comparison["total_fields"] += 1
            extracted_value = extracted.get(field, None)
            
            # Handle nested fields (dicts with sub-keys)
            if isinstance(ground_truth_value, dict):
                comparison["nested_fields"].append(field)
                # For nested dicts, compare each sub-key
                sub_matches = 0
                sub_total = 0
                sub_results = {}
                
                for sub_key, sub_value in ground_truth_value.items():
                    sub_total += 1
                    extracted_sub = extracted_value.get(sub_key) if isinstance(extracted_value, dict) else None
                    is_match = extracted_sub == sub_value
                    
                    if is_match:
                        sub_matches += 1
                    
                    sub_results[sub_key] = {
                        "extracted": extracted_sub,
                        "ground_truth": sub_value,
                        "is_match": is_match
                    }
                
                field_match_ratio = sub_matches / sub_total if sub_total > 0 else 0
                if field_match_ratio >= 0.5:  # Consider it a match if 50%+ sub-keys match
                    comparison["match_count"] += 1
                    comparison["exact_matches"].append(field)
                
                comparison["field_results"][field] = {
                    "is_nested": True,
                    "extracted": extracted_value,
                    "ground_truth": ground_truth_value,
                    "sub_results": sub_results,
                    "match_ratio": field_match_ratio,
                    "is_match": field_match_ratio >= 0.5
                }
            else:
                # Handle simple fields (strings, numbers, etc.)
                comparison["simple_fields"].append(field)
                extracted_str = str(extracted_value).strip() if extracted_value else ""
                ground_truth_str = str(ground_truth_value).strip() if ground_truth_value else ""
                
                # Check for exact match
                is_exact_match = extracted_str.lower() == ground_truth_str.lower()
                
                # Check for partial match (substring or similarity)
                partial_match = False
                similarity_ratio = 0.0
                if extracted_str and ground_truth_str:
                    ratio = difflib.SequenceMatcher(None, extracted_str.lower(), ground_truth_str.lower()).ratio()
                    similarity_ratio = ratio
                    partial_match = ratio >= 0.7
                
                if is_exact_match:
                    comparison["match_count"] += 1
                    comparison["exact_matches"].append(field)
                
                comparison["field_results"][field] = {
                    "is_nested": False,
                    "extracted": extracted_str,
                    "ground_truth": ground_truth_str,
                    "is_match": is_exact_match,
                    "partial_match": partial_match,
                    "similarity": round(similarity_ratio, 2)
                }
        
        return comparison
    
    def test_single_file(self, annotation_filename: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Test a single PDF against its annotation.
        Returns (passed, details)
        """
        detail = {
            "annotation_file": annotation_filename,
            "pdf_file": None,
            "status": "unknown",
            "accuracy_percent": 0.0,
            "comparison": None,
            "error": None
        }
        
        try:
            # Get PDF path
            pdf_path = AnnotationMatcher.get_pdf_path(annotation_filename)
            detail["pdf_file"] = str(pdf_path)
            
            # Check if PDF exists
            if not pdf_path.exists():
                detail["status"] = "error"
                detail["error"] = f"PDF not found: {pdf_path}"
                return False, detail
            
            # Load ground truth annotation
            annotation_path = ANNOTATIONS_PATH / annotation_filename
            with open(annotation_path, 'r', encoding='utf-8') as f:
                ground_truth = json.load(f)
            
            # Extract data from PDF
            extracted = self.extractor.extract_from_pdf(str(pdf_path))
            
            if not extracted:
                detail["status"] = "error"
                detail["error"] = "Failed to extract data from PDF"
                return False, detail
            
            # Compare
            comparison = self.compare_fields(extracted, ground_truth)
            detail["comparison"] = comparison
            
            # Calculate accuracy
            accuracy = comparison["match_count"] / comparison["total_fields"] if comparison["total_fields"] > 0 else 0
            detail["accuracy_percent"] = round(accuracy * 100, 1)
            
            # Determine status based on realistic thresholds
            if accuracy >= 0.65:
                detail["status"] = "pass"
                return True, detail
            elif accuracy >= 0.58:
                detail["status"] = "warn"
                return False, detail
            else:
                detail["status"] = "fail"
                return False, detail
        
        except Exception as e:
            detail["status"] = "error"
            detail["error"] = str(e)
            return False, detail
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run tests for all annotation files"""
        annotation_files = sorted(list(ANNOTATIONS_PATH.glob("*.json")))
        
        if not annotation_files:
            print("Error: No annotation files found in", ANNOTATIONS_PATH)
            return self.results
        
        print(f"Found {len(annotation_files)} annotation files to test")
        print(f"Testing accuracy of PDF extraction...\n")
        
        for idx, annotation_file in enumerate(annotation_files, 1):
            filename = annotation_file.name
            passed, detail = self.test_single_file(filename)
            
            self.results["total_tests"] += 1
            
            if detail["status"] == "pass":
                self.results["passed"] += 1
                status_str = "PASS"
            elif detail["status"] == "warn":
                self.results["partial_matches"] += 1
                status_str = "WARN"
            elif detail["status"] == "error":
                self.results["errors"] += 1
                status_str = "ERROR"
            else:
                self.results["failed"] += 1
                status_str = "FAIL"
            
            self.results["test_details"].append(detail)
            
            if self.verbose or detail["status"] in ["error"]:
                accuracy_str = f" ({detail['accuracy_percent']:.1f}%)" if detail.get('accuracy_percent') else ""
                print(f"[{idx:3d}/{len(annotation_files)}] {status_str} - {filename}{accuracy_str}")
                if detail["error"]:
                    print(f"         Error: {detail['error']}")
            else:
                accuracy_str = f" ({detail['accuracy_percent']:.1f}%)" if detail.get('accuracy_percent') else ""
                print(f"[{idx:3d}/{len(annotation_files)}] {status_str} - {filename}{accuracy_str}")
            
            # Track field-level accuracy
            if detail["comparison"]:
                self.results["total_fields_matched"] += detail["comparison"]["match_count"]
                self.results["total_fields_tested"] += detail["comparison"]["total_fields"]
        
        return self.results
    
    def test_single_bulletin(self, bulletin_name: str) -> Dict[str, Any]:
        """Test a specific bulletin"""
        print(f"Testing bulletin: {bulletin_name}\n")
        
        # Find matching annotation files
        matching_files = list(ANNOTATIONS_PATH.glob(f"{bulletin_name}*.json"))
        
        if not matching_files:
            print(f"Error: No annotation files found for {bulletin_name}")
            return self.results
        
        print(f"Found {len(matching_files)} annotation file(s)\n")
        
        for annotation_file in matching_files:
            filename = annotation_file.name
            passed, detail = self.test_single_file(filename)
            
            self.results["total_tests"] += 1
            
            if detail["status"] == "pass":
                self.results["passed"] += 1
                status_str = "PASS"
            elif detail["status"] == "warn":
                self.results["partial_matches"] += 1
                status_str = "WARN"
            elif detail["status"] == "error":
                self.results["errors"] += 1
                status_str = "ERROR"
            else:
                self.results["failed"] += 1
                status_str = "FAIL"
            
            self.results["test_details"].append(detail)
            
            accuracy_str = f" ({detail['accuracy_percent']:.1f}%)" if detail.get('accuracy_percent') else ""
            print(f"{status_str} - {filename}{accuracy_str}")
            if detail["error"]:
                print(f"  Error: {detail['error']}")
            elif detail["comparison"]:
                fields_info = f"{detail['comparison']['match_count']}/{detail['comparison']['total_fields']} fields matched"
                print(f"  {fields_info}")
                # Track field-level accuracy
                self.results["total_fields_matched"] += detail["comparison"]["match_count"]
                self.results["total_fields_tested"] += detail["comparison"]["total_fields"]
        
        return self.results
    
    def print_summary(self):
        """Print test summary"""
        results = self.results
        print("\n" + "="*80)
        print("[ACCURACY TEST SUMMARY]")
        print("="*80)
        print(f"Total tests:       {results['total_tests']}")
        print(f"Passed:            {results['passed']}")
        print(f"Warnings:          {results['partial_matches']}")
        print(f"Failed:            {results['failed']}")
        print(f"Errors:            {results['errors']}")
        
        if results['total_tests'] > 0:
            pass_rate = (results['passed'] / results['total_tests'] * 100)
            print(f"\nPass rate:         {pass_rate:.1f}%")
        
        # Calculate overall field-level accuracy
        if results['total_fields_tested'] > 0:
            overall_accuracy = results['total_fields_matched'] / results['total_fields_tested'] * 100
            print(f"\nField accuracy:    {overall_accuracy:.1f}%")
            print(f"Fields matched:    {results['total_fields_matched']}/{results['total_fields_tested']}")
        
        print("="*80)
    
    def print_detailed_results(self):
        """Print detailed field-by-field results"""
        if not self.results["test_details"]:
            return
        
        print("\n" + "="*80)
        print("[DETAILED FIELD-BY-FIELD RESULTS]")
        print("="*80)
        
        for detail in self.results["test_details"]:
            if detail["status"] == "error":
                print(f"\n{detail['annotation_file']} - ERROR")
                print(f"  {detail['error']}")
                continue
            
            if not detail["comparison"]:
                continue
            
            comparison = detail["comparison"]
            accuracy = comparison["match_count"] / comparison["total_fields"]
            
            print(f"\n{detail['annotation_file']}")
            print(f"  Status:   {detail['status'].upper()}")
            print(f"  Accuracy: {accuracy*100:.1f}%")
            print(f"  Fields matched: {comparison['match_count']}/{comparison['total_fields']}")
            
            # Group by simple and nested fields
            if comparison['simple_fields']:
                print(f"\n  [Simple Fields]")
                for field in comparison['simple_fields']:
                    if field in comparison['field_results']:
                        result = comparison['field_results'][field]
                        match_indicator = "✓" if result["is_match"] else ("◐" if result["partial_match"] else "✗")
                        print(f"    {match_indicator} {field}:")
                        print(f"       Extracted:    {result['extracted'][:100]}")
                        print(f"       Ground truth: {result['ground_truth'][:100]}")
                        if result["similarity"] < 1.0:
                            print(f"       Similarity:   {result['similarity']*100:.1f}%")
            
            if comparison['nested_fields']:
                print(f"\n  [Nested Fields (Dict/Tags)]")
                for field in comparison['nested_fields']:
                    if field in comparison['field_results']:
                        result = comparison['field_results'][field]
                        match_indicator = "✓" if result["is_match"] else "◐" if result["match_ratio"] >= 0.25 else "✗"
                        print(f"    {match_indicator} {field}:")
                        print(f"       Match ratio: {result['match_ratio']*100:.1f}%")
                        
                        # Show sub-keys if detailed view
                        if self.detailed and result.get('sub_results'):
                            for sub_key, sub_result in result['sub_results'].items():
                                sub_match = "✓" if sub_result["is_match"] else "✗"
                                print(f"         {sub_match} {sub_key}: extracted={sub_result['extracted']}, ground_truth={sub_result['ground_truth']}")


def main():
    """Main entry point"""
    detailed = "--detailed" in sys.argv
    metrics = "--metrics" in sys.argv
    verbose = "--verbose" in sys.argv
    
    # Remove flags from argv for cleaner processing
    clean_argv = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    
    tester = AccuracyTester(verbose=verbose, detailed=detailed)
    
    if clean_argv:
        # Test specific bulletin
        bulletin_name = clean_argv[0]
        tester.test_single_bulletin(bulletin_name)
    else:
        # Auto-test all annotations
        print("Auto-testing all annotations in pdfs_annotation/")
        print("Matching with corresponding PDFs...\n")
        tester.run_all_tests()
    
    tester.print_summary()
    
    if detailed or metrics:
        tester.print_detailed_results()
    
    # Exit with appropriate code
    if tester.results["failed"] == 0 and tester.results["errors"] == 0:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
