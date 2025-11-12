#!/usr/bin/env python3
"""
Debug script to examine the raw data format and understand field structure.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pdfplumber
import re

def debug_raw_data():
    """Debug the raw data format to understand field structure."""
    
    # Open the PDF and extract raw text
    with pdfplumber.open('data/archive/20250613-614-Compensation_Reports_unlocked.pdf') as pdf:
        print("=== DEBUGGING RAW DATA FORMAT ===")
        
        # Look at pages 4-7 (where transaction data is)
        for page_num in range(3, 7):  # Pages 4-7 (0-indexed)
            page = pdf.pages[page_num]
            page_text = page.extract_text()
            
            print(f"\n--- Page {page_num + 1} ---")
            
            # Find lines that start with 8 digits (ticket numbers)
            lines = page_text.split('\n')
            transaction_lines = []
            
            for line in lines:
                line = line.strip()
                if re.match(r'^\d{8}\s', line):
                    transaction_lines.append(line)
            
            print(f"Found {len(transaction_lines)} transaction lines on page {page_num + 1}")
            
            # Look for specific transaction 61411893
            target_ticket = '61411893'
            for line in transaction_lines:
                if target_ticket in line:
                    print(f"\n*** FOUND TARGET TRANSACTION {target_ticket} ***")
                    print(f"Raw line: {repr(line)}")
                    
                    # Split by spaces and show parts
                    parts = line.split()
                    print(f"Parts ({len(parts)}): {parts}")
                    
                    # Find where dates end and post-date fields start
                    date_end_idx = None
                    for j, part in enumerate(parts):
                        if re.match(r'^\d{1,2}/\d{1,2}/\d{2}$', part):
                            date_end_idx = j
                    if date_end_idx is not None:
                        print(f"  Dates end at index {date_end_idx}: {parts[date_end_idx]}")
                        print(f"  Post-date parts starting at index {date_end_idx + 1}: {parts[date_end_idx + 1:date_end_idx + 10]}")
                    
                    # Show field mapping
                    print("Field mapping analysis:")
                    if date_end_idx is not None:
                        post_date_parts = parts[date_end_idx + 1:]
                        expected_fields = ['Split %', 'Anes Time (Min)', 'Anes Base Units', 'Med Base Units', 'Other Units', 'Chg Amt']
                        for i, field in enumerate(expected_fields):
                            if i < len(post_date_parts):
                                print(f"  {field}: '{post_date_parts[i]}'")
                            else:
                                print(f"  {field}: (missing)")
                    break
            
            # Show first few transaction lines
            for i, line in enumerate(transaction_lines[:3]):
                print(f"\nTransaction {i+1}:")
                print(f"Raw line: {repr(line)}")
                
                # Split by spaces and show parts
                parts = line.split()
                print(f"Parts ({len(parts)}): {parts}")
                
                # Show first 20 parts with indices
                print("First 20 parts:")
                for j, part in enumerate(parts[:20]):
                    print(f"  [{j}]: {part}")
                
                if i >= 2:  # Only show first 3 transactions per page
                    break

if __name__ == "__main__":
    debug_raw_data() 