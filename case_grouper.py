import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import sessionmaker
from database_models import get_session, ChargeTransaction, MasterCase

logger = logging.getLogger(__name__)

class CaseGrouper:
    def __init__(self, session):
        self.session = session

    def group_transactions_into_cases(self):
        """
        Groups all charge transactions into master cases.
        This process is idempotent and can be re-run.
        """
        # Step 1: Group transactions by physician ticket reference
        transactions_by_ticket = self._get_transactions_by_ticket()

        # Step 2: Merge ticket groups that belong to the same case
        master_cases_data = self._merge_ticket_groups(transactions_by_ticket)

        # Step 3: Create or update MasterCase records and link transactions
        self._create_and_link_master_cases(master_cases_data)

    def _get_transactions_by_ticket(self):
        """
        Retrieves all charge transactions and groups them by phys_ticket_ref.
        """
        transactions = self.session.query(ChargeTransaction).all()
        transactions_by_ticket = {}
        for t in transactions:
            if t.phys_ticket_ref not in transactions_by_ticket:
                transactions_by_ticket[t.phys_ticket_ref] = []
            transactions_by_ticket[t.phys_ticket_ref].append(t)
        return transactions_by_ticket

    def _merge_ticket_groups(self, transactions_by_ticket):
        """
        Merges ticket groups that belong to the same case based on patient name,
        date of service, and overlapping or nearby service times.
        """
        # First, group transactions by patient and date
        groups_by_patient_date = {}
        for ticket_ref, transactions in transactions_by_ticket.items():
            if not transactions:
                continue
            
            patient_name = transactions[0].patient_name
            date_of_service = transactions[0].date_of_service
            key = (patient_name, date_of_service)

            if key not in groups_by_patient_date:
                groups_by_patient_date[key] = []
            
            groups_by_patient_date[key].extend(transactions)

        # Now, merge groups with overlapping/nearby times
        merged_cases = []
        for key, transactions in groups_by_patient_date.items():
            # Sort transactions by start time to make merging easier
            transactions.sort(key=lambda t: datetime.strptime(t.start_time, '%H:%M') if t.start_time else datetime.min)

            if not merged_cases:
                merged_cases.append(transactions)
                continue

            was_merged = False
            for i, case in enumerate(merged_cases):
                if self._are_cases_related(case, transactions):
                    merged_cases[i].extend(transactions)
                    was_merged = True
                    break
            
            if not was_merged:
                merged_cases.append(transactions)

        return merged_cases

    def _are_cases_related(self, case1, case2, time_window_minutes=15):
        """
        Determines if two cases are related based on patient name, date, and time.
        """
        # Basic checks for patient name and date
        if case1[0].patient_name != case2[0].patient_name or \
           case1[0].date_of_service != case2[0].date_of_service:
            return False

        # Time-based check
        case1_start = min(datetime.strptime(t.start_time, '%H:%M') for t in case1 if t.start_time)
        case2_start = min(datetime.strptime(t.start_time, '%H:%M') for t in case2 if t.start_time)

        time_diff = abs((case1_start - case2_start).total_seconds() / 60)

        return time_diff <= time_window_minutes

    def _create_and_link_master_cases(self, master_cases_data):
        """
        Creates MasterCase records and links the charge transactions.
        """
        for transaction_group in master_cases_data:
            if not transaction_group:
                continue

            # Determine the primary attributes of the master case
            patient_name = transaction_group[0].patient_name
            date_of_service = datetime.strptime(transaction_group[0].date_of_service, '%m/%d/%y').date()
            
            # Aggregate start and stop times
            start_times = [datetime.strptime(t.start_time, '%H:%M') for t in transaction_group if t.start_time]
            stop_times = [datetime.strptime(t.stop_time, '%H:%M') for t in transaction_group if t.stop_time]
            
            earliest_start_time = min(start_times) if start_times else None
            latest_stop_time = max(stop_times) if stop_times else None

            # Create a unique key for the master case
            case_key = f"{patient_name}-{date_of_service}"

            # Create or get the MasterCase
            master_case = self.session.query(MasterCase).filter_by(case_key=case_key).first()
            if not master_case:
                master_case = MasterCase(
                    case_key=case_key,
                    patient_name=patient_name,
                    date_of_service=date_of_service,
                    earliest_start_time=earliest_start_time.strftime('%H:%M') if earliest_start_time else None,
                    latest_stop_time=latest_stop_time.strftime('%H:%M') if latest_stop_time else None,
                    primary_ticket_ref=transaction_group[0].phys_ticket_ref
                )
                self.session.add(master_case)
                self.session.flush()

            # Link all transactions in the group to the master case
            for transaction in transaction_group:
                transaction.master_case_id = master_case.id
        
        self.session.commit()

if __name__ == '__main__':
    session = get_session()
    grouper = CaseGrouper(session)
    grouper.group_transactions_into_cases()
    print("Successfully grouped transactions into master cases.")