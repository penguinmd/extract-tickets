#!/usr/bin/env python3
"""
Migration script to update the MasterCase table structure.
This script will:
1. Drop the existing MasterCase table
2. Create the new MasterCase table with the updated schema
3. Clear any existing case relationships
"""

import os
import sys
from sqlalchemy import create_engine, text
from database_models import Base, DATABASE_URL

def migrate_cases_table():
    """Migrate the MasterCase table to the new structure."""
    
    print("Starting MasterCase table migration...")
    
    # Create engine
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # Check if MasterCase table exists
            result = conn.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='master_cases'
            """))
            
            if result.fetchone():
                print("Found existing MasterCase table. Dropping it...")
                
                # Drop existing table
                conn.execute(text("DROP TABLE IF EXISTS master_cases"))
                conn.commit()
                print("Existing MasterCase table dropped.")
            
            # Create new table with updated schema
            print("Creating new MasterCase table...")
            Base.metadata.create_all(engine, tables=[Base.metadata.tables['master_cases']])
            print("New MasterCase table created successfully.")
            
            # Clear any existing master_case_id references in charge_transactions
            print("Clearing existing case relationships...")
            conn.execute(text("UPDATE charge_transactions SET master_case_id = NULL"))
            conn.commit()
            print("Existing case relationships cleared.")
            
            print("Migration completed successfully!")
            
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    success = migrate_cases_table()
    if success:
        print("\nMigration successful! You can now run the case grouper to populate the new cases.")
    else:
        print("\nMigration failed. Please check the error messages above.")
        sys.exit(1) 