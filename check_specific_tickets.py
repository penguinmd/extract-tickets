"""Check specific ticket numbers in the PDF"""
import pdfplumber
import re

def find_tickets_in_pdf(pdf_path, ticket_numbers):
    """Find specific ticket numbers in the PDF and show their lines"""
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num in range(3, len(pdf.pages)):  # Start from page 4
            page = pdf.pages[page_num]
            text = page.extract_text()
            
            if not text:
                continue
            
            lines = text.split('\n')
            
            for i, line in enumerate(lines):
                # Check if line contains any of our ticket numbers
                for ticket in ticket_numbers:
                    if ticket in line:
                        print(f"\n=== Page {page_num + 1}, Line {i} ===")
                        print(f"Line: {repr(line)}")
                        print(f"Length: {len(line)}")
                        
                        # Show surrounding lines for context
                        if i > 0:
                            print(f"Previous: {repr(lines[i-1])}")
                        if i < len(lines) - 1:
                            print(f"Next: {repr(lines[i+1])}")
                        
                        # Show character positions
                        print("\nCharacter positions:")
                        for j in range(0, min(len(line), 150), 10):
                            print(f"{j:3d}: '{line[j:j+10]}'")

if __name__ == "__main__":
    pdf_path = "data/archive/20250613-614-Compensation_Reports_unlocked.pdf"
    tickets = ['61411951', '61411952', '61411953']
    
    print("Searching for problematic tickets in PDF...")
    find_tickets_in_pdf(pdf_path, tickets)