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

        # Anonymize data by removing patient information
        charge_transactions = self._anonymize_dataframe(charge_transactions)
        ticket_tracking = self._anonymize_dataframe(ticket_tracking)

        logger.info(f"Extracted {len(charge_transactions)} charge transactions and {len(ticket_tracking)} ticket tracking records")
        
        return charge_transactions, ticket_tracking
    
    def _create_dataframe_from_table(self, table) -> pd.DataFrame:
        """Create a pandas DataFrame from a table extracted by pdfplumber."""
        try:
            if not table or len(table) < 2:
                return pd.DataFrame()
            
            # Handle multi-line headers by merging the first two rows
            if len(table) > 1:
                header_rows = [table[0], table[1]]
                headers = [f"{h1 or ''} {h2 or ''}".strip() for h1, h2 in zip(*header_rows)]
                data = table[2:]
            else:
                headers = table[0]
                data = table[1:]

            # Clean headers
            clean_headers = [str(h).replace('\n', ' ').strip() for h in headers]
            
            # Create DataFrame
            df = pd.DataFrame(data, columns=clean_headers)
            
            # Handle multi-line rows by forward-filling missing values
            df = df.ffill()
            
            # Remove completely empty rows
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
            
            # Map common column variations to standard names
            column_mapping = {
                'ticket': 'ticket_ref',
                'patient': 'patient_name',
                'patient name': 'patient_name',
                'site': 'site_code',
                'serv': 'serv_type',
                'service': 'serv_type',
                'cpt': 'cpt_code',
                'cpt code': 'cpt_code',
                'pay': 'pay_code',
                'pay code': 'pay_code',
                'start': 'start_time',
                'start time': 'start_time',
                'stop': 'stop_time',
                'stop time': 'stop_time',
                'date of service': 'date_of_service',
                'dos': 'date_of_service',
                'date of post': 'date_of_post',
                'dop': 'date_of_post',
                'time': 'time_min',
                'time min': 'time_min',
                'minutes': 'time_min',
                'anes base': 'anes_base_units',
                'anes base units': 'anes_base_units',
                'med base': 'med_base_units',
                'med base units': 'med_base_units',
                'other': 'other_units',
                'other units': 'other_units',
                'chg': 'chg_amt',
                'chg amt': 'chg_amt',
                'charge': 'chg_amt',
                'amount': 'chg_amt'
            }
            
            # Rename columns based on mapping
            for old_name, new_name in column_mapping.items():
                matching_cols = [col for col in cleaned_df.columns if old_name.lower() in str(col).lower()]
                if matching_cols:
                    cleaned_df = cleaned_df.rename(columns={matching_cols[0]: new_name})
            
            # Convert numeric columns
            numeric_columns = ['time_min', 'anes_base_units', 'med_base_units', 'other_units', 'chg_amt']
            for col in numeric_columns:
                if col in cleaned_df.columns:
                    cleaned_df[col] = pd.to_numeric(cleaned_df[col].astype(str).str.replace(',', ''), errors='coerce')
            
            # Remove rows where ticket_ref is not a valid 8-digit number
            if 'ticket_ref' in cleaned_df.columns:
                cleaned_df = cleaned_df[cleaned_df['ticket_ref'].astype(str).str.match(r'^\d{8}$', na=False)]
            
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
        charge_transactions_data = []
        ticket_tracking_data = []

        lines = page_text.split('\n')
        
        for line in lines:
            # Skip header lines and empty lines
            if not line.strip() or 'Ticket' in line or 'Patient' in line or 'Total:' in line:
                continue
            
            # Look for lines starting with 8-digit ticket numbers
            if re.match(r'^\d{8}', line.strip()):
                # Split the line into parts
                parts = line.strip().split()
                
                if len(parts) < 10:  # Skip lines that are too short
                    continue
                
                try:
                    # Extract basic fields that are consistent
                    ticket_ref = parts[0]
                    
                    # Find the patient name (everything before UF/WC)
                    patient_parts = []
                    site_idx = None
                    for i, part in enumerate(parts[1:], 1):
                        if part in ['UF', 'WC']:
                            site_idx = i
                            break
                        patient_parts.append(part)
                    
                    if site_idx is None:
                        continue  # Skip if we can't find site code
                    
                    patient_name = ' '.join(patient_parts)
                    site_code = parts[site_idx]
                    
                    # Service type should be next
                    if site_idx + 1 >= len(parts):
                        continue
                    serv_type = parts[site_idx + 1]
                    
                    # CPT code should be next
                    if site_idx + 2 >= len(parts):
                        continue
                    cpt_code = parts[site_idx + 2]
                    
                    # Insurance type
                    if site_idx + 3 >= len(parts):
                        continue
                    insurance_type = parts[site_idx + 3]
                    
                    # For anesthesia records, look for time fields
                    if serv_type == 'An' and len(parts) >= site_idx + 8:
                        # Try to find time fields (HH:MM format)
                        start_time = None
                        stop_time = None
                        date_service = None
                        date_post = None
                        
                        # Look for time patterns
                        for i in range(site_idx + 4, min(site_idx + 10, len(parts))):
                            if re.match(r'\d{2}:\d{2}', parts[i]):
                                if start_time is None:
                                    start_time = parts[i]
                                elif stop_time is None:
                                    stop_time = parts[i]
                                    break
                        
                        # Look for date patterns (M/D/YY format)
                        for i in range(site_idx + 4, min(len(parts) - 5, len(parts))):
                            if re.match(r'\d{1,2}/\d{1,2}/\d{2}', parts[i]):
                                if date_service is None:
                                    date_service = parts[i]
                                elif date_post is None:
                                    date_post = parts[i]
                                    break
                        
                        # Look for numeric values at the end
                        numeric_parts = []
                        for part in parts[-10:]:  # Last 10 parts likely contain numeric data
                            try:
                                # Try to convert to float, handling commas
                                val = float(part.replace(',', ''))
                                numeric_parts.append(val)
                            except ValueError:
                                continue
                        
                        # Extract time, base units, and charge amount
                        time_min = 0
                        anes_base_units = 0.0
                        med_base_units = 0.0
                        other_units = 0.0
                        chg_amt = 0.0
                        
                        if len(numeric_parts) >= 5:
                            time_min = int(numeric_parts[0]) if numeric_parts[0] > 0 else 0
                            anes_base_units = numeric_parts[1]
                            med_base_units = numeric_parts[2]
                            other_units = numeric_parts[3]
                            chg_amt = numeric_parts[4]
                        
                        charge_transactions_data.append({
                            'ticket_ref': ticket_ref,
                            'patient_name': patient_name,
                            'site_code': site_code,
                            'serv_type': serv_type,
                            'cpt_code': cpt_code,
                            'insurance_type': insurance_type,
                            'start_time': start_time,
                            'stop_time': stop_time,
                            'date_of_service': date_service,
                            'date_of_post': date_post,
                            'time_min': time_min,
                            'anes_base_units': anes_base_units,
                            'med_base_units': med_base_units,
                            'other_units': other_units,
                            'chg_amt': chg_amt,
                        })
                    
                    elif serv_type in ['Me', 'Mo']:
                        # Medical/Modifier records have different structure
                        # Look for numeric values
                        numeric_parts = []
                        for part in parts[-8:]:  # Last 8 parts likely contain numeric data
                            try:
                                val = float(part.replace(',', ''))
                                numeric_parts.append(val)
                            except ValueError:
                                continue
                        
                        # Find date
                        date_service = None
                        date_post = None
                        for i in range(site_idx + 4, min(len(parts) - 3, len(parts))):
                            if re.match(r'\d{1,2}/\d{1,2}/\d{2}', parts[i]):
                                if date_service is None:
                                    date_service = parts[i]
                                elif date_post is None:
                                    date_post = parts[i]
                                    break
                        
                        med_base_units = 0.0
                        other_units = 0.0
                        chg_amt = 0.0
                        
                        if len(numeric_parts) >= 3:
                            med_base_units = numeric_parts[0] if numeric_parts[0] > 0 else 0.0
                            other_units = numeric_parts[1] if len(numeric_parts) > 1 else 0.0
                            chg_amt = numeric_parts[2] if len(numeric_parts) > 2 else 0.0
                        
                        charge_transactions_data.append({
                            'ticket_ref': ticket_ref,
                            'patient_name': patient_name,
                            'site_code': site_code,
                            'serv_type': serv_type,
                            'cpt_code': cpt_code,
                            'insurance_type': insurance_type,
                            'start_time': None,
                            'stop_time': None,
                            'date_of_service': date_service,
                            'date_of_post': date_post,
                            'time_min': 0,
                            'anes_base_units': 0.0,
                            'med_base_units': med_base_units,
                            'other_units': other_units,
                            'chg_amt': chg_amt,
                        })
                
                except (IndexError, ValueError) as e:
                    logger.debug(f"Could not parse line on page {page_num}: {line[:50]}... Error: {e}")
                    continue

        # Create DataFrames
        charge_df = pd.DataFrame(charge_transactions_data)
        ticket_df = pd.DataFrame(ticket_tracking_data)

        # Clean and anonymize the data
        if not charge_df.empty:
            charge_df = self._anonymize_dataframe(charge_df)
            logger.debug(f"Parsed {len(charge_df)} charge transactions from text on page {page_num}")

        if not ticket_df.empty:
            ticket_df = self._anonymize_dataframe(ticket_df)
            logger.debug(f"Parsed {len(ticket_df)} ticket tracking records from text on page {page_num}")

        return charge_df, ticket_df
    
    def _anonymize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove patient names and other sensitive information from DataFrame."""
        if df.empty:
            return df
        
        # List of column names that might contain patient information
        sensitive_columns = [
            'Patient Name', 'patient_name', 'Patient', 'patient',
            'Name', 'name', 'PATIENT NAME', 'PATIENT_NAME'
        ]
        
        # Remove sensitive columns
        columns_to_drop = [col for col in df.columns if col in sensitive_columns]
        if columns_to_drop:
            df = df.drop(columns=columns_to_drop)
            logger.info(f"Removed sensitive columns: {columns_to_drop}")
        
        return df

def test_extractor():
    """Test function to verify the extractor works."""
    extractor = MedicalReportExtractor()
    
    # Test with the sample file
    test_file = "data/archive/20250613-614-Compensation Reports_unlocked.pdf"
    
    try:
        summary, charges, tickets = extractor.extract_data_from_report(test_file)
        
        print("=== SUMMARY DATA ===")
        for key, value in summary.items():
            print(f"{key}: {value}")
        
        print(f"\n=== CHARGE TRANSACTIONS ({len(charges)} records) ===")
        if not charges.empty:
            print(charges.head())
            print(f"Columns: {list(charges.columns)}")
        else:
            print("No charge transaction data found")
        
        print(f"\n=== TICKET TRACKING ({len(tickets)} records) ===")
        if not tickets.empty:
            print(tickets.head())
            print(f"Columns: {list(tickets.columns)}")
        else:
            print("No ticket tracking data found")
            
    except Exception as e:
        print(f"Error testing extractor: {e}")

if __name__ == "__main__":
    test_extractor()