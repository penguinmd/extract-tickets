"""
Minimal diagnostic tool to analyze PDF extraction issues
"""
import pdfplumber
import re
import json
from typing import Dict, List, Any

def analyze_pdf(file_path: str) -> Dict[str, Any]:
    """Analyze PDF structure and content to diagnose extraction issues"""
    
    analysis = {
        "file": file_path,
        "pages": [],
        "patterns_found": {},
        "potential_issues": [],
        "recommendations": []
    }
    
    try:
        with pdfplumber.open(file_path) as pdf:
            print(f"\n{'='*60}")
            print(f"Analyzing PDF: {file_path}")
            print(f"Total pages: {len(pdf.pages)}")
            print(f"{'='*60}\n")
            
            # Analyze each page
            for page_num, page in enumerate(pdf.pages):
                page_analysis = analyze_page(page, page_num + 1)
                analysis["pages"].append(page_analysis)
                
                # Print summary for each page
                print(f"\nPage {page_num + 1}:")
                print(f"- Text length: {len(page_analysis['text'])} chars")
                print(f"- Tables found: {page_analysis['table_count']}")
                print(f"- Lines with data: {len(page_analysis['data_lines'])}")
                
                if page_analysis['data_lines']:
                    print(f"- First data line: {page_analysis['data_lines'][0][:100]}...")
            
            # Aggregate patterns
            aggregate_patterns(analysis)
            
            # Generate recommendations
            generate_recommendations(analysis)
            
    except Exception as e:
        analysis["potential_issues"].append(f"Error opening PDF: {str(e)}")
    
    return analysis

def analyze_page(page, page_num: int) -> Dict[str, Any]:
    """Analyze a single page for extraction patterns"""
    
    page_data = {
        "page_number": page_num,
        "text": "",
        "tables": [],
        "table_count": 0,
        "data_lines": [],
        "line_patterns": {}
    }
    
    # Extract text
    page_text = page.extract_text()
    if page_text:
        page_data["text"] = page_text
        
        # Analyze lines for patterns
        lines = page_text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check various patterns
            patterns_to_check = {
                "8_digits": r'^\d{8}',
                "6_plus_digits": r'^\d{6,}',
                "date_start": r'^\d{1,2}/\d{1,2}/\d{4}',
                "alphanumeric": r'^[A-Z0-9]{5,}',
                "mixed_ticket": r'^\d+\s*[A-Z]',
                "any_number_start": r'^\d+',
                "phys_pattern": r'^\d+\s+\w+'
            }
            
            for pattern_name, pattern in patterns_to_check.items():
                if re.match(pattern, line):
                    if pattern_name not in page_data["line_patterns"]:
                        page_data["line_patterns"][pattern_name] = 0
                    page_data["line_patterns"][pattern_name] += 1
                    
                    # Consider it a potential data line
                    if len(line) > 20:  # Likely a data row
                        page_data["data_lines"].append(line)
                        break
    
    # Extract tables
    tables = page.extract_tables()
    if tables:
        page_data["table_count"] = len(tables)
        for i, table in enumerate(tables):
            table_info = {
                "table_index": i,
                "rows": len(table),
                "columns": len(table[0]) if table else 0,
                "headers": table[0] if table else [],
                "sample_rows": table[1:4] if len(table) > 1 else []
            }
            page_data["tables"].append(table_info)
    
    return page_data

def aggregate_patterns(analysis: Dict[str, Any]):
    """Aggregate patterns across all pages"""
    
    all_patterns = {}
    for page in analysis["pages"]:
        for pattern, count in page["line_patterns"].items():
            if pattern not in all_patterns:
                all_patterns[pattern] = 0
            all_patterns[pattern] += count
    
    analysis["patterns_found"] = all_patterns
    
    # Identify most common pattern
    if all_patterns:
        most_common = max(all_patterns, key=all_patterns.get)
        analysis["most_common_pattern"] = {
            "name": most_common,
            "count": all_patterns[most_common]
        }

def generate_recommendations(analysis: Dict[str, Any]):
    """Generate recommendations based on analysis"""
    
    # Check if tables were found
    total_tables = sum(page["table_count"] for page in analysis["pages"])
    
    if total_tables > 0:
        analysis["recommendations"].append("Tables detected - pdfplumber table extraction should work")
    else:
        analysis["recommendations"].append("No tables detected - need text-based parsing")
        analysis["potential_issues"].append("PDF may not have proper table structure")
    
    # Check patterns
    if "patterns_found" in analysis and analysis["patterns_found"]:
        if "8_digits" in analysis["patterns_found"]:
            analysis["recommendations"].append("8-digit pattern found - current regex should work")
        else:
            analysis["potential_issues"].append("No 8-digit patterns found - regex needs adjustment")
            
            # Recommend alternative patterns
            if "any_number_start" in analysis["patterns_found"]:
                analysis["recommendations"].append("Use more flexible number pattern: r'^\\d+'")
            if "alphanumeric" in analysis["patterns_found"]:
                analysis["recommendations"].append("Consider alphanumeric pattern: r'^[A-Z0-9]{5,}'")
    
    # Check for data lines
    total_data_lines = sum(len(page["data_lines"]) for page in analysis["pages"])
    if total_data_lines == 0:
        analysis["potential_issues"].append("No potential data lines detected")
        analysis["recommendations"].append("Review page structure and text extraction")
    else:
        analysis["recommendations"].append(f"Found {total_data_lines} potential data rows")

def save_diagnostic_report(analysis: Dict[str, Any], output_file: str = "pdf_diagnostic_report.json"):
    """Save the diagnostic report to a JSON file"""
    
    with open(output_file, 'w') as f:
        json.dump(analysis, f, indent=2)
    
    print(f"\nDiagnostic report saved to: {output_file}")

def print_sample_extraction(file_path: str, page_start: int = 3):
    """Print sample of what extraction would produce"""
    
    print(f"\n{'='*60}")
    print("Sample Extraction from ChargeTransaction Pages")
    print(f"{'='*60}")
    
    with pdfplumber.open(file_path) as pdf:
        # Start from page 4 (index 3) for charge transaction data
        for page_num in range(page_start, min(page_start + 2, len(pdf.pages))):
            page = pdf.pages[page_num]
            
            print(f"\n--- Page {page_num + 1} ---")
            
            # Try table extraction first
            tables = page.extract_tables()
            if tables:
                print(f"Table extraction successful - {len(tables)} table(s) found")
                for i, table in enumerate(tables):
                    if table and len(table) > 0:
                        print(f"\nTable {i + 1} - Headers: {table[0] if table else 'None'}")
                        if len(table) > 1:
                            print(f"First data row: {table[1]}")
            else:
                print("No tables found - checking text patterns")
                
                # Try text extraction
                text = page.extract_text()
                if text:
                    lines = text.split('\n')
                    data_lines = []
                    
                    for line in lines:
                        # Try multiple patterns
                        if (re.match(r'^\d+', line.strip()) and len(line.strip()) > 20):
                            data_lines.append(line.strip())
                    
                    if data_lines:
                        print(f"Found {len(data_lines)} potential data lines:")
                        for i, line in enumerate(data_lines[:3]):
                            print(f"  {i+1}: {line[:100]}...")
                    else:
                        print("No data lines matching patterns")

if __name__ == "__main__":
    # Run diagnostic on the sample file
    test_file = "data/archive/20250613-614-Compensation_Reports_unlocked.pdf"
    
    # Run analysis
    analysis = analyze_pdf(test_file)
    
    # Print summary
    print(f"\n{'='*60}")
    print("ANALYSIS SUMMARY")
    print(f"{'='*60}")
    
    print(f"\nPatterns Found:")
    for pattern, count in analysis["patterns_found"].items():
        print(f"  - {pattern}: {count} occurrences")
    
    print(f"\nPotential Issues:")
    for issue in analysis["potential_issues"]:
        print(f"  ⚠️  {issue}")
    
    print(f"\nRecommendations:")
    for rec in analysis["recommendations"]:
        print(f"  ✓ {rec}")
    
    # Save detailed report
    save_diagnostic_report(analysis)
    
    # Show sample extraction
    print_sample_extraction(test_file)