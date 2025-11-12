#!/usr/bin/env python3

from database_models import get_session, MonthlySummary, ChargeTransaction, MasterCase
from sqlalchemy import func

def check_database():
    session = get_session()
    
    try:
        # Check monthly summaries
        summaries = session.query(MonthlySummary).all()
        print(f"Monthly Summaries: {len(summaries)}")
        for summary in summaries:
            print(f"  - ID: {summary.id}, File: {summary.source_file}")
        
        # Check charge transactions
        total_transactions = session.query(ChargeTransaction).count()
        print(f"Total Charge Transactions: {total_transactions}")
        
        # Check master cases
        total_cases = session.query(MasterCase).count()
        print(f"Total Master Cases: {total_cases}")
        
        # Show some sample cases
        cases = session.query(MasterCase).limit(5).all()
        print(f"Sample Cases:")
        for case in cases:
            print(f"  - Ticket: {case.patient_ticket_number}, Date: {case.date_of_service}, CPT: {case.cpt_code}")
        
        # Check transactions by summary
        for summary in summaries:
            trans_count = session.query(ChargeTransaction).filter_by(summary_id=summary.id).count()
            print(f"  Summary {summary.id}: {trans_count} transactions")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    check_database() 