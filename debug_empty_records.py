#!/usr/bin/env python3
"""Debug records with ticket numbers but no data"""

import sqlite3
import pandas as pd
from data_extractor import MedicalReportExtractor

# Check database for empty records
conn = sqlite3.connect('compensation.db')
cursor = conn.cursor()

# First, check all records and look for ones with minimal data
print("=== CHECKING FOR RECORDS WITH MINIMAL DATA ===")
cursor.execute("""
    SELECT phys_ticket_ref, site_code, serv_type,
           cpt_code, note, split_percent, date_of_service,
           start_time, stop_time, pay_code
    FROM charge_transactions
    ORDER BY phys_ticket_ref
""")

rows = cursor.fetchall()
empty_tickets = []
all_tickets = {}

for row in rows:
    ticket_ref = row[0]
    if ticket_ref not in all_tickets:
        all_tickets[ticket_ref] = []
    
    # Check if record has minimal data (only ticket ref, maybe CPT)
    non_empty_fields = sum(1 for field in row[1:] if field and str(field).strip() and str(field).strip() != 'None')
    
    if non_empty_fields <= 1:  # Only ticket and maybe CPT
        empty_tickets.append(ticket_ref)
        print(f"\nEMPTY RECORD - Ticket: {ticket_ref}")
        print(f"  Site: '{row[1]}', Service: '{row[2]}', CPT: '{row[3]}'")
        print(f"  Note: '{row[4]}', Split%: '{row[5]}', Date: '{row[6]}'")
        print(f"  Start: '{row[7]}', Stop: '{row[8]}', PayCode: '{row[9]}'")
    
    all_tickets[ticket_ref].append(row)

# Get unique empty tickets
unique_empty = list(set(empty_tickets))
print(f"\n=== SUMMARY ===")
print(f"Total unique tickets: {len(all_tickets)}")
print(f"Tickets with minimal data: {len(unique_empty)}")
print(f"Empty ticket numbers: {unique_empty}")

# Now let's extract these specific lines from the PDF
if unique_empty:
    print("\n=== EXTRACTING PROBLEMATIC TICKETS FROM PDF ===")
    extractor = MedicalReportExtractor()
    
    # Read the PDF
    pdf_path = 'data/test_final.pdf'
    print(f"\nReading PDF: {pdf_path}")
    
    with open(pdf_path, 'rb') as f:
        import pdfplumber
        pdf = pdfplumber.open(f)
        
        # Search for the problematic tickets
        for ticket in unique_empty[:5]:  # Check first 5 empty tickets
            print(f"\n--- Searching for ticket {ticket} ---")
            found = False
            
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text and ticket in text:
                    lines = text.split('\n')
                    for i, line in enumerate(lines):
                        if line.strip().startswith(ticket):
                            found = True
                            print(f"Found on page {page_num + 1}, line {i + 1}:")
                            print(f"RAW LINE: {repr(line)}")
                            
                            # Show context
                            if i > 0:
                                print(f"PREV LINE: {repr(lines[i-1])}")
                            if i < len(lines) - 1:
                                print(f"NEXT LINE: {repr(lines[i+1])}")
                            
                            # Try to parse
                            print("\nParsing attempt:")
                            try:
                                parsed = extractor._parse_charge_transaction_line(line)
                                if parsed:
                                    print("PARSED DATA:")
                                    for key, value in parsed.items():
                                        if value:
                                            print(f"  {key}: {repr(value)}")
                                else:
                                    print("  Failed to parse!")
                            except Exception as e:
                                print(f"  Parse error: {e}")
                            break
                    
                    if found:
                        break
            
            if not found:
                print(f"Ticket {ticket} not found in PDF!")

conn.close()