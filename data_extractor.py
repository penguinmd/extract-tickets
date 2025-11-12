"""
Data extraction module for medical compensation reports.
Extracts compensation summary, charge transactions, and ticket tracking data from PDF reports.
"""

import pdfplumber
import pandas as pd
import re
from datetime import datetime, timedelta
from typing import Tuple, Dict, Any
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MedicalReportExtractor:
    """Class to extract data from medical compensation PDF reports."""
    
    def __init__(self):
        self.summary_patterns = {
            'pay_period': r"Period:\s*([A-Za-z]+\s+\d{4})",  # "Period: May 2025"
            'pay_period_alt': r"For the Month of\s+([A-Za-z]+)",  # "For the Month of May"
            'pay_date': r"Pay Date:\s*(\d{1,2}/\d{1,2}/\d{4})",  # "Pay Date: 06/13/2025"
            'payroll_issued': r"Payroll Issued:\s*(\d{1,2}/\d{1,2}/\d{4})",  # "Payroll Issued: 6/13/2025"
            'gross_earnings': r"Gross Earnings\s*\$([\d,]+\.?\d*)",  # From payroll stub
            'net_compensation': r"Net Compensation/Net Pay\s*([\d,]+\.?\d*)",  # From compensation report
            'medical_director_stipend': r"Medical Director Stipend\s*([\d,]+\.?\d*)",
            'clinical_compensation': r"Clinical Compensation Subject to Overhead.*?\n.*?([\d,]+\.?\d*)",
            'employee_number': r"Employee Number\s*(\d+)"
        }
    
    def extract_data_from_report(self, file_path: str) -> Tuple[Dict[str, Any], pd.DataFrame, pd.DataFrame]:
        """
        Extract all data from a medical compensation PDF report.
        
        Args:
            file_path (str): Path to the PDF file
            
        Returns:
            Tuple containing:
            - summary_data (dict): Compensation summary data
            - charge_transactions (DataFrame): Charge transaction data
            - ticket_tracking (DataFrame): Ticket tracking data
        """
        logger.info(f"Processing file: {file_path}")
        
        try:
            with pdfplumber.open(file_path) as pdf:
                # Extract text from first 3 pages only for summary data (compensation section)
                summary_text = ""
                for page_num in range(min(3, len(pdf.pages))):  # Pages 1-3
                    page = pdf.pages[page_num]
                    page_text = page.extract_text()
                    if page_text:
                        summary_text += page_text + "\n"
                
                # 1. Extract summary data from compensation pages
                summary_data = self._extract_summary_data(summary_text, file_path)
                
                # 2. Extract table data from productivity pages (4+)
                charge_transactions, ticket_tracking = self._extract_table_data(pdf)
                
                logger.info(f"Successfully extracted data from {file_path}")
                return summary_data, charge_transactions, ticket_tracking
                
        except Exception as e:
            logger.error(f"Error processing {file_path}: {str(e)}")
            raise
    
    def _extract_summary_data(self, full_text: str, file_path: str) -> Dict[str, Any]:
        """Extract compensation summary data using regex patterns."""
        summary_data = {'source_file': file_path.split('/')[-1]}  # Just filename
        
        for field, pattern in self.summary_patterns.items():
            match = re.search(pattern, full_text, re.IGNORECASE | re.DOTALL)
            if match:
                value = match.group(1)
                if field in ['pay_date']:
                    # Convert date string to date object
                    try:
                        summary_data[field] = datetime.strptime(value, '%m/%d/%Y').date()
                    except ValueError:
                        logger.warning(f"Could not parse date: {value}")
                        summary_data[field] = None
                elif field in ['pay_period', 'pay_period_alt']:
                    # Handle period like "May 2025" or just "May"
                    try:
                        if field == 'pay_period_alt':
                            # For "For the Month of May", we need to get the year from pay_date
                            # We'll handle this after all patterns are processed
                            summary_data['_temp_month'] = value
                        else:
                            # Convert "May 2025" to a date (use first day of month)
                            period_date = datetime.strptime(f"01 {value}", '%d %B %Y').date()
                            summary_data['pay_period_start_date'] = period_date
                            # End date is last day of the month
                            if period_date.month == 12:
                                end_date = period_date.replace(year=period_date.year + 1, month=1, day=1) - timedelta(days=1)
                            else:
                                end_date = period_date.replace(month=period_date.month + 1, day=1) - timedelta(days=1)
                            summary_data['pay_period_end_date'] = end_date
                    except ValueError:
                        logger.warning(f"Could not parse period: {value}")
                        if field == 'pay_period':
                            summary_data['pay_period_start_date'] = None
                            summary_data['pay_period_end_date'] = None
                elif field in ['employee_number']:
                    # Keep as string/integer
                    summary_data[field] = value
                else:
                    # Convert monetary values
                    try:
                        clean_value = value.replace(',', '').replace('$', '').strip()
                        summary_data[field] = float(clean_value)
                    except ValueError:
                        logger.warning(f"Could not parse monetary value: {value}")
                        summary_data[field] = None
            else:
                logger.debug(f"Could not find {field} in document")
                summary_data[field] = None
        
        # Handle alternative month format
        if '_temp_month' in summary_data and summary_data['_temp_month']:
            month_name = summary_data['_temp_month']
            # Get year from pay_date if available
            if 'pay_date' in summary_data and summary_data['pay_date']:
                year = summary_data['pay_date'].year
                try:
                    period_date = datetime.strptime(f"01 {month_name} {year}", '%d %B %Y').date()
                    summary_data['pay_period_start_date'] = period_date
                    # End date is last day of the month
                    if period_date.month == 12:
                        end_date = period_date.replace(year=period_date.year + 1, month=1, day=1) - timedelta(days=1)
                    else:
                        end_date = period_date.replace(month=period_date.month + 1, day=1) - timedelta(days=1)
                    summary_data['pay_period_end_date'] = end_date
                except ValueError:
                    logger.warning(f"Could not parse month: {month_name}")
            del summary_data['_temp_month']
        
        # If we still don't have period dates, use pay_date to estimate
        if (not summary_data.get('pay_period_start_date') and
            summary_data.get('pay_date')):
            pay_date = summary_data['pay_date']
            # Assume the pay period is the previous month
            if pay_date.month == 1:
                period_start = pay_date.replace(year=pay_date.year - 1, month=12, day=1)
            else:
                period_start = pay_date.replace(month=pay_date.month - 1, day=1)
            
            # End date is last day of that month
            if period_start.month == 12:
                period_end = period_start.replace(year=period_start.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                period_end = period_start.replace(month=period_start.month + 1, day=1) - timedelta(days=1)
            
            summary_data['pay_period_start_date'] = period_start
            summary_data['pay_period_end_date'] = period_end
            logger.info(f"Estimated pay period: {period_start} to {period_end}")
        
        # Map to our standard field names
        if 'gross_earnings' in summary_data and summary_data['gross_earnings']:
            summary_data['gross_pay'] = summary_data['gross_earnings']
        elif 'net_compensation' in summary_data and summary_data['net_compensation']:
            summary_data['gross_pay'] = summary_data['net_compensation']
        
        # Set defaults for missing fields
        summary_data.setdefault('base_salary', None)
        summary_data.setdefault('total_commission', None)
        summary_data.setdefault('bonus_amount', None)
        summary_data.setdefault('gross_pay', None)
        
        return summary_data
    
    def _extract_table_data(self, pdf) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Extract table data from PDF pages using pdfplumber's table extraction."""
        charge_transactions_dfs = []
        ticket_tracking_dfs = []

        # Start from page 4 (index 3) onwards for productivity data
        for page_num in range(3, len(pdf.pages)):
            page = pdf.pages[page_num]
            page_text = page.extract_text()
            
            if not page_text:
                continue

            # First try pdfplumber's table extraction
            tables = page.extract_tables()
            
            if tables:
                logger.debug(f"Found {len(tables)} structured tables on page {page_num + 1}")
                # Process structured tables
                for table in tables:
                    if not table or len(table) < 2:
                        continue

                    df = self._create_dataframe_from_table(table)
                    if df.empty:
                        continue

                    table_type = self._identify_table_type(df, page_text)
                    
                    if table_type == "charge_transaction":
                        df = self._clean_charge_transaction_data(df)
                        if not df.empty:
                            charge_transactions_dfs.append(df)
                            logger.info(f"Found charge transaction table with {len(df)} rows on page {page_num + 1}")
                    
                    elif table_type == "ticket_tracking":
                        df = self._clean_ticket_tracking_data(df)
                        if not df.empty:
                            ticket_tracking_dfs.append(df)
                            logger.info(f"Found ticket tracking table with {len(df)} rows on page {page_num + 1}")
            else:
                # Fall back to text-based parsing for pages with text-formatted data
                logger.debug(f"No structured tables found on page {page_num + 1}, trying text parsing")
                
                # Check if this page contains charge transaction data
                if 'chargetransaction' in page_text.lower().replace(' ', '') or 'ticket tracking' in page_text.lower():
                    charge_df, ticket_df = self._parse_text_based_tables(page_text, page_num + 1)
                    
                    if not charge_df.empty:
                        charge_transactions_dfs.append(charge_df)
                        logger.info(f"Parsed {len(charge_df)} charge transactions from text on page {page_num + 1}")
                    
                    if not ticket_df.empty:
                        ticket_tracking_dfs.append(ticket_df)
                        logger.info(f"Parsed {len(ticket_df)} ticket tracking records from text on page {page_num + 1}")

        # Consolidate multi-page tables
        charge_transactions = pd.concat(charge_transactions_dfs, ignore_index=True) if charge_transactions_dfs else pd.DataFrame()
        ticket_tracking = pd.concat(ticket_tracking_dfs, ignore_index=True) if ticket_tracking_dfs else pd.DataFrame()

        # Note: Anonymization removed - patient names are now preserved
        # charge_transactions = self._anonymize_dataframe(charge_transactions)
        # ticket_tracking = self._anonymize_dataframe(ticket_tracking)

        logger.info(f"Extracted {len(charge_transactions)} charge transactions and {len(ticket_tracking)} ticket tracking records")
        
        return charge_transactions, ticket_tracking
    
    def _create_dataframe_from_table(self, table) -> pd.DataFrame:
        """Create a pandas DataFrame from a table extracted by pdfplumber."""
        try:
            if not table or len(table) < 2:
                return pd.DataFrame()

            headers = [str(h).replace('\n', ' ').strip() for h in table[0]]
            data = table[1:]
            
            df = pd.DataFrame(data, columns=headers)
            df = df.ffill()
            df = df.dropna(how='all')
            
            return df
            
        except Exception as e:
            logger.warning(f"Error creating DataFrame from table: {str(e)}")
            return pd.DataFrame()

    def _identify_table_type(self, df: pd.DataFrame, page_text: str) -> str:
        """Identify the type of table based on headers and page content."""
        if df.empty:
            return "unknown"
        
        # Convert headers to lowercase for easier matching
        headers = [str(col).lower() for col in df.columns]
        page_text_lower = page_text.lower()
        
        # Look for charge transaction indicators
        charge_indicators = ['ticket', 'patient', 'cpt', 'chg', 'site', 'serv']
        charge_score = sum(1 for indicator in charge_indicators if any(indicator in header for header in headers))
        
        # Look for ticket tracking indicators
        ticket_indicators = ['ticket', 'date', 'closed', 'commission', 'case']
        ticket_score = sum(1 for indicator in ticket_indicators if any(indicator in header for header in headers))
        
        # Check page content for context clues
        if 'chargetransaction' in page_text_lower.replace(' ', '') or 'charge transaction' in page_text_lower:
            return "charge_transaction"
        elif 'ticket tracking' in page_text_lower or 'tickettracking' in page_text_lower.replace(' ', ''):
            return "ticket_tracking"
        
        # Fall back to header analysis
        if charge_score >= 3:
            return "charge_transaction"
        elif ticket_score >= 2:
            return "ticket_tracking"
        
        logger.debug(f"Could not identify table type. Headers: {headers}")
        return "unknown"

    def _clean_charge_transaction_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize charge transaction data."""
        if df.empty:
            return df
        
        try:
            # Create a copy to avoid modifying the original
            cleaned_df = df.copy()
            
            # Do not rename columns or convert data types
            pass
            
            # Remove completely empty rows
            cleaned_df = cleaned_df.dropna(how='all')
            
            logger.debug(f"Cleaned charge transaction data: {len(cleaned_df)} rows, columns: {list(cleaned_df.columns)}")
            return cleaned_df
            
        except Exception as e:
            logger.warning(f"Error cleaning charge transaction data: {str(e)}")
            return pd.DataFrame()

    def _clean_ticket_tracking_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize ticket tracking data."""
        if df.empty:
            return df
        
        try:
            # Create a copy to avoid modifying the original
            cleaned_df = df.copy()
            
            # Map common column variations to standard names
            column_mapping = {
                'ticket': 'case_id',
                'ticket number': 'case_id',
                'case': 'case_id',
                'case id': 'case_id',
                'type': 'case_type',
                'case type': 'case_type',
                'anesthesia type': 'case_type',
                'date closed': 'date_closed',
                'closed': 'date_closed',
                'commission': 'commission_earned',
                'commission earned': 'commission_earned',
                'earned': 'commission_earned'
            }
            
            # Rename columns based on mapping
            for old_name, new_name in column_mapping.items():
                matching_cols = [col for col in cleaned_df.columns if old_name.lower() in str(col).lower()]
                if matching_cols:
                    cleaned_df = cleaned_df.rename(columns={matching_cols[0]: new_name})
            
            # Convert numeric columns
            if 'commission_earned' in cleaned_df.columns:
                cleaned_df['commission_earned'] = pd.to_numeric(
                    cleaned_df['commission_earned'].astype(str).str.replace(',', '').str.replace('$', ''),
                    errors='coerce'
                )
            
            # Convert date columns
            if 'date_closed' in cleaned_df.columns:
                cleaned_df['date_closed'] = pd.to_datetime(cleaned_df['date_closed'], errors='coerce')
            
            # Remove completely empty rows
            cleaned_df = cleaned_df.dropna(how='all')
            
            logger.debug(f"Cleaned ticket tracking data: {len(cleaned_df)} rows, columns: {list(cleaned_df.columns)}")
            return cleaned_df
            
        except Exception as e:
            logger.warning(f"Error cleaning ticket tracking data: {str(e)}")
            return pd.DataFrame()

    def _parse_text_based_tables(self, page_text: str, page_num: int) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Parse table data from text when structured tables are not detected."""
        
        lines = page_text.split('\n')
        transactions = []
        
        for line in lines:
            line = line.strip()
            
            # Check if line starts with 8 digits (ticket number)
            if re.match(r'^\d{8}\s', line):
                transaction = self._parse_charge_transaction_line(line)
                if transaction and transaction.get('Phys Ticket Ref#'):
                    transactions.append(transaction)
        
        if transactions:
            df = pd.DataFrame(transactions)
            logger.info(f"Extracted {len(df)} transactions from page {page_num} using flexible parsing")
            return df, pd.DataFrame()
        else:
            return pd.DataFrame(), pd.DataFrame()
    
    def _parse_charge_transaction_line(self, line: str) -> dict:
        """
        Parse a charge transaction line with comprehensive field extraction.
        Captures all fields including Note and numeric values at the end.
        """
        
        # Initialize empty result
        result = {}
        
        try:
            # Extract ticket ref (first 8 digits)
            if len(line) >= 8 and line[:8].isdigit():
                result['Phys Ticket Ref#'] = line[:8]
            else:
                return {}  # Not a valid data line
            
            # Extract Note field (single character at position 9, after a space)
            # Only capture valid note characters: S, B, M, D, Z
            if len(line) > 9 and line[9] in ['S', 'B', 'M', 'D', 'Z']:
                result['Note'] = line[9]
            else:
                result['Note'] = ''
            
            # Find where Site/Service fields start (look for "UF An", "UF Me", or "UF Mo")
            # Handle cases where UF might be concatenated with patient name
            site_pattern = r'(UF)\s*(An|Me|Mo)\s+'
            site_match = re.search(site_pattern, line[10:])  # Start after Note field
            
            # Also check for embedded patterns like "UroFlynAn" or "UroFlynMe"
            if not site_match:
                # Try to find patterns like "Flynn" or similar embedded text
                embedded_pattern = r'(?:Uro)?(?:Flynn?|Flyn)(An|Me|Mo)\s+'
                embedded_match = re.search(embedded_pattern, line[10:])
                if embedded_match:
                    # For embedded patterns, we'll assume UF as site code
                    result['Site Code'] = 'UF'
                    result['Serv Type'] = embedded_match.group(1)
                    site_match = embedded_match
            
            if site_match:
                # Extract patient name, which is between the note and the site code
                name_start_index = 11 if result.get('Note') else 9
                name_end_index = 10 + site_match.start()
                patient_name = line[name_start_index:name_end_index].strip()
                # Note: Patient name extraction removed - field no longer needed
                # result['patient_name'] = patient_name  # Store original name without scrambling

                if 'Site Code' not in result:
                    result['Site Code'] = site_match.group(1)
                if 'Serv Type' not in result:
                    result['Serv Type'] = site_match.group(2) if len(site_match.groups()) >= 2 else site_match.group(1)
                
                # Everything after site/service
                remaining = line[10 + site_match.end():].strip()
                parts = remaining.split()
                
                idx = 0
                
                # CPT Code (5 digits)
                if idx < len(parts) and re.match(r'^\d{5}$', parts[idx]):
                    result['CPT Code'] = parts[idx]
                    idx += 1
                
                # Pay Code (next non-time field)
                if idx < len(parts) and not re.match(r'^\d{1,2}:\d{2}$', parts[idx]):
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
                
                # OB Case Pos (might be present before dates)
                if idx < len(parts) and not re.match(r'^\d{1,2}/\d{1,2}/\d{2}$', parts[idx]):
                    # Check if it's a position indicator
                    if parts[idx] in ['L', 'R', 'S', 'P'] or len(parts[idx]) == 1:
                        result['OB Case Pos'] = parts[idx]
                        idx += 1
                
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
                
                # Robust parsing for all fields after dates
                # Define the complete list of expected fields in order
                post_date_fields = [
                    'Split %',
                    'Anes Time (Min)', 'Anes Base Units', 'Med Base Units', 'Other Units',
                    'Chg Amt', 'Sub Pool %', 'Sb Pl Time (Min)', 'Anes Base', 'Med Base',
                    'Grp Pool %', 'Gr Pl Time (Min)', 'Grp Anes Base', 'Grp Med Base'
                ]
                
                # Special handling for Split% vs Anes Time
                if idx < len(parts):
                    first_value = parts[idx]
                    
                    # Check if first value is a decimal (Split%) or integer (Anes Time)
                    try:
                        float_val = float(first_value.replace(',', ''))
                        
                        if '.' in first_value:  # Decimal number = Split%
                            result['Split %'] = first_value
                            idx += 1
                            
                            # Next value is Anes Time
                            if idx < len(parts):
                                result['Anes Time (Min)'] = parts[idx]
                                idx += 1
                            else:
                                result['Anes Time (Min)'] = ''
                        else:  # Integer = Anes Time, Split% is missing
                            result['Split %'] = ''  # Split% is missing
                            result['Anes Time (Min)'] = first_value
                            idx += 1
                            
                    except ValueError:
                        # Not a valid number, treat as missing Split%
                        result['Split %'] = ''
                        result['Anes Time (Min)'] = first_value
                        idx += 1
                else:
                    # No more parts, set both to empty
                    result['Split %'] = ''
                    result['Anes Time (Min)'] = ''
                
                # Continue with remaining fields (starting from Anes Base Units)
                remaining_fields = [
                    'Anes Base Units', 'Med Base Units', 'Other Units',
                    'Chg Amt', 'Sub Pool %', 'Sb Pl Time (Min)', 'Anes Base', 'Med Base',
                    'Grp Pool %', 'Gr Pl Time (Min)', 'Grp Anes Base', 'Grp Med Base'
                ]
                
                # Always consume a value for each expected field to maintain alignment
                for field in remaining_fields:
                    if idx < len(parts):
                        value = parts[idx]
                        
                        # Validate numeric fields
                        if field in ['Anes Base Units', 'Med Base Units', 'Other Units', 'Chg Amt', 'Sub Pool %', 'Sb Pl Time (Min)', 'Anes Base', 'Med Base', 'Grp Pool %', 'Gr Pl Time (Min)', 'Grp Anes Base', 'Grp Med Base']:
                            # Try to convert to float, if it fails, set to empty
                            try:
                                float_val = float(value.replace(',', ''))
                                result[field] = value
                            except ValueError:
                                # Not a valid number, set to empty
                                result[field] = ''
                        else:
                            result[field] = value
                        idx += 1
                    else:
                        result[field] = ''
            
            return result

        except Exception as e:
            logger.error(f"Error parsing charge transaction line: {str(e)}")
            return {}

def test_extractor():
    """Test function to verify the extractor works."""
    
    # Create a dummy PDF for testing if needed, or use an existing one
    # For now, we assume a test PDF exists at 'data/test_report.pdf'
    
    try:
        extractor = MedicalReportExtractor()
        summary, charges, tickets = extractor.extract_data_from_report('data/test_final.pdf')
        
        print("=== SUMMARY DATA ===")
        print(summary)
        
        print("\n=== CHARGE TRANSACTIONS ===")
        print(charges.head())
        
        print("\n=== TICKET TRACKING ===")
        print(tickets.head())
        
    except Exception as e:
        print(f"An error occurred during testing: {str(e)}")

if __name__ == '__main__':
    test_extractor()