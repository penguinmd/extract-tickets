#!/usr/bin/env python3
"""Test if the extraction fix works for problematic tickets."""

from data_extractor import MedicalReportExtractor
import pdfplumber

def test_specific_tickets():
    """Test extraction of specific problematic tickets."""
    extractor = MedicalReportExtractor()
    pdf_path = 'data/test_final.pdf'
    
    print("Testing extraction of problematic tickets...")
    print("=" * 60)
    
    # Tickets that were showing as blank
    target_tickets = ['61411951', '61411952', '61411953']
    found_tickets = {}
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text:
                continue
                
            lines = text.split('\n')
            for line in lines:
                # Check if this line contains one of our target tickets
                for ticket in target_tickets:
                    if ticket in line:
                        print(f"\nFound ticket {ticket} on page {page_num + 1}")
                        print(f"Raw line: {repr(line)}")
                        
                        # Try to parse it
                        result = extractor._parse_charge_transaction_line(line)
                        if result:
                            found_tickets[ticket] = result
                            print(f"Parsed successfully!")
                            print(f"Patient: {result.get('Patient Name', 'N/A')}")
                            print(f"Site Code: {result.get('Site Code', 'N/A')}")
                            print(f"Serv Type: {result.get('Serv Type', 'N/A')}")
                            print(f"Note: {result.get('Note', 'N/A')}")
                            print(f"All fields: {list(result.keys())}")
                        else:
                            print(f"Failed to parse!")
    
    print("\n" + "=" * 60)
    print(f"Summary: Found and parsed {len(found_tickets)} out of {len(target_tickets)} target tickets")
    
    for ticket in target_tickets:
        if ticket in found_tickets:
            print(f"✓ {ticket}: Successfully parsed")
        else:
            print(f"✗ {ticket}: Not found or failed to parse")

if __name__ == "__main__":
    test_specific_tickets()