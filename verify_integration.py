"""
Verify that the extraction integration is working properly
"""
import sqlite3
import pandas as pd

def verify_database():
    """Check the database contents after extraction"""
    
    conn = sqlite3.connect('compensation.db')
    
    print("=== DATABASE VERIFICATION ===")
    print()
    
    # Check monthly_summary table
    print("1. Monthly Summary Table:")
    print("-" * 40)
    summary_df = pd.read_sql_query("SELECT * FROM monthly_summary", conn)
    print(f"Records: {len(summary_df)}")
    if not summary_df.empty:
        print(summary_df[['id', 'pay_period_start_date', 'pay_period_end_date', 'gross_pay']].to_string())
    
    print()
    
    # Check charge_transactions table
    print("2. Charge Transactions Table:")
    print("-" * 40)
    
    # First, check the table structure
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(charge_transactions)")
    columns = cursor.fetchall()
    print("Table columns:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")
    
    print()
    
    # Check if 'case_id' column exists
    column_names = [col[1] for col in columns]
    if 'case_id' in column_names:
        print("⚠️  WARNING: 'case_id' column still exists in table!")
    else:
        print("✓ 'case_id' column correctly removed")
    
    print()
    
    # Check data
    charge_df = pd.read_sql_query("SELECT * FROM charge_transactions LIMIT 5", conn)
    print(f"Total records: {pd.read_sql_query('SELECT COUNT(*) as count FROM charge_transactions', conn)['count'][0]}")
    
    if not charge_df.empty:
        print("\nFirst 5 records (key columns):")
        key_cols = ['id', 'phys_ticket_ref', 'cpt_code', 'date_of_service', 'chg_amt']
        available_cols = [col for col in key_cols if col in charge_df.columns]
        print(charge_df[available_cols].to_string())
    
    print()
    
    # Check for any null phys_ticket_ref
    null_tickets = pd.read_sql_query(
        "SELECT COUNT(*) as count FROM charge_transactions WHERE phys_ticket_ref IS NULL OR phys_ticket_ref = ''", 
        conn
    )['count'][0]
    
    if null_tickets > 0:
        print(f"⚠️  WARNING: {null_tickets} records have empty phys_ticket_ref")
    else:
        print("✓ All records have phys_ticket_ref values")
    
    conn.close()
    
    print("\n=== VERIFICATION COMPLETE ===")

if __name__ == "__main__":
    verify_database()