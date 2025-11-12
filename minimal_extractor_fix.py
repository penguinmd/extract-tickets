"""
Minimal fix for PDF extraction - flexible column parsing
"""
import re
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def parse_charge_transaction_line(line: str) -> dict:
    """
    Parse a charge transaction line with flexible column detection
    Based on actual data format from diagnostic:
    61411888 Myers Stephanie UF An 25111 PPO 12:25 13:24 4/22/25 5/13/25 59 3.00 0.0 0.0 868.00 UTCS 100...
    """
    
    # Split by multiple spaces (2 or more) to separate columns
    parts = re.split(r'\s{2,}', line.strip())
    
    # If split by multiple spaces doesn't work well, try single space
    if len(parts) < 10:
        parts = line.strip().split()
    
    # Initialize empty result
    result = {}
    
    try:
        # Parse based on position and content patterns
        idx = 0
        
        # Ticket ref (8 digits)
        if idx < len(parts) and re.match(r'^\d{8}$', parts[idx]):
            result['Phys Ticket Ref#'] = parts[idx]
            idx += 1
        
        # Patient name (skip 'B' prefix if present)
        if idx < len(parts) and parts[idx] == 'B':
            idx += 1
        
        # Patient name (usually 2 parts)
        name_parts = []
        while idx < len(parts) and not parts[idx].isupper() or len(name_parts) < 2:
            if parts[idx] not in ['UF', 'An', 'Me']:
                name_parts.append(parts[idx])
            else:
                break
            idx += 1
        
        result['Patient Name'] = ' '.join(name_parts)
        
        # Site/Service info (UF An/Me)
        site_serv = []
        while idx < len(parts) and parts[idx] in ['UF', 'An', 'Me']:
            site_serv.append(parts[idx])
            idx += 1
        
        if len(site_serv) >= 2:
            result['Site Code'] = site_serv[0]
            result['Serv Type'] = site_serv[1]
        
        # CPT Code (5 digits)
        if idx < len(parts) and re.match(r'^\d{5}$', parts[idx]):
            result['CPT Code'] = parts[idx]
            idx += 1
        
        # Pay Code (alphanumeric)
        if idx < len(parts):
            result['Pay Code'] = parts[idx]
            idx += 1
        
        # Times (HH:MM format)
        times_found = []
        while idx < len(parts) and len(times_found) < 2:
            if re.match(r'^\d{1,2}:\d{2}$', parts[idx]):
                times_found.append(parts[idx])
                idx += 1
            else:
                break
        
        if len(times_found) >= 1:
            result['Start Time'] = times_found[0]
        if len(times_found) >= 2:
            result['Stop Time'] = times_found[1]
        
        # Dates (M/D/YY format)
        dates_found = []
        while idx < len(parts) and len(dates_found) < 2:
            if re.match(r'^\d{1,2}/\d{1,2}/\d{2}$', parts[idx]):
                dates_found.append(parts[idx])
                idx += 1
            else:
                break
        
        if len(dates_found) >= 1:
            result['Date of Service'] = dates_found[0]
        if len(dates_found) >= 2:
            result['Date of Post'] = dates_found[1]
        
        # Remaining numeric values
        numeric_values = []
        while idx < len(parts):
            # Try to parse as number
            try:
                # Remove commas and try to convert
                clean_val = parts[idx].replace(',', '')
                float(clean_val)
                numeric_values.append(parts[idx])
            except:
                # Not a number, could be text like 'UTCS'
                pass
            idx += 1
        
        # Map numeric values to expected fields
        if len(numeric_values) > 0:
            result['Anes Time (Min)'] = numeric_values[0]
        if len(numeric_values) > 1:
            result['Anes Base Units'] = numeric_values[1]
        if len(numeric_values) > 2:
            result['Med Base Units'] = numeric_values[2]
        if len(numeric_values) > 3:
            result['Other Units'] = numeric_values[3]
        if len(numeric_values) > 4:
            result['Chg Amt'] = numeric_values[4]
        
        # Fill in missing fields with empty strings
        expected_fields = [
            'Phys Ticket Ref#', 'Note', 'Patient Name', 'Original Chg Mo', 'Site Code',
            'Serv Type', 'CPT Code', 'Pay Code', 'Start Time', 'Stop Time', 'OB Case Pos',
            'Date of Service', 'Date of Post', 'Split %', 'Anes Time (Min)', 'Anes Base Units',
            'Med Base Units', 'Other Units', 'Chg Amt', 'Sub Pool %', 'Sb Pl Time (Min)',
            'Anes Base', 'Med Base', 'Grp Pool %', 'Gr Pl Time (Min)', 'Anes Base', 'Med Base'
        ]
        
        for field in expected_fields:
            if field not in result:
                result[field] = ''
        
    except Exception as e:
        logger.warning(f"Error parsing line: {str(e)}")
        logger.debug(f"Line content: {line}")
    
    return result

def extract_charge_transactions_flexible(text: str) -> pd.DataFrame:
    """
    Extract charge transactions using flexible parsing
    """
    lines = text.split('\n')
    transactions = []
    
    for line in lines:
        line = line.strip()
        
        # Check if line starts with 8 digits (ticket number)
        if re.match(r'^\d{8}\s', line):
            transaction = parse_charge_transaction_line(line)
            if transaction and transaction.get('Phys Ticket Ref#'):
                transactions.append(transaction)
    
    if transactions:
        df = pd.DataFrame(transactions)
        logger.info(f"Extracted {len(df)} transactions using flexible parsing")
        return df
    else:
        return pd.DataFrame()

def test_flexible_extraction():
    """Test the flexible extraction with sample data"""
    
    sample_lines = [
        "61411888 Myers Stephanie UF An 25111 PPO 12:25 13:24 4/22/25 5/13/25 59 3.00 0.0 0.0 868.00 UTCS 100",
        "61411889 Kuntz Andrian UF An 43239 TRICARE 08:29 08:58 4/22/25 5/13/25 29 5.00 0.0 0.0 868.00 UTCS 1",
        "61411915 B Amir Rami UF An 29823 PPO 09:21 10:27 4/29/25 5/13/25 97.06 66 4.85 0.0 0.0 1,240.00 UTCS"
    ]
    
    print("Testing flexible extraction:")
    print("-" * 80)
    
    for line in sample_lines:
        result = parse_charge_transaction_line(line)
        print(f"\nOriginal: {line[:80]}...")
        print(f"Parsed:")
        for key, value in result.items():
            if value:  # Only show non-empty values
                print(f"  {key}: {value}")
    
    # Test with full text
    full_text = "\n".join(sample_lines)
    df = extract_charge_transactions_flexible(full_text)
    
    print(f"\n\nDataFrame shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    print(f"\nFirst row:")
    print(df.iloc[0].to_dict())

if __name__ == "__main__":
    test_flexible_extraction()