"""
Fixed-width column parser for medical PDF extraction
"""
import re
import pandas as pd
import pdfplumber
import logging

logger = logging.getLogger(__name__)

class FixedWidthExtractor:
    def __init__(self):
        # Define column positions based on the PDF layout
        # These need to be adjusted based on actual PDF structure
        self.columns = [
            ('phys', 0, 4),           # Phys (0-3)
            ('ticket_ref', 4, 12),    # Ticket Ref# (4-11)
            ('note', 12, 14),         # Note (12-13)
            ('patient_name', 14, 29), # Patient Name (14-28) - will be skipped
            ('orig_chg_mo', 29, 33),  # Original Chg Mo (29-32)
            ('site_code', 33, 36),    # Site Code (33-35)
            ('serv_type', 36, 39),    # Serv Type (36-38)
            ('cpt_code', 39, 45),     # CPT Code (39-44)
            ('pay_code', 45, 53),     # Pay Code (45-52)
            ('start_time', 53, 59),   # Start Time (53-58)
            ('stop_time', 59, 65),    # Stop Time (59-64)
            ('ob_case_pos', 65, 69),  # OB Case Pos (65-68)
            ('date_of_service', 69, 79), # Date of Service (69-78)
            ('date_of_post', 79, 89),    # Date of Post (79-88)
            ('split_percent', 89, 95),   # Split % (89-94)
            ('anes_time_min', 95, 102),  # Anes Time (95-101)
            ('anes_base_units', 102, 108), # Anes Base Units (102-107)
            ('med_base_units', 108, 114),  # Med Base Units (108-113)
            ('other_units', 114, 120),     # Other Units (114-119)
            ('chg_amt', 120, 129),          # Chg Amt (120-128)
            # Continue for remaining columns...
        ]
    
    def extract_from_pdf(self, pdf_path, start_page=3):
        """Extract charge transactions using fixed-width parsing"""
        
        all_transactions = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num in range(start_page, len(pdf.pages)):
                page = pdf.pages[page_num]
                text = page.extract_text()
                
                if not text:
                    continue
                
                # Extract transactions from this page
                transactions = self.parse_page_text(text, page_num + 1)
                all_transactions.extend(transactions)
        
        return pd.DataFrame(all_transactions)
    
    def parse_page_text(self, text, page_num):
        """Parse text from a single page using fixed-width columns"""
        
        transactions = []
        lines = text.split('\n')
        
        for line in lines:
            # Check if line starts with 8 digits (ticket number)
            if re.match(r'^\d{8}', line):
                transaction = self.parse_transaction_line(line)
                if transaction:
                    transactions.append(transaction)
        
        logger.info(f"Extracted {len(transactions)} transactions from page {page_num}")
        return transactions
    
    def parse_transaction_line(self, line):
        """Parse a single transaction line using fixed-width columns"""
        
        # Ensure line is long enough
        if len(line) < 80:
            return None
        
        transaction = {}
        
        # Extract based on fixed positions
        transaction['Phys Ticket Ref#'] = line[0:8].strip()
        
        # Skip patient name but continue with other fields
        transaction['Note'] = line[12:14].strip()
        transaction['Original Chg Mo'] = line[29:33].strip()
        transaction['Site Code'] = line[33:36].strip()
        transaction['Serv Type'] = line[36:39].strip()
        transaction['CPT Code'] = line[39:45].strip()
        transaction['Pay Code'] = line[45:53].strip()
        
        # Extract times (format: HH:MM)
        start_time_match = re.search(r'(\d{1,2}:\d{2})', line[53:65])
        if start_time_match:
            transaction['Start Time'] = start_time_match.group(1)
            
            # Look for stop time after start time
            stop_time_match = re.search(r'(\d{1,2}:\d{2})', line[start_time_match.end() + 53:])
            if stop_time_match:
                transaction['Stop Time'] = stop_time_match.group(1)
        
        # Extract dates (format: M/D/YY or MM/DD/YY)
        date_pattern = r'(\d{1,2}/\d{1,2}/\d{2})'
        dates = re.findall(date_pattern, line[65:])
        if len(dates) >= 1:
            transaction['Date of Service'] = dates[0]
        if len(dates) >= 2:
            transaction['Date of Post'] = dates[1]
        
        # Extract numeric values from the rest of the line
        # Look for patterns like numbers with decimals
        remaining_text = line[89:]
        numeric_pattern = r'[\d,]+\.?\d*'
        numbers = re.findall(numeric_pattern, remaining_text)
        
        # Map numbers to fields (adjust based on actual data)
        if len(numbers) > 0:
            transaction['Anes Time (Min)'] = numbers[0]
        if len(numbers) > 1:
            transaction['Anes Base Units'] = numbers[1]
        if len(numbers) > 2:
            transaction['Med Base Units'] = numbers[2]
        if len(numbers) > 3:
            transaction['Other Units'] = numbers[3]
        if len(numbers) > 4:
            transaction['Chg Amt'] = numbers[4]
        
        # Fill in empty fields
        for field in ['Split %', 'Sub Pool %', 'Sb Pl Time (Min)', 'Anes Base', 
                      'Med Base', 'Grp Pool %', 'Gr Pl Time (Min)', 'OB Case Pos']:
            if field not in transaction:
                transaction[field] = ''
        
        return transaction

def test_fixed_width_extraction():
    """Test the fixed-width extraction"""
    
    extractor = FixedWidthExtractor()
    
    # Test with sample lines
    sample_lines = [
        "61411888 Myers    Stephanie     UF An 25111 PPO     12:25 13:24    4/22/25 5/13/25    59 3.00 0.0 0.0   868.00",
        "61411889 Kuntz    Andrian       UF An 43239 TRICARE 08:29 08:58    4/22/25 5/13/25    29 5.00 0.0 0.0   868.00",
        "61411890 MCELMURRY Carol W       UF An 69310 MCARE   07:19 10:48    4/23/25 5/13/25   209 5.00 0.0 0.0 2,343.60"
    ]
    
    print("Testing fixed-width extraction:")
    print("=" * 80)
    
    for line in sample_lines:
        result = extractor.parse_transaction_line(line)
        if result:
            print(f"\nTicket: {result.get('Phys Ticket Ref#')}")
            print(f"Site/Serv: {result.get('Site Code')}/{result.get('Serv Type')}")
            print(f"CPT: {result.get('CPT Code')}")
            print(f"Pay Code: {result.get('Pay Code')}")
            print(f"DOS: {result.get('Date of Service')}")
            print(f"Amount: {result.get('Chg Amt')}")

if __name__ == "__main__":
    test_fixed_width_extraction()