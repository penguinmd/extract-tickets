#!/usr/bin/env python3

from database_models import get_session, MasterCase, ChargeTransaction
from case_grouper import CaseGrouper

def regenerate_cases():
    session = get_session()
    
    try:
        # Clear all existing master cases
        session.query(MasterCase).delete(synchronize_session=False)
        session.commit()
        print("Cleared all existing master cases")
        
        # Regenerate cases from all transactions
        grouper = CaseGrouper(session)
        grouper.group_transactions_into_cases()
        
        # Get statistics
        stats = grouper.get_case_statistics()
        print(f"Case regeneration completed:")
        print(f"  Total cases: {stats['total_cases']}")
        print(f"  Total transactions: {stats['total_transactions']}")
        print(f"  Linked transactions: {stats['linked_transactions']}")
        print(f"  Unlinked transactions: {stats['unlinked_transactions']}")
        
    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    regenerate_cases() 