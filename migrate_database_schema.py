#!/usr/bin/env python3
"""
Database migration script to update ChargeTransaction field types.
Converts String fields to proper types (REAL for numbers, Date for dates).

This script:
1. Backs up the existing database
2. Creates new tables with correct field types
3. Migrates data with proper type conversions
4. Adds indexes for performance
"""

import sqlite3
import shutil
from datetime import datetime
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = 'compensation.db'
BACKUP_PATH = f'compensation_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'

def backup_database():
    """Create a backup of the existing database."""
    if not Path(DB_PATH).exists():
        logger.info(f"No existing database found at {DB_PATH}, skipping backup")
        return False

    logger.info(f"Creating backup: {BACKUP_PATH}")
    shutil.copy2(DB_PATH, BACKUP_PATH)
    logger.info("Backup created successfully")
    return True

def safe_float(value):
    """Convert value to float, return None if conversion fails."""
    if value is None or value == '' or str(value).strip().lower() in ['', 'nan', 'none']:
        return None
    try:
        return float(str(value).replace(',', ''))
    except (ValueError, TypeError):
        return None

def safe_date(value):
    """Convert M/D/YY string to YYYY-MM-DD format, return None if conversion fails."""
    if value is None or value == '' or str(value).strip().lower() in ['', 'nan', 'none']:
        return None
    try:
        # Parse M/D/YY format
        date_obj = datetime.strptime(str(value).strip(), '%m/%d/%y')
        return date_obj.strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        return None

def migrate_charge_transactions(conn):
    """Migrate charge_transactions table to new schema with proper types."""
    cursor = conn.cursor()

    # Check if old table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='charge_transactions'")
    if not cursor.fetchone():
        logger.info("No existing charge_transactions table to migrate")
        return

    logger.info("Migrating charge_transactions table...")

    # Rename old table
    cursor.execute("ALTER TABLE charge_transactions RENAME TO charge_transactions_old")

    # Create new table with proper types
    cursor.execute("""
    CREATE TABLE charge_transactions (
        id INTEGER PRIMARY KEY,
        summary_id INTEGER NOT NULL,
        master_case_id INTEGER,
        phys_ticket_ref TEXT,
        note TEXT,
        original_chg_mo TEXT,
        site_code TEXT,
        serv_type TEXT,
        cpt_code TEXT,
        pay_code TEXT,
        start_time TEXT,
        stop_time TEXT,
        ob_case_pos TEXT,
        date_of_service DATE,
        date_of_post DATE,
        split_percent REAL,
        anes_time_min REAL,
        anes_base_units REAL,
        med_base_units REAL,
        other_units REAL,
        chg_amt REAL,
        sub_pool_percent REAL,
        sb_pl_time_min REAL,
        anes_base REAL,
        med_base REAL,
        grp_pool_percent REAL,
        gr_pl_time_min REAL,
        grp_anes_base REAL,
        grp_med_base REAL,
        created_at TIMESTAMP,
        FOREIGN KEY (summary_id) REFERENCES monthly_summary(id),
        FOREIGN KEY (master_case_id) REFERENCES master_cases(id)
    )
    """)

    # Migrate data with type conversions
    cursor.execute("SELECT * FROM charge_transactions_old")
    columns = [description[0] for description in cursor.description]

    migrated_count = 0
    error_count = 0

    for row in cursor.fetchall():
        row_dict = dict(zip(columns, row))

        try:
            # Convert numeric fields
            split_percent = safe_float(row_dict.get('split_percent'))
            anes_time_min = safe_float(row_dict.get('anes_time_min'))
            anes_base_units = safe_float(row_dict.get('anes_base_units'))
            med_base_units = safe_float(row_dict.get('med_base_units'))
            other_units = safe_float(row_dict.get('other_units'))
            chg_amt = safe_float(row_dict.get('chg_amt'))
            sub_pool_percent = safe_float(row_dict.get('sub_pool_percent'))
            sb_pl_time_min = safe_float(row_dict.get('sb_pl_time_min'))
            anes_base = safe_float(row_dict.get('anes_base'))
            med_base = safe_float(row_dict.get('med_base'))
            grp_pool_percent = safe_float(row_dict.get('grp_pool_percent'))
            gr_pl_time_min = safe_float(row_dict.get('gr_pl_time_min'))
            grp_anes_base = safe_float(row_dict.get('grp_anes_base'))
            grp_med_base = safe_float(row_dict.get('grp_med_base'))

            # Convert date fields
            date_of_service = safe_date(row_dict.get('date_of_service'))
            date_of_post = safe_date(row_dict.get('date_of_post'))

            # Insert into new table
            conn.execute("""
            INSERT INTO charge_transactions (
                id, summary_id, master_case_id, phys_ticket_ref, note, original_chg_mo,
                site_code, serv_type, cpt_code, pay_code, start_time, stop_time,
                ob_case_pos, date_of_service, date_of_post, split_percent,
                anes_time_min, anes_base_units, med_base_units, other_units, chg_amt,
                sub_pool_percent, sb_pl_time_min, anes_base, med_base,
                grp_pool_percent, gr_pl_time_min, grp_anes_base, grp_med_base, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row_dict['id'], row_dict['summary_id'], row_dict.get('master_case_id'),
                row_dict.get('phys_ticket_ref'), row_dict.get('note'), row_dict.get('original_chg_mo'),
                row_dict.get('site_code'), row_dict.get('serv_type'), row_dict.get('cpt_code'),
                row_dict.get('pay_code'), row_dict.get('start_time'), row_dict.get('stop_time'),
                row_dict.get('ob_case_pos'), date_of_service, date_of_post, split_percent,
                anes_time_min, anes_base_units, med_base_units, other_units, chg_amt,
                sub_pool_percent, sb_pl_time_min, anes_base, med_base,
                grp_pool_percent, gr_pl_time_min, grp_anes_base, grp_med_base, row_dict.get('created_at')
            ))
            migrated_count += 1

        except Exception as e:
            logger.warning(f"Error migrating row {row_dict.get('id')}: {str(e)}")
            error_count += 1
            continue

    # Drop old table
    cursor.execute("DROP TABLE charge_transactions_old")

    logger.info(f"Migrated {migrated_count} charge transaction records")
    if error_count > 0:
        logger.warning(f"Failed to migrate {error_count} records")

    conn.commit()

def add_indexes(conn):
    """Add indexes for frequently queried columns."""
    logger.info("Adding database indexes...")

    cursor = conn.cursor()

    indexes = [
        ("idx_ct_phys_ticket", "charge_transactions", "phys_ticket_ref"),
        ("idx_ct_date_service", "charge_transactions", "date_of_service"),
        ("idx_ct_cpt_code", "charge_transactions", "cpt_code"),
        ("idx_mc_patient_ticket", "master_cases", "patient_ticket_number"),
        ("idx_mc_date_service", "master_cases", "date_of_service"),
        ("idx_ms_pay_period", "monthly_summary", "pay_period_end_date"),
    ]

    for idx_name, table_name, column_name in indexes:
        try:
            # Check if table exists
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            if not cursor.fetchone():
                logger.info(f"Table {table_name} doesn't exist, skipping index {idx_name}")
                continue

            # Drop index if it exists
            cursor.execute(f"DROP INDEX IF EXISTS {idx_name}")

            # Create index
            cursor.execute(f"CREATE INDEX {idx_name} ON {table_name}({column_name})")
            logger.info(f"Created index: {idx_name}")
        except Exception as e:
            logger.warning(f"Error creating index {idx_name}: {str(e)}")

    conn.commit()
    logger.info("Indexes created successfully")

def main():
    """Run the migration."""
    logger.info("=" * 60)
    logger.info("DATABASE MIGRATION SCRIPT")
    logger.info("=" * 60)

    # Step 1: Backup
    has_existing_db = backup_database()

    if not has_existing_db:
        logger.info("No existing database to migrate. Will create new schema when app runs.")
        return

    # Step 2: Connect to database
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        # Step 3: Migrate charge_transactions
        migrate_charge_transactions(conn)

        # Step 4: Add indexes
        add_indexes(conn)

        logger.info("=" * 60)
        logger.info("MIGRATION COMPLETED SUCCESSFULLY")
        logger.info(f"Backup saved as: {BACKUP_PATH}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        logger.error("Restoring from backup...")
        conn.close()
        shutil.copy2(BACKUP_PATH, DB_PATH)
        logger.info("Database restored from backup")
        raise

    finally:
        conn.close()

if __name__ == "__main__":
    main()
