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

class ChargeTransaction(Base):
    """Table to store charge transaction data from ChargeTransaction Report."""
    __tablename__ = 'charge_transactions'
    
    id = Column(Integer, primary_key=True)
    summary_id = Column(Integer, ForeignKey('monthly_summary.id'), nullable=False)
    case_id = Column(String, nullable=True)  # Links to anesthesia_cases
    cpt_code = Column(String, nullable=True)  # Procedure Code
    billed_amount = Column(REAL, nullable=True)
    paid_amount = Column(REAL, nullable=True)
    insurance_carrier = Column(String, nullable=True)
    service_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    summary = relationship("MonthlySummary", back_populates="charge_transactions")

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