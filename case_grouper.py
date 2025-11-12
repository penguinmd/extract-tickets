import logging
from datetime import datetime, date, timedelta
from sqlalchemy.orm import sessionmaker
from database_models import get_session, ChargeTransaction, MasterCase
from sqlalchemy import and_

logger = logging.getLogger(__name__)

class CaseGrouper:
    def __init__(self, session):
        self.session = session

    def group_transactions_into_cases(self):
        """
        Groups all charge transactions into master cases based on:
        - patient (identified by ticket number within upload)
        - date of service
        - CPT code
        - initial start time
        
        This process is idempotent and can be re-run.
        """
        # Step 1: Get all transactions and group them by the case key criteria
        transactions = self.session.query(ChargeTransaction).all()

        # Step 2: Group transactions by ticket number (patient identifier)
        case_groups = self._group_transactions_by_case_criteria(transactions)

        # Step 3: Create or update MasterCase records and link transactions
        self._create_and_link_master_cases(case_groups)
        
        logger.info(f"Successfully grouped {len(transactions)} transactions into {len(case_groups)} cases")

    def _group_transactions_by_case_criteria(self, transactions):
        """
        Groups transactions by ticket number (patient identifier).
        Each ticket number represents one patient case, which can have multiple CPT codes and time periods.
        """
        case_groups = {}
        
        for transaction in transactions:
            # Skip transactions without required fields
            if not transaction.phys_ticket_ref:
                logger.warning(f"Skipping transaction {transaction.id} - missing ticket reference")
                continue
            
            # Use ticket number as the case key (patient identifier)
            case_key = transaction.phys_ticket_ref
            
            if case_key not in case_groups:
                case_groups[case_key] = []
            
            case_groups[case_key].append(transaction)
        
        return case_groups

    def _create_and_link_master_cases(self, case_groups):
        """
        Creates MasterCase records and links the charge transactions.
        Each case represents one patient (ticket number) and can have multiple CPT codes and time periods.
        """
        # Import ASMGCalculator for calculating ASMG units
        from asmg_calculator import ASMGCalculator
        calculator = ASMGCalculator(self.session)
        
        total_cases = len(case_groups)
        cases_without_dates = 0
        
        for case_key, transactions in case_groups.items():
            if not transactions:
                continue
            
            patient_ticket = case_key
            
            # Calculate summary fields from all transactions for this ticket
            total_anes_time = 0.0
            total_anes_base_units = 0.0
            total_med_base_units = 0.0
            total_other_units = 0.0
            
            # Collect all unique values for the case
            all_dates = set()
            all_cpt_codes = set()
            all_start_times = []
            all_stop_times = []
            ticket_numbers = set()
            
            for transaction in transactions:
                # Sum anesthesia time
                if transaction.anes_time_min:
                    try:
                        total_anes_time += float(transaction.anes_time_min)
                    except (ValueError, TypeError):
                        pass
                
                # Sum anesthesia base units
                if transaction.anes_base_units:
                    try:
                        total_anes_base_units += float(transaction.anes_base_units)
                    except (ValueError, TypeError):
                        pass
                
                # Sum medical base units
                if transaction.med_base_units:
                    try:
                        total_med_base_units += float(transaction.med_base_units)
                    except (ValueError, TypeError):
                        pass
                
                # Sum other units
                if transaction.other_units:
                    try:
                        total_other_units += float(transaction.other_units)
                    except (ValueError, TypeError):
                        pass
                
                # Collect unique values
                if transaction.date_of_service:
                    all_dates.add(transaction.date_of_service)
                if transaction.cpt_code:
                    all_cpt_codes.add(transaction.cpt_code)
                if transaction.start_time:
                    all_start_times.append(transaction.start_time)
                if transaction.stop_time:
                    all_stop_times.append(transaction.stop_time)
                if transaction.phys_ticket_ref:
                    ticket_numbers.add(transaction.phys_ticket_ref)
            
            # Determine case metadata
            # Use the earliest date if multiple dates exist
            date_of_service = None
            if all_dates:
                try:
                    # Filter out invalid date strings
                    valid_dates = []
                    for date_str in all_dates:
                        # Skip empty, None, or whitespace-only strings
                        if not date_str or str(date_str).strip() == '' or str(date_str).lower() in ['nan', 'none']:
                            continue
                        
                        try:
                            date_obj = datetime.strptime(str(date_str).strip(), '%m/%d/%y').date()
                            valid_dates.append(date_obj)
                        except ValueError:
                            logger.warning(f"Invalid date format for case {patient_ticket}: {date_str}")
                    
                    if valid_dates:
                        date_of_service = min(valid_dates)
                    else:
                        logger.warning(f"No valid dates found for case {patient_ticket}")
                except Exception as e:
                    logger.warning(f"Error processing dates for case {patient_ticket}: {str(e)}")
            
            # Combine all CPT codes into a comma-separated list
            cpt_codes_combined = ', '.join(sorted(all_cpt_codes)) if all_cpt_codes else ''
            
            # Find earliest start time and latest stop time
            initial_start_time = min(all_start_times) if all_start_times else ''
            latest_stop_time = max(all_stop_times) if all_stop_times else ''
            
            # Get ticket number info
            initial_ticket = min(ticket_numbers) if ticket_numbers else patient_ticket
            final_ticket = max(ticket_numbers) if ticket_numbers else patient_ticket
            
            # Calculate ASMG units
            asmg_units = 0.0
            if date_of_service and isinstance(date_of_service, (date, datetime)):
                try:
                    # Convert to date if it's a datetime
                    case_date = date_of_service.date() if isinstance(date_of_service, datetime) else date_of_service
                    asmg_units = calculator.calculate_asmg_units(
                        case_date=case_date,
                        total_anes_units=total_anes_base_units,
                        total_anes_time=total_anes_time,
                        total_med_units=total_med_base_units
                    )
                except Exception as e:
                    logger.warning(f"Error calculating ASMG units for case {patient_ticket}: {str(e)}")
                    asmg_units = 0.0
            else:
                cases_without_dates += 1
                logger.warning(f"No valid date for ASMG calculation for case {patient_ticket} - ASMG units set to 0.0")
            
            # Validate required fields before creating/updating case
            if not patient_ticket or str(patient_ticket).lower() in ['nan', 'none', '']:
                logger.warning(f"Skipping case with invalid ticket number: {patient_ticket}")
                continue

            # Check if case already exists
            existing_case = self.session.query(MasterCase).filter_by(
                patient_ticket_number=patient_ticket
            ).first()
            
            if existing_case:
                # Update existing case with new summary data
                existing_case.date_of_service = date_of_service
                existing_case.cpt_code = cpt_codes_combined
                existing_case.initial_start_time = initial_start_time
                existing_case.total_anes_time = total_anes_time
                existing_case.total_anes_base_units = total_anes_base_units
                existing_case.total_med_base_units = total_med_base_units
                existing_case.total_other_units = total_other_units
                existing_case.asmg_units = asmg_units
                existing_case.final_ticket_number = final_ticket
                existing_case.updated_at = datetime.utcnow()
                master_case = existing_case
            else:
                # Create new case
                master_case = MasterCase(
                    patient_ticket_number=patient_ticket,
                    date_of_service=date_of_service,
                    cpt_code=cpt_codes_combined,
                    initial_start_time=initial_start_time,
                    total_anes_time=total_anes_time,
                    total_anes_base_units=total_anes_base_units,
                    total_med_base_units=total_med_base_units,
                    total_other_units=total_other_units,
                    asmg_units=asmg_units,
                    initial_ticket_number=initial_ticket,
                    final_ticket_number=final_ticket
                )
                self.session.add(master_case)
                self.session.flush()  # Get the ID

            # Link all transactions to the master case
            for transaction in transactions:
                transaction.master_case_id = master_case.id
        
        self.session.commit()
        
        # Log summary
        if cases_without_dates > 0:
            summary_msg = f"Case grouping completed: {total_cases} total cases, {cases_without_dates} cases without valid dates for ASMG calculation"
            logger.info(summary_msg)
            print(f"INFO: {summary_msg}")
        else:
            summary_msg = f"Case grouping completed: {total_cases} total cases, all cases have valid dates for ASMG calculation"
            logger.info(summary_msg)
            print(f"INFO: {summary_msg}")

    def get_case_statistics(self):
        """
        Returns statistics about the cases.
        """
        total_cases = self.session.query(MasterCase).count()
        total_transactions = self.session.query(ChargeTransaction).count()
        linked_transactions = self.session.query(ChargeTransaction).filter(
            ChargeTransaction.master_case_id.isnot(None)
        ).count()
        
        return {
            'total_cases': total_cases,
            'total_transactions': total_transactions,
            'linked_transactions': linked_transactions,
            'unlinked_transactions': total_transactions - linked_transactions
        }

if __name__ == '__main__':
    session = get_session()
    grouper = CaseGrouper(session)
    grouper.group_transactions_into_cases()
    
    stats = grouper.get_case_statistics()
    print(f"Case grouping completed:")
    print(f"  Total cases: {stats['total_cases']}")
    print(f"  Total transactions: {stats['total_transactions']}")
    print(f"  Linked transactions: {stats['linked_transactions']}")
    print(f"  Unlinked transactions: {stats['unlinked_transactions']}")