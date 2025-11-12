"""
Debug script to examine table structures in the PDF.
"""

import pdfplumber

def debug_tables(file_path):
    """Debug the table structures in the PDF."""
    print(f"Analyzing tables in: {file_path}")
    print("=" * 60)
    
    with pdfplumber.open(file_path) as pdf:
        for page_num in range(3, 7):  # Only pages 4-7
            page = pdf.pages[page_num]
            print(f"PAGE {page_num + 1}:")
            print("-" * 40)
            
            # Print full page text for manual inspection
            text = page.extract_text()
            print("FULL PAGE TEXT:")
            print(text)
            print("-" * 40)

            # Try different table extraction settings
            for vertical_strategy in ["lines", "text"]:
                for horizontal_strategy in ["lines", "text"]:
                    settings = {
                        "vertical_strategy": vertical_strategy,
                        "horizontal_strategy": horizontal_strategy,
                        "snap_tolerance": 3,
                    }
                    print(f"Trying settings: {settings}")
                    tables = page.extract_tables(table_settings=settings)
                    print(f"Found {len(tables)} tables")
                    
                    for i, table in enumerate(tables):
                        if table:
                            print(f"\nTable {i+1}:")
                            print(f"  Rows: {len(table)}")
                            print(f"  Columns: {len(table[0]) if table else 0}")
                            for row in table:
                                print(f"  {row}")
                    print()
            
            print("=" * 60)

if __name__ == "__main__":
    debug_tables("data/20250613-614-Compensation Reports_unlocked.pdf")