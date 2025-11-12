"""
Data loader module for inserting extracted data into the database.
"""

import pandas as pd
from datetime import datetime
from typing import Dict, Any
import logging
from database_models import MonthlySummary, AnesthesiaCase, ChargeTransaction, MasterCase, get_session
from case_grouper import CaseGrouper

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataLoader:
    """Class to load extracted data into the database."""
    
    def __init__(self):
        self.session = None
    
    def load_report_data(self, summary_data: Dict[str, Any], 
                        charge_transactions: pd.DataFrame, 
                        ticket_tracking: pd.DataFrame) -> bool:
        """
        Load all extracted data from a report into the database.
        
        Args:
            summary_data (dict): Monthly summary data
            charge_transactions (DataFrame): Charge transaction data
            ticket_tracking (DataFrame): Ticket tracking data
            
        Returns:
            bool: True if successful, False otherwise
        """
        self.session = get_session()
        
        try:
            # 1. Insert monthly summary
            summary_id = self._insert_monthly_summary(summary_data)
            if not summary_id:
                logger.error("Failed to insert monthly summary")
                return False
            
            # 2. Insert charge transactions
            if not charge_transactions.empty:
                success = self._insert_charge_transactions(charge_transactions, summary_id)
                if not success:
                    logger.warning("Failed to insert some charge transactions")
            
            # 3. Group transactions into master cases
            if not charge_transactions.empty:
                try:
                    grouper = CaseGrouper(self.session)
                    grouper.group_transactions_into_cases()
                    stats = grouper.get_case_statistics()
                    logger.info(f"Case grouping completed: {stats['total_cases']} cases created from {stats['linked_transactions']} transactions")
                except Exception as e:
                    logger.warning(f"Failed to group transactions into cases: {str(e)}")
            
            # 4. Insert ticket tracking data (anesthesia cases)
            if not ticket_tracking.empty:
                success = self._insert_anesthesia_cases(ticket_tracking, summary_id)
                if not success:
                    logger.warning("Failed to insert some anesthesia cases")
            
            # Commit all changes
            self.session.commit()
            logger.info(f"Successfully loaded data for summary ID: {summary_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading data: {str(e)}")
            if self.session:
                self.session.rollback()
            return False
        finally:
            if self.session:
                self.session.close()
    
    def _insert_monthly_summary(self, summary_data: Dict[str, Any]) -> int:
        """Insert monthly summary data and return the ID."""
        try:
            # Check if this report already exists
            existing = self.session.query(MonthlySummary).filter_by(
                source_file=summary_data['source_file']
            ).first()
            
            if existing:
                logger.warning(f"Report {summary_data['source_file']} already exists. Deleting old data before re-inserting.")
                # Delete associated records first to maintain referential integrity
                self.session.query(ChargeTransaction).filter_by(summary_id=existing.id).delete(synchronize_session=False)
                self.session.query(AnesthesiaCase).filter_by(summary_id=existing.id).delete(synchronize_session=False)
                
                # Clear all master cases since they're derived from transactions
                self.session.query(MasterCase).delete(synchronize_session=False)
                
                # Now delete the summary record
                self.session.delete(existing)
                self.session.flush()  # Ensure deletion is processed before inserting new data
            
            # Create new summary record
            summary = MonthlySummary(
                pay_period_start_date=summary_data.get('pay_period_start_date'),
                pay_period_end_date=summary_data.get('pay_period_end_date'),
                base_salary=summary_data.get('base_salary'),
                total_commission=summary_data.get('total_commission'),
                bonus_amount=summary_data.get('bonus_amount'),
                gross_pay=summary_data.get('gross_pay'),
                source_file=summary_data['source_file']
            )
            
            self.session.add(summary)
            self.session.flush()  # Get the ID without committing
            
            logger.info(f"Inserted monthly summary with ID: {summary.id}")
            return summary.id
            
        except Exception as e:
            logger.error(f"Error inserting monthly summary: {str(e)}")
            return None
    
    def _insert_charge_transactions(self, df: pd.DataFrame, summary_id: int) -> bool:
        """Insert or update charge transaction data with proper type conversions."""
        try:
            upserted_count = 0
            for _, row in df.iterrows():
                try:
                    case_id = str(row.get('Phys Ticket Ref#', '')).strip()
                    if not case_id or case_id.lower() in ['nan', 'none', '']:
                        logger.warning(f"Skipping transaction with invalid ticket reference: {case_id}")
                        continue

                    # Helper functions for type conversion
                    def clean_string_field(value):
                        """Convert to string, return empty string for invalid values."""
                        if value is None or str(value).strip().lower() in ['', 'nan', 'none']:
                            return ''
                        return str(value).strip()

                    def clean_numeric_field(value):
                        """Convert to float, return None for invalid values."""
                        if value is None or str(value).strip().lower() in ['', 'nan', 'none']:
                            return None
                        try:
                            return float(str(value).replace(',', ''))
                        except (ValueError, TypeError):
                            return None

                    def clean_date_field(value):
                        """Convert M/D/YY string to date object, return None for invalid values."""
                        if value is None or str(value).strip().lower() in ['', 'nan', 'none']:
                            return None
                        try:
                            return datetime.strptime(str(value).strip(), '%m/%d/%y').date()
                        except (ValueError, TypeError):
                            return None

                    # Build record with proper types
                    record_data = {
                        'summary_id': summary_id,
                        # String fields
                        'phys_ticket_ref': clean_string_field(row.get('Phys Ticket Ref#', '')),
                        'note': clean_string_field(row.get('Note', '')),
                        'original_chg_mo': clean_string_field(row.get('Original Chg Mo', '')),
                        'site_code': clean_string_field(row.get('Site Code', '')),
                        'serv_type': clean_string_field(row.get('Serv Type', '')),
                        'cpt_code': clean_string_field(row.get('CPT Code', '')),
                        'pay_code': clean_string_field(row.get('Pay Code', '')),
                        'start_time': clean_string_field(row.get('Start Time', '')),
                        'stop_time': clean_string_field(row.get('Stop Time', '')),
                        'ob_case_pos': clean_string_field(row.get('OB Case Pos', '')),
                        # Date fields
                        'date_of_service': clean_date_field(row.get('Date of Service', '')),
                        'date_of_post': clean_date_field(row.get('Date of Post', '')),
                        # Numeric fields
                        'split_percent': clean_numeric_field(row.get('Split %', '')),
                        'anes_time_min': clean_numeric_field(row.get('Anes Time (Min)', '')),
                        'anes_base_units': clean_numeric_field(row.get('Anes Base Units', '')),
                        'med_base_units': clean_numeric_field(row.get('Med Base Units', '')),
                        'other_units': clean_numeric_field(row.get('Other Units', '')),
                        'chg_amt': clean_numeric_field(row.get('Chg Amt', '')),
                        'sub_pool_percent': clean_numeric_field(row.get('Sub Pool %', '')),
                        'sb_pl_time_min': clean_numeric_field(row.get('Sb Pl Time (Min)', '')),
                        'anes_base': clean_numeric_field(row.get('Anes Base', '')),
                        'med_base': clean_numeric_field(row.get('Med Base', '')),
                        'grp_pool_percent': clean_numeric_field(row.get('Grp Pool %', '')),
                        'gr_pl_time_min': clean_numeric_field(row.get('Gr Pl Time (Min)', '')),
                        'grp_anes_base': clean_numeric_field(row.get('Anes Base', '')),
                        'grp_med_base': clean_numeric_field(row.get('Med Base', '')),
                    }

                    # Use a composite key to find the existing transaction
                    # Include start_time AND stop_time to differentiate split cases
                    existing_transaction = self.session.query(ChargeTransaction).filter_by(
                        phys_ticket_ref=case_id,
                        cpt_code=record_data['cpt_code'],
                        date_of_service=record_data['date_of_service'],
                        start_time=record_data['start_time'],
                        stop_time=record_data['stop_time']
                    ).first()

                    if existing_transaction:
                        # Update the existing record
                        for key, value in record_data.items():
                            setattr(existing_transaction, key, value)
                    else:
                        # Insert a new record
                        new_transaction = ChargeTransaction(**record_data)
                        self.session.add(new_transaction)

                    upserted_count += 1
                except Exception as e:
                    logger.warning(f"Error upserting charge transaction row: {str(e)}")
                    continue

            logger.info(f"Upserted {upserted_count} charge transactions")
            return True
        except Exception as e:
            logger.error(f"Error upserting charge transactions: {str(e)}")
            return False
    
    def _insert_anesthesia_cases(self, df: pd.DataFrame, summary_id: int) -> bool:
        """Insert or update anesthesia case data from ticket tracking."""
        try:
            # Map common column names to our schema
            column_mapping = {
                'Ticket Number': 'case_id', 'ticket_number': 'case_id', 'Case ID': 'case_id', 'case_id': 'case_id', 'Ticket': 'case_id',
                'Case Type': 'case_type', 'case_type': 'case_type', 'Anesthesia Type': 'case_type', 'Type': 'case_type', 'Procedure': 'case_type',
                'Date Closed': 'date_closed', 'date_closed': 'date_closed', 'Closed Date': 'date_closed', 'Date': 'date_closed',
                'Commission': 'commission_earned', 'commission_earned': 'commission_earned', 'Commission Earned': 'commission_earned', 'Earned': 'commission_earned'
            }
            
            df_mapped = df.copy()
            for old_name, new_name in column_mapping.items():
                if old_name in df_mapped.columns:
                    df_mapped = df_mapped.rename(columns={old_name: new_name})
            
            upserted_count = 0
            for _, row in df_mapped.iterrows():
                try:
                    case_id = str(row.get('case_id', '')).strip()
                    if not case_id:
                        continue

                    record_data = {
                        'summary_id': summary_id,
                        'case_type': str(row.get('case_type', '')).strip() if row.get('case_type') else None,
                        'date_closed': self._parse_date_value(row.get('date_closed')),
                        'commission_earned': self._parse_monetary_value(row.get('commission_earned'))
                    }

                    existing_case = self.session.query(AnesthesiaCase).filter_by(case_id=case_id).first()

                    if existing_case:
                        for key, value in record_data.items():
                            setattr(existing_case, key, value)
                    else:
                        new_case = AnesthesiaCase(case_id=case_id, **record_data)
                        self.session.add(new_case)
                    
                    upserted_count += 1
                except Exception as e:
                    logger.warning(f"Error upserting anesthesia case row: {str(e)}")
                    continue
            
            logger.info(f"Upserted {upserted_count} anesthesia cases")
            return True
        except Exception as e:
            logger.error(f"Error upserting anesthesia cases: {str(e)}")
            return False
    
    def _parse_monetary_value(self, value) -> float:
        """Parse a monetary value from various formats."""
        if pd.isna(value) or value is None:
            return None
        
        try:
            # Convert to string and clean
            str_value = str(value).strip()
            if not str_value or str_value.lower() in ['', 'nan', 'none']:
                return None
            
            # Remove currency symbols and commas
            cleaned = str_value.replace('$', '').replace(',', '').replace('(', '-').replace(')', '')
            return float(cleaned)
        except (ValueError, TypeError):
            logger.warning(f"Could not parse monetary value: {value}")
            return None
    
    def _parse_date_value(self, value):
        """Parse a date value from various formats."""
        if pd.isna(value) or value is None:
            return None
        
        # Handle cases where the value is already a datetime object
        if isinstance(value, datetime):
            return value.date()
            
        try:
            str_value = str(value).strip()
            if not str_value or str_value.lower() in ['', 'nan', 'none']:
                return None
            
            # Try common date formats
            date_formats = ['%m/%d/%y', '%m/%d/%Y', '%Y-%m-%d', '%m-%d-%Y', '%d/%m/%Y']
            
            for fmt in date_formats:
                try:
                    return datetime.strptime(str_value, fmt).date()
                except ValueError:
                    continue
            
            logger.warning(f"Could not parse date value: {value}")
            return None
            
        except (ValueError, TypeError):
            logger.warning(f"Could not parse date value: {value}")
            return None

def test_loader():
    """Test function to verify the loader works."""
    from data_extractor import MedicalReportExtractor
    
    # Test with the sample file
    extractor = MedicalReportExtractor()
    loader = DataLoader()
    
    test_file = "data/archive/20250613-614-Compensation Reports_unlocked.pdf"
    
    try:
        summary, charges, tickets = extractor.extract_data_from_report(test_file)
        success = loader.load_report_data(summary, charges, tickets)
        
        if success:
            print("Data loaded successfully!")
        else:
            print("Failed to load data")
            
    except Exception as e:
        print(f"Error testing loader: {e}")

if __name__ == "__main__":
    test_loader()