#!/usr/bin/env python3
"""
Test script to compare Tabula extraction with our current PDFplumber approach.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import tabula
import pandas as pd
from data_extractor import MedicalReportExtractor

def test_tabula_extraction():
    """Test Tabula extraction on the same PDF."""
    
    print("=== TABULA EXTRACTION TEST ===")
    
    # Test Tabula extraction
    try:
        # Extract tables from pages 4-7
        tables = tabula.read_pdf(
            'data/archive/20250613-614-Compensation_Reports_unlocked.pdf',
            pages=[4, 5, 6, 7],
            multiple_tables=True,
            guess=False,  # Don't guess table structure
            lattice=True,  # Use lattice mode for tables with borders
            stream=True   # Use stream mode for tables without borders
        )
        
        print(f"Tabula found {len(tables)} tables")
        
        # Show first few tables
        for i, table in enumerate(tables[:3]):
            print(f"\n--- Tabula Table {i+1} ---")
            print(f"Shape: {table.shape}")
            print(f"Columns: {list(table.columns)}")
            print(table.head())
            
    except Exception as e:
        print(f"Tabula extraction failed: {str(e)}")
    
    print("\n=== PDFPLUMBER EXTRACTION TEST ===")
    
    # Test our current PDFplumber approach
    try:
        extractor = MedicalReportExtractor()
        summary, charges, tickets = extractor.extract_data_from_report('data/archive/20250613-614-Compensation_Reports_unlocked.pdf')
        
        print(f"PDFplumber extracted {len(charges)} charge transactions")
        print(f"Sample data:")
        print(charges[['Phys Ticket Ref#', 'Split %', 'Anes Time (Min)', 'Chg Amt']].head())
        
    except Exception as e:
        print(f"PDFplumber extraction failed: {str(e)}")

if __name__ == "__main__":
    test_tabula_extraction() 