#!/usr/bin/env python3
"""
Debug script to examine Split% parsing issues and field alignment.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_extractor import MedicalReportExtractor
import pandas as pd

def debug_split_parsing():
    """Debug Split% parsing issues."""
    
    print("=== DEBUGGING SPLIT% PARSING ===")
    
    # Process the PDF
    extractor = MedicalReportExtractor()
    summary, charges, tickets = extractor.extract_data_from_report('data/archive/20250613-614-Compensation_Reports_unlocked.pdf')
    
    print(f"Total transactions: {len(charges)}")
    
    # Show Split% value distribution
    print("\nSplit% value counts:")
    print(charges['Split %'].value_counts())
    
    # Find transactions where Split% seems wrong (very large numbers that should be Anes Time)
    print("\n=== TRANSACTIONS WITH POTENTIAL SPLIT% ISSUES ===")
    
    # Look for Split% values that are > 100 (likely should be Anes Time)
    # Safely handle blank values by filtering out empty strings first
    non_empty_split = charges[charges['Split %'].notna() & (charges['Split %'] != '')]
    large_split_values = non_empty_split[
        non_empty_split['Split %'].astype(str).str.replace(',', '').str.replace('.', '').str.isdigit() & 
        (non_empty_split['Split %'].astype(str).str.replace(',', '').astype(float) > 100)
    ]
    
    print(f"\nFound {len(large_split_values)} transactions with Split% > 100:")
    print(large_split_values[['Phys Ticket Ref#', 'Split %', 'Anes Time (Min)', 'Anes Base Units', 'Chg Amt']].head(10))
    
    # Look for transactions where Anes Time is empty but Split% has a reasonable value
    empty_anes_time = charges[(charges['Anes Time (Min)'].isna() | (charges['Anes Time (Min)'] == '')) & 
                             (charges['Split %'] != '') & (charges['Split %'].notna())]
    
    print(f"\nFound {len(empty_anes_time)} transactions with empty Anes Time but non-empty Split%:")
    print(empty_anes_time[['Phys Ticket Ref#', 'Split %', 'Anes Time (Min)', 'Anes Base Units', 'Chg Amt']].head(10))
    
    # Show some specific examples
    print("\n=== DETAILED EXAMPLES ===")
    
    # Get a few specific transactions to examine
    sample_tickets = ['61411890', '61411891', '61411892', '61411893', '61411894', '61411895']
    
    for ticket in sample_tickets:
        transaction = charges[charges['Phys Ticket Ref#'] == ticket]
        if not transaction.empty:
            print(f"\nTransaction {ticket}:")
            print(f"  Split%: '{transaction.iloc[0]['Split %']}'")
            print(f"  Anes Time: '{transaction.iloc[0]['Anes Time (Min)']}'")
            print(f"  Anes Base Units: '{transaction.iloc[0]['Anes Base Units']}'")
            print(f"  Chg Amt: '{transaction.iloc[0]['Chg Amt']}'")
            
            # Check if this looks like a misalignment
            split_val = transaction.iloc[0]['Split %']
            anes_time = transaction.iloc[0]['Anes Time (Min)']
            
            if split_val == '' and anes_time and anes_time != '':
                try:
                    anes_float = float(anes_time.replace(',', ''))
                    if anes_float > 100:  # This looks like it should be Split%
                        print(f"  *** POTENTIAL MISALIGNMENT: Anes Time '{anes_time}' looks like it should be Split% ***")
                except ValueError:
                    pass

if __name__ == "__main__":
    debug_split_parsing() 