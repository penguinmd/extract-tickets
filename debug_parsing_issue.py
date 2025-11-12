#!/usr/bin/env python3
"""Debug parsing issue for tickets with multiple lines"""

import sqlite3
import pdfplumber
from data_extractor import MedicalReportExtractor

# Problematic tickets
problem_tickets = ['61411904', '61411908', '61411952']

# Read and parse the PDF looking for all instances of these tickets
extractor = MedicalReportExtractor()
pdf_path = 'data/test_final.pdf'

print("=== PARSING ALL LINES FOR PROBLEMATIC TICKETS ===")
all_parsed_data = []

with open(pdf_path, 'rb') as f:
    pdf = pdfplumber.open(f)
    
    for page_num, page in enumerate(pdf.pages):
        text = page.extract_text()
        if not text:
            continue
            
        lines = text.split('\n')
        for i, line in enumerate(lines):
            # Check if line starts with any of our problem tickets
            for ticket in problem_tickets:
                if line.strip().startswith(ticket):
                    print(f"\n--- Found {ticket} on page {page_num + 1}, line {i + 1} ---")
                    print(f"RAW LINE: {repr(line)}")
                    
                    # Try to parse
                    try:
                        parsed = extractor._parse_charge_transaction_line(line)
                        if parsed:
                            all_parsed_data.append(parsed)
                            print("PARSED OK - Key fields:")
                            print(f"  Ticket: {parsed.get('Phys Ticket Ref#')}")
                            print(f"  CPT: {parsed.get('CPT Code')}")
                            print(f"  Start: {parsed.get('Start Time')}")
                            print(f"  Stop: {parsed.get('Stop Time')}")
                            print(f"  Site: {parsed.get('Site Code')}")
                            print(f"  Service: {parsed.get('Serv Type')}")
                            print(f"  Patient extracted: {bool(parsed.get('patient_name'))}")
                        else:
                            print("FAILED TO PARSE!")
                            all_parsed_data.append({
                                'Phys Ticket Ref#': ticket,
                                'failed_line': line
                            })
                    except Exception as e:
                        print(f"PARSE ERROR: {e}")

print(f"\n=== TOTAL PARSED LINES: {len(all_parsed_data)} ===")

# Now check what's in the database
print("\n=== DATABASE CONTENTS FOR THESE TICKETS ===")
conn = sqlite3.connect('compensation.db')
cursor = conn.cursor()

for ticket in problem_tickets:
    print(f"\n--- Ticket {ticket} in database ---")
    cursor.execute("""
        SELECT phys_ticket_ref, cpt_code, start_time, stop_time,
               site_code, serv_type, split_percent, date_of_service
        FROM charge_transactions 
        WHERE phys_ticket_ref = ?
        ORDER BY cpt_code, start_time
    """, (ticket,))
    
    rows = cursor.fetchall()
    if not rows:
        print("  NOT FOUND IN DATABASE!")
    else:
        for row in rows:
            print(f"  CPT: {row[1]}, Start: {row[2]}, Stop: {row[3]}, Site: {row[4]}, Service: {row[5]}")

conn.close()