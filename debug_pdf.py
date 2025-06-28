"""
Debug script to examine the actual content of the PDF file.
"""

import pdfplumber

def debug_pdf_content(file_path):
    """Debug the PDF content to understand its structure."""
    print(f"Analyzing PDF: {file_path}")
    print("=" * 60)
    
    with pdfplumber.open(file_path) as pdf:
        print(f"Total pages: {len(pdf.pages)}")
        print()
        
        for page_num, page in enumerate(pdf.pages):
            print(f"PAGE {page_num + 1}:")
            print("-" * 40)
            
            # Extract text
            text = page.extract_text()
            if text:
                # Show first 500 characters of text
                print("TEXT CONTENT (first 500 chars):")
                print(repr(text[:500]))
                print()
                
                # Look for key terms
                key_terms = ['Pay Period', 'Gross Pay', 'Commission', 'ChargeTransaction', 'Ticket Tracking']
                found_terms = []
                for term in key_terms:
                    if term.lower() in text.lower():
                        found_terms.append(term)
                
                if found_terms:
                    print(f"Found key terms: {', '.join(found_terms)}")
                    print()
            
            # Extract tables
            tables = page.extract_tables()
            if tables:
                print(f"Found {len(tables)} tables on this page")
                for i, table in enumerate(tables):
                    if table:
                        print(f"  Table {i+1}: {len(table)} rows, {len(table[0]) if table else 0} columns")
                        if table and len(table) > 0:
                            print(f"    Headers: {table[0]}")
                            if len(table) > 1:
                                print(f"    First row: {table[1]}")
                print()
            
            print("=" * 60)
            print()

if __name__ == "__main__":
    debug_pdf_content("data/20250613-614-Compensation Reports_unlocked.pdf")