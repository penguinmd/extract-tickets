"""
Comprehensive PDF structure analysis to identify all fields and their positions
"""
import pdfplumber
import re

def analyze_comprehensive_structure(pdf_path, page_num=3):
    """Analyze the complete structure including headers and data"""
    
    with pdfplumber.open(pdf_path) as pdf:
        if page_num >= len(pdf.pages):
            print(f"Page {page_num + 1} not found")
            return
        
        page = pdf.pages[page_num]
        
        # Try to extract tables first
        tables = page.extract_tables()
        if tables:
            print("=== TABLE STRUCTURE FOUND ===")
            for i, table in enumerate(tables):
                print(f"\nTable {i+1}:")
                if table and len(table) > 0:
                    # Print headers
                    headers = table[0] if table else []
                    print(f"Headers ({len(headers)} columns):")
                    for j, header in enumerate(headers):
                        print(f"  Col {j}: '{header}'")
                    
                    # Print first few data rows
                    print("\nFirst 3 data rows:")
                    for row_idx in range(1, min(4, len(table))):
                        print(f"Row {row_idx}:")
                        for j, cell in enumerate(table[row_idx]):
                            if cell and str(cell).strip():
                                print(f"  Col {j}: '{cell}'")
        
        # Also analyze raw text
        text = page.extract_text()
        if text:
            print("\n\n=== RAW TEXT ANALYSIS ===")
            lines = text.split('\n')
            
            # Find header area
            header_lines = []
            data_start = -1
            for i, line in enumerate(lines):
                if 'Phys' in line or 'Ticket' in line or 'Note' in line:
                    header_lines.append((i, line))
                if re.match(r'^\d{8}', line.strip()) and data_start == -1:
                    data_start = i
                    break
            
            print("\nHeader area:")
            for idx, line in header_lines:
                print(f"Line {idx}: {line}")
            
            # Analyze the specific line before first data line
            if data_start > 0:
                print(f"\nLine before first data (Line {data_start-1}):")
                print(repr(lines[data_start-1]))
            
            # Analyze first data line character by character
            if data_start >= 0 and data_start < len(lines):
                print(f"\n\nFirst data line analysis (Line {data_start}):")
                line = lines[data_start]
                print(f"Full line: {line}")
                print(f"Length: {len(line)} characters")
                
                # Show character positions
                print("\nCharacter mapping:")
                for i in range(0, min(len(line), 200), 10):
                    chars = line[i:i+10]
                    print(f"{i:3d}-{i+9:3d}: '{chars}'")
                
                # Try to identify Note field (single character)
                print("\n\nAnalyzing 'Note' field position:")
                # After 8-digit ticket, there should be a space and then a single character
                if len(line) > 9:
                    print(f"Position 8: '{line[8]}' (expected space)")
                    print(f"Position 9: '{line[9]}' (Note field?)")
                    print(f"Position 10: '{line[10]}' (space after Note?)")
                
                # Look for numeric patterns in the latter part
                print("\n\nNumeric values in line:")
                # Find all numeric patterns
                numeric_pattern = r'[\d,]+\.?\d*'
                numbers = [(m.start(), m.group()) for m in re.finditer(numeric_pattern, line)]
                
                print(f"Found {len(numbers)} numeric values:")
                for pos, num in numbers:
                    print(f"  Position {pos}: '{num}'")

def find_missing_rows(pdf_path):
    """Identify which rows might be getting filtered out"""
    
    with pdfplumber.open(pdf_path) as pdf:
        all_rows = []
        
        for page_num in range(3, len(pdf.pages)):
            page = pdf.pages[page_num]
            text = page.extract_text()
            if text:
                lines = text.split('\n')
                for line in lines:
                    if re.match(r'^\d{8}', line.strip()):
                        # Extract key fields for duplicate analysis
                        parts = line.split()
                        if len(parts) > 5:
                            ticket = parts[0]
                            # Try to find CPT code (5 digits)
                            cpt = None
                            for part in parts:
                                if re.match(r'^\d{5}$', part):
                                    cpt = part
                                    break
                            
                            # Try to find date
                            date = None
                            date_match = re.search(r'\d{1,2}/\d{1,2}/\d{2}', line)
                            if date_match:
                                date = date_match.group()
                            
                            all_rows.append({
                                'line': line[:100] + '...' if len(line) > 100 else line,
                                'ticket': ticket,
                                'cpt': cpt,
                                'date': date,
                                'page': page_num + 1
                            })
        
        print(f"\n\n=== DUPLICATE ANALYSIS ===")
        print(f"Total rows found: {len(all_rows)}")
        
        # Group by composite key
        from collections import defaultdict
        grouped = defaultdict(list)
        for row in all_rows:
            key = (row['ticket'], row['cpt'], row['date'])
            grouped[key].append(row)
        
        print(f"Unique composite keys: {len(grouped)}")
        
        # Show duplicates
        print("\nRows that share the same (ticket, cpt, date):")
        dup_count = 0
        for key, rows in grouped.items():
            if len(rows) > 1:
                dup_count += len(rows) - 1
                print(f"\nKey: {key}")
                for row in rows:
                    print(f"  Page {row['page']}: {row['line']}")
        
        print(f"\nTotal duplicate rows that would be filtered: {dup_count}")

if __name__ == "__main__":
    pdf_path = "data/archive/20250613-614-Compensation_Reports_unlocked.pdf"
    
    print("=== COMPREHENSIVE PDF STRUCTURE ANALYSIS ===\n")
    analyze_comprehensive_structure(pdf_path)
    find_missing_rows(pdf_path)