#!/usr/bin/env python3
"""
Debug script to analyze data vertically (column-wise) to identify field patterns and misalignments.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pdfplumber
import re
import pandas as pd
from collections import defaultdict

def analyze_vertical_data():
    """Analyze the data vertically to identify field patterns and misalignments."""
    
    print("=== VERTICAL DATA ANALYSIS ===")
    
    # Open the PDF and extract raw text
    with pdfplumber.open('data/archive/20250613-614-Compensation_Reports_unlocked.pdf') as pdf:
        all_transactions = []
        
        # Collect all transaction lines from pages 4-7
        for page_num in range(3, 7):  # Pages 4-7 (0-indexed)
            page = pdf.pages[page_num]
            page_text = page.extract_text()
            
            lines = page_text.split('\n')
            for line in lines:
                line = line.strip()
                if re.match(r'^\d{8}\s', line):
                    all_transactions.append(line)
        
        print(f"Total transactions found: {len(all_transactions)}")
        
        # Parse each transaction to find where dates end
        post_date_columns = defaultdict(list)
        
        for i, line in enumerate(all_transactions):
            parts = line.split()
            
            # Find where dates end
            date_end_idx = None
            for j, part in enumerate(parts):
                if re.match(r'^\d{1,2}/\d{1,2}/\d{2}$', part):
                    date_end_idx = j
            
            if date_end_idx is not None:
                # Get all parts after the dates
                post_date_parts = parts[date_end_idx + 1:]
                
                # Store each column position
                for col_idx, value in enumerate(post_date_parts):
                    post_date_columns[col_idx].append({
                        'ticket': parts[0],
                        'value': value,
                        'line_num': i
                    })
        
        # Analyze each column
        print(f"\n=== COLUMN ANALYSIS ===")
        print(f"Found {len(post_date_columns)} columns after dates")
        
        for col_idx in sorted(post_date_columns.keys()):
            values = [item['value'] for item in post_date_columns[col_idx]]
            
            print(f"\n--- Column {col_idx} ---")
            print(f"Total values: {len(values)}")
            
            # Analyze value patterns
            numeric_count = 0
            decimal_count = 0
            large_numbers = []
            small_numbers = []
            non_numeric = []
            
            for value in values:
                try:
                    float_val = float(value.replace(',', ''))
                    numeric_count += 1
                    
                    if '.' in value:
                        decimal_count += 1
                    
                    if float_val > 100:
                        large_numbers.append(value)
                    elif 0 <= float_val <= 100:
                        small_numbers.append(value)
                    else:
                        large_numbers.append(value)
                        
                except ValueError:
                    non_numeric.append(value)
            
            print(f"Numeric values: {numeric_count}")
            print(f"Decimal values: {decimal_count}")
            print(f"Values 0-100: {len(small_numbers)}")
            print(f"Values >100: {len(large_numbers)}")
            print(f"Non-numeric: {len(non_numeric)}")
            
            # Show sample values
            if small_numbers:
                print(f"Sample 0-100 values: {small_numbers[:5]}")
            if large_numbers:
                print(f"Sample >100 values: {large_numbers[:5]}")
            if non_numeric:
                print(f"Sample non-numeric: {non_numeric[:5]}")
            
            # Suggest field type based on patterns
            if col_idx == 0:
                if len(small_numbers) > len(large_numbers):
                    print("*** SUGGESTION: This looks like Split% column (mostly 0-100) ***")
                else:
                    print("*** SUGGESTION: This looks like Anes Time column (many >100) ***")
            elif col_idx == 1:
                if len(large_numbers) > len(small_numbers):
                    print("*** SUGGESTION: This looks like Anes Time column (many >100) ***")
                else:
                    print("*** SUGGESTION: This looks like Anes Base Units column ***")
            
            # Show some specific examples
            print("Sample transactions in this column:")
            for item in post_date_columns[col_idx][:3]:
                print(f"  Ticket {item['ticket']}: '{item['value']}'")

if __name__ == "__main__":
    analyze_vertical_data() 