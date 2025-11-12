#!/usr/bin/env python3
"""
ASMG Units Calculator
Calculates ASMG units based on temporal rules and case data.
"""

from datetime import datetime, date
from typing import Optional
from database_models import get_session, ASMGTemporalRules
import logging

logger = logging.getLogger(__name__)

class ASMGCalculator:
    """Calculates ASMG units based on temporal rules."""
    
    def __init__(self, session=None):
        self.session = session or get_session()
    
    def get_applicable_rule(self, case_date: date) -> Optional[ASMGTemporalRules]:
        """
        Get the applicable ASMG rule for a given case date.
        Returns the rule with the most recent effective_date that is <= case_date.
        """
        try:
            # Get the most recent rule that is effective on or before the case date
            rule = self.session.query(ASMGTemporalRules).filter(
                ASMGTemporalRules.effective_date <= case_date
            ).order_by(ASMGTemporalRules.effective_date.desc()).first()
            
            return rule
        except Exception as e:
            logger.error(f"Error getting applicable rule for date {case_date}: {str(e)}")
            return None
    
    def calculate_asmg_units(self, case_date: date, total_anes_units: float, 
                           total_anes_time: float, total_med_units: float) -> float:
        """
        Calculate ASMG units for a case based on temporal rules.
        
        Args:
            case_date: Date of service for the case
            total_anes_units: Total anesthesia base units
            total_anes_time: Total anesthesia time in minutes
            total_med_units: Total medical base units
            
        Returns:
            float: Calculated ASMG units
        """
        try:
            # Get the applicable rule for this date
            rule = self.get_applicable_rule(case_date)
            
            if not rule:
                # Default rule if no temporal rule found
                logger.warning(f"No ASMG rule found for date {case_date}, using defaults")
                anes_units_multiplier = 0.5
                anes_time_divisor = 10.0
                med_units_multiplier = 0.6
            else:
                anes_units_multiplier = rule.anes_units_multiplier
                anes_time_divisor = rule.anes_time_divisor
                med_units_multiplier = rule.med_units_multiplier
            
            # Calculate ASMG units based on the formula
            asmg_units = (
                (anes_units_multiplier * total_anes_units) +
                (total_anes_time / anes_time_divisor) +
                (med_units_multiplier * total_med_units)
            )
            
            return round(asmg_units, 2)
            
        except Exception as e:
            logger.error(f"Error calculating ASMG units: {str(e)}")
            return 0.0
    
    def get_default_rule(self) -> dict:
        """Get the default ASMG calculation rule."""
        return {
            'effective_date': date(2025, 1, 1),
            'anes_units_multiplier': 0.5,
            'anes_time_divisor': 10.0,
            'med_units_multiplier': 0.6,
            'description': 'Default rule for tickets performed after 1/1/2025'
        }
    
    def initialize_default_rules(self):
        """Initialize the database with default ASMG rules."""
        try:
            # Check if any rules exist
            existing_rules = self.session.query(ASMGTemporalRules).count()
            
            if existing_rules == 0:
                # Create default rule
                default_rule = ASMGTemporalRules(
                    effective_date=date(2025, 1, 1),
                    anes_units_multiplier=0.5,
                    anes_time_divisor=10.0,
                    med_units_multiplier=0.6,
                    description='Default rule for tickets performed after 1/1/2025'
                )
                
                self.session.add(default_rule)
                self.session.commit()
                logger.info("Initialized default ASMG rules")
            else:
                logger.info(f"ASMG rules already exist ({existing_rules} rules found)")
                
        except Exception as e:
            logger.error(f"Error initializing default rules: {str(e)}")
            self.session.rollback()
    
    def get_all_rules(self):
        """Get all ASMG temporal rules ordered by effective date."""
        try:
            return self.session.query(ASMGTemporalRules).order_by(
                ASMGTemporalRules.effective_date.desc()
            ).all()
        except Exception as e:
            logger.error(f"Error getting all rules: {str(e)}")
            return []
    
    def add_rule(self, effective_date: date, anes_units_multiplier: float, 
                anes_time_divisor: float, med_units_multiplier: float, 
                description: str = None) -> bool:
        """
        Add a new ASMG temporal rule.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if a rule already exists for this date
            existing_rule = self.session.query(ASMGTemporalRules).filter_by(
                effective_date=effective_date
            ).first()
            
            if existing_rule:
                # Update existing rule
                existing_rule.anes_units_multiplier = anes_units_multiplier
                existing_rule.anes_time_divisor = anes_time_divisor
                existing_rule.med_units_multiplier = med_units_multiplier
                existing_rule.description = description
                existing_rule.updated_at = datetime.utcnow()
            else:
                # Create new rule
                new_rule = ASMGTemporalRules(
                    effective_date=effective_date,
                    anes_units_multiplier=anes_units_multiplier,
                    anes_time_divisor=anes_time_divisor,
                    med_units_multiplier=med_units_multiplier,
                    description=description
                )
                self.session.add(new_rule)
            
            self.session.commit()
            logger.info(f"Successfully added/updated ASMG rule for {effective_date}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding ASMG rule: {str(e)}")
            self.session.rollback()
            return False
    
    def delete_rule(self, rule_id: int) -> bool:
        """
        Delete an ASMG temporal rule.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            rule = self.session.query(ASMGTemporalRules).filter_by(id=rule_id).first()
            if rule:
                self.session.delete(rule)
                self.session.commit()
                logger.info(f"Successfully deleted ASMG rule {rule_id}")
                return True
            else:
                logger.warning(f"ASMG rule {rule_id} not found")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting ASMG rule: {str(e)}")
            self.session.rollback()
            return False

if __name__ == "__main__":
    # Initialize default rules
    calculator = ASMGCalculator()
    calculator.initialize_default_rules()
    print("ASMG calculator initialized with default rules") 