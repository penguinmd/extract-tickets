#!/usr/bin/env python3
"""
Migration script to add ASMG temporal rules table and initialize default rules.
"""

import os
import sys
from sqlalchemy import create_engine, text
from database_models import Base, DATABASE_URL
from asmg_calculator import ASMGCalculator

def migrate_asmg_rules():
    """Migrate the ASMG rules table and initialize default rules."""
    
    print("Starting ASMG rules migration...")
    
    # Create engine
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # Check if ASMG rules table exists
            result = conn.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='asmg_temporal_rules'
            """))
            
            if result.fetchone():
                print("Found existing ASMG rules table. Skipping table creation.")
            else:
                print("Creating new ASMG rules table...")
                # Create new table
                Base.metadata.create_all(engine, tables=[Base.metadata.tables['asmg_temporal_rules']])
                print("ASMG rules table created successfully.")
        
        # Initialize default rules
        print("Initializing default ASMG rules...")
        calculator = ASMGCalculator()
        calculator.initialize_default_rules()
        
        # Verify rules were created
        rules = calculator.get_all_rules()
        print(f"Found {len(rules)} ASMG rules in database:")
        for rule in rules:
            print(f"  - {rule.effective_date}: Anes={rule.anes_units_multiplier}, Time/={rule.anes_time_divisor}, Med={rule.med_units_multiplier}")
        
        print("ASMG rules migration completed successfully!")
        
    except Exception as e:
        print(f"Error during ASMG rules migration: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    success = migrate_asmg_rules()
    if success:
        print("\nMigration successful! ASMG rules are now available.")
    else:
        print("\nMigration failed. Please check the error messages above.")
        sys.exit(1) 