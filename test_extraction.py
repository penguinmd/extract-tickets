"""
Test the updated extraction logic with the actual PDF
"""
from data_extractor import MedicalReportExtractor
import pandas as pd

def test_extraction():
    """Test extraction with the actual PDF file"""
    
    extractor = MedicalReportExtractor()
    test_file = "data/archive/20250613-614-Compensation_Reports_unlocked.pdf"
    
    print("Testing PDF extraction with updated logic...")
    print("=" * 80)
    
    try:
        # Extract data
        summary, charges, tickets = extractor.extract_data_from_report(test_file)
        
        # Print summary
        print("\nSUMMARY DATA:")
        print("-" * 40)
        for key, value in summary.items():
            print(f"{key}: {value}")
        
        # Print charge transactions
        print(f"\n\nCHARGE TRANSACTIONS: {len(charges)} records")
        print("-" * 40)
        
        if not charges.empty:
            # Show columns
            print(f"Columns: {list(charges.columns)}")
            
            # Show first few rows
            print("\nFirst 5 rows:")
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', None)
            pd.set_option('display.max_colwidth', 20)
            
            # Display key columns
            key_columns = ['Phys Ticket Ref#', 'Site Code', 'Serv Type', 'CPT Code', 
                          'Pay Code', 'Date of Service', 'Chg Amt']
            available_columns = [col for col in key_columns if col in charges.columns]
            
            if available_columns:
                print(charges[available_columns].head())
            else:
                print(charges.head())
            
            # Show data types
            print("\nData types:")
            for col in available_columns:
                if col in charges.columns:
                    print(f"  {col}: {charges[col].dtype}")
            
            # Check for empty values
            print("\nNon-empty value counts:")
            for col in available_columns:
                if col in charges.columns:
                    non_empty = charges[col].astype(str).str.strip().ne('').sum()
                    print(f"  {col}: {non_empty}/{len(charges)}")
        else:
            print("No charge transactions found!")
        
        # Print ticket tracking
        print(f"\n\nTICKET TRACKING: {len(tickets)} records")
        print("-" * 40)
        
        if not tickets.empty:
            print(f"Columns: {list(tickets.columns)}")
            print("\nFirst 5 rows:")
            print(tickets.head())
        else:
            print("No ticket tracking records found.")
            
    except Exception as e:
        print(f"\nERROR during extraction: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_extraction()