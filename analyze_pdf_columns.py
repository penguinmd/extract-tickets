"""
Analyze PDF text to determine exact column positions
"""
import pdfplumber

def analyze_pdf_structure(pdf_path, page_num=3):
    """Analyze the structure of charge transaction data in the PDF"""
    
    with pdfplumber.open(pdf_path) as pdf:
        if page_num >= len(pdf.pages):
            print(f"Page {page_num + 1} not found")
            return
        
        page = pdf.pages[page_num]
        text = page.extract_text()
        
        if not text:
            print("No text found on page")
            return
        
        lines = text.split('\n')
        
        print("=== RAW TEXT ANALYSIS ===")
        print()
        
        # Find header line
        header_line = None
        header_index = -1
        for i, line in enumerate(lines):
            if 'Phys' in line and 'Ticket' in line and 'CPT' in line:
                header_line = line
                header_index = i
                break
        
        if header_line:
            print("HEADER LINE:")
            print(header_line)
            print()
            print("Character positions (0-indexed):")
            for i in range(0, min(len(header_line), 150), 10):
                print(f"{i:3d}: {header_line[i:i+10]}")
            print()
        
        # Find and analyze data lines
        print("\nDATA LINES (first 5):")
        print("=" * 100)
        
        data_count = 0
        for i, line in enumerate(lines):
            if i <= header_index:
                continue
                
            # Look for lines starting with 8 digits
            if len(line) > 8 and line[:8].isdigit():
                data_count += 1
                print(f"\nLine {data_count}:")
                print(line)
                print()
                
                # Show character positions
                print("Positions:")
                for j in range(0, min(len(line), 150), 10):
                    print(f"{j:3d}: '{line[j:j+10]}'")
                
                # Try to identify key fields
                print("\nField Analysis:")
                print(f"  0-8:   '{line[0:8]}'    <- Ticket Ref")
                print(f"  8-12:  '{line[8:12]}'")
                print(f"  12-30: '{line[12:30]}' <- Patient Name area")
                print(f"  30-35: '{line[30:35]}'")
                print(f"  35-40: '{line[35:40]}'  <- Site/Serv area")
                print(f"  40-50: '{line[40:50]}'  <- CPT/Pay Code area")
                print(f"  50-70: '{line[50:70]}'  <- Times area")
                print(f"  70-90: '{line[70:90]}'  <- Dates area")
                print(f"  90+:   '{line[90:]}'    <- Numeric values")
                
                if data_count >= 5:
                    break
        
        print(f"\n\nTotal data lines found: {data_count}")

if __name__ == "__main__":
    pdf_path = "data/archive/20250613-614-Compensation_Reports_unlocked.pdf"
    analyze_pdf_structure(pdf_path)