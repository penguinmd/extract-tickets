#!/usr/bin/env python3
"""
Migration script to add ASMG units column to MasterCase table and calculate ASMG units for existing cases.
"""

import logging
import sys
from sqlalchemy import text
from database_models import get_session, MasterCase
from asmg_calculator import ASMGCalculator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_asmg_units():
    """
    Migrate existing MasterCase records to include ASMG units.
    """
    session = get_session()
    
    try:
        # Check if asmg_units column already exists
        result = session.execute(text("""
            SELECT name FROM pragma_table_info('master_cases') 
            WHERE name = 'asmg_units'
        """))
        
        if result.fetchone():
            logger.info("ASMG units column already exists. Skipping column creation.")
        else:
            # Add asmg_units column to master_cases table
            logger.info("Adding asmg_units column to master_cases table...")
            session.execute(text("""
                ALTER TABLE master_cases 
                ADD COLUMN asmg_units REAL DEFAULT 0.0
            """))
            session.commit()
            logger.info("Successfully added asmg_units column.")
        
        # Calculate ASMG units for all existing cases
        logger.info("Calculating ASMG units for existing cases...")
        calculator = ASMGCalculator(session)
        
        cases = session.query(MasterCase).all()
        updated_count = 0
        
        for case in cases:
            try:
                if case.date_of_service:
                    asmg_units = calculator.calculate_asmg_units(
                        case_date=case.date_of_service,
                        total_anes_units=case.total_anes_base_units or 0.0,
                        total_anes_time=case.total_anes_time or 0.0,
                        total_med_units=case.total_med_base_units or 0.0
                    )
                    case.asmg_units = asmg_units
                    updated_count += 1
                else:
                    case.asmg_units = 0.0
                    updated_count += 1
            except Exception as e:
                logger.warning(f"Error calculating ASMG units for case {case.id}: {str(e)}")
                case.asmg_units = 0.0
                updated_count += 1
        
        session.commit()
        logger.info(f"Successfully updated ASMG units for {updated_count} cases.")
        
        # Verify the migration
        total_cases = session.query(MasterCase).count()
        cases_with_asmg = session.query(MasterCase).filter(
            MasterCase.asmg_units.isnot(None)
        ).count()
        
        logger.info(f"Migration verification:")
        logger.info(f"  Total cases: {total_cases}")
        logger.info(f"  Cases with ASMG units: {cases_with_asmg}")
        
        if total_cases == cases_with_asmg:
            logger.info("✅ Migration completed successfully!")
        else:
            logger.warning(f"⚠️  Migration may be incomplete. {total_cases - cases_with_asmg} cases missing ASMG units.")
            
    except Exception as e:
        session.rollback()
        logger.error(f"Migration failed: {str(e)}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    try:
        migrate_asmg_units()
        print("Migration completed successfully!")
    except Exception as e:
        print(f"Migration failed: {str(e)}")
        sys.exit(1) 