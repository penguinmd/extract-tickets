"""
Database models for the Anesthesia Compensation & Practice Analysis Pipeline.
"""

from sqlalchemy import create_engine, Column, Integer, String, Date, REAL, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
import os

# Database configuration
DATABASE_URL = "sqlite:///compensation.db"

# Create engine and base
engine = create_engine(DATABASE_URL, echo=False)
Base = declarative_base()

class MonthlySummary(Base):
    """Table to store monthly compensation summary data."""
    __tablename__ = 'monthly_summary'
    
    id = Column(Integer, primary_key=True)
    pay_period_start_date = Column(Date, nullable=False)
    pay_period_end_date = Column(Date, nullable=False)
    base_salary = Column(REAL, nullable=True)
    total_commission = Column(REAL, nullable=True)
    bonus_amount = Column(REAL, nullable=True)
    gross_pay = Column(REAL, nullable=False)
    source_file = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    anesthesia_cases = relationship("AnesthesiaCase", back_populates="summary")
    charge_transactions = relationship("ChargeTransaction", back_populates="summary")

class AnesthesiaCase(Base):
    """Table to store individual anesthesia case data from Ticket Tracking Report."""
    __tablename__ = 'anesthesia_cases'
    
    id = Column(Integer, primary_key=True)
    summary_id = Column(Integer, ForeignKey('monthly_summary.id'), nullable=False)
    case_id = Column(String, nullable=True)  # e.g., Ticket Number
    case_type = Column(String, nullable=True)  # e.g., Anesthesia Type
    date_closed = Column(Date, nullable=True)
    commission_earned = Column(REAL, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    summary = relationship("MonthlySummary", back_populates="anesthesia_cases")

class ASMGTemporalRules(Base):
    """Table to store temporal rules for ASMG unit calculations."""
    __tablename__ = 'asmg_temporal_rules'
    
    id = Column(Integer, primary_key=True)
    effective_date = Column(Date, nullable=False)  # Date when this rule becomes effective
    anes_units_multiplier = Column(REAL, nullable=False, default=0.5)  # Multiplier for anesthesia base units
    anes_time_divisor = Column(REAL, nullable=False, default=10.0)  # Divisor for anesthesia time
    med_units_multiplier = Column(REAL, nullable=False, default=0.6)  # Multiplier for medical base units
    description = Column(String, nullable=True)  # Optional description of the rule
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Ensure effective_date is unique
    __table_args__ = (
        # Unique constraint on effective_date to prevent overlapping rules
    )

class MasterCase(Base):
    """A master case that groups multiple charge transactions by patient ticket number."""
    __tablename__ = 'master_cases'

    id = Column(Integer, primary_key=True)
    # Primary key fields (patient is identified by ticket number within each upload)
    patient_ticket_number = Column(String, nullable=False)  # Ticket number that identifies the patient
    date_of_service = Column(Date, nullable=True)  # Can be null if no date available
    cpt_code = Column(String, nullable=True)  # Can be null, or comma-separated list of CPT codes
    initial_start_time = Column(String, nullable=True)  # Earliest start time for this case
    
    # Summary fields
    total_anes_time = Column(REAL, default=0.0)  # Sum of all anesthesia times
    total_anes_base_units = Column(REAL, default=0.0)  # Sum of all anesthesia base units
    total_med_base_units = Column(REAL, default=0.0)  # Sum of all medical base units
    total_other_units = Column(REAL, default=0.0)  # Sum of all other units
    
    # Calculated ASMG units (stored in database for performance)
    asmg_units = Column(REAL, default=0.0)  # Calculated ASMG units based on temporal rules
    
    # Ticket number tracking
    initial_ticket_number = Column(String, nullable=False)  # First ticket number assigned
    final_ticket_number = Column(String, nullable=False)  # Most recent ticket number (defaults to initial)
    
    # Additional metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Create a unique constraint on patient_ticket_number since each ticket represents one patient case
    __table_args__ = (
        # Unique constraint on patient ticket number - each ticket represents one patient case
        # This allows multiple CPT codes and time periods within the same case
    )

    charge_transactions = relationship("ChargeTransaction", back_populates="master_case")

class ChargeTransaction(Base):
    """Table to store charge transaction data from ChargeTransaction Report."""
    __tablename__ = 'charge_transactions'
    
    id = Column(Integer, primary_key=True)
    summary_id = Column(Integer, ForeignKey('monthly_summary.id'), nullable=False)
    master_case_id = Column(Integer, ForeignKey('master_cases.id'))
    phys_ticket_ref = Column(String, nullable=True)
    note = Column(String, nullable=True)
    original_chg_mo = Column(String, nullable=True)
    site_code = Column(String, nullable=True)
    serv_type = Column(String, nullable=True)
    cpt_code = Column(String, nullable=True)
    pay_code = Column(String, nullable=True)
    start_time = Column(String, nullable=True)
    stop_time = Column(String, nullable=True)
    ob_case_pos = Column(String, nullable=True)
    date_of_service = Column(String, nullable=True)
    date_of_post = Column(String, nullable=True)
    split_percent = Column(String, nullable=True)
    anes_time_min = Column(String, nullable=True)
    anes_base_units = Column(String, nullable=True)
    med_base_units = Column(String, nullable=True)
    other_units = Column(String, nullable=True)
    chg_amt = Column(String, nullable=True)
    sub_pool_percent = Column(String, nullable=True)
    sb_pl_time_min = Column(String, nullable=True)
    anes_base = Column(String, nullable=True)
    med_base = Column(String, nullable=True)
    grp_pool_percent = Column(String, nullable=True)
    gr_pl_time_min = Column(String, nullable=True)
    grp_anes_base = Column(String, nullable=True)
    grp_med_base = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    summary = relationship("MonthlySummary", back_populates="charge_transactions")
    master_case = relationship("MasterCase", back_populates="charge_transactions")

def create_database():
    """Create all tables in the database."""
    Base.metadata.create_all(engine)
    print("Database tables created successfully.")

def get_session():
    """Get a database session."""
    Session = sessionmaker(bind=engine)
    return Session()

if __name__ == "__main__":
    # Create the database when this file is run directly
    create_database()