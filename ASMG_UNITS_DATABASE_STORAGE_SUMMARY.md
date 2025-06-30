# ASMG Units Database Storage Implementation Summary

## Overview
This document summarizes the changes made to store calculated ASMG units in the database instead of calculating them on-the-fly, improving performance and enabling efficient database-level sorting.

## Problem
- ASMG units were calculated dynamically every time the cases page was loaded
- Sorting by ASMG units required Python-level sorting after calculation, which was inefficient
- ASMG units values don't change once a case is created (they're based on fixed temporal rules)

## Solution
Store calculated ASMG units in the database as a column in the `MasterCase` table.

## Changes Made

### 1. Database Model Updates (`database_models.py`)
- Added `asmg_units` column to `MasterCase` model:
  ```python
  asmg_units = Column(REAL, default=0.0)  # Calculated ASMG units based on temporal rules
  ```

### 2. Case Grouping Updates (`case_grouper.py`)
- Imported `ASMGCalculator` in the case grouper
- Added ASMG units calculation when creating or updating master cases:
  ```python
  # Calculate ASMG units
  asmg_units = calculator.calculate_asmg_units(
      case_date=case_date,
      total_anes_units=total_anes_base_units,
      total_anes_time=total_anes_time,
      total_med_units=total_med_base_units
  )
  ```
- Store calculated ASMG units in both new case creation and case updates

### 3. Data Analyzer Updates (`data_analyzer.py`)
- Simplified `get_master_cases()` method to use stored ASMG units
- Removed on-the-fly ASMG units calculation
- Removed special case handling for ASMG units sorting (now handled at database level)
- Database-level sorting now works for all fields including ASMG units

### 4. Migration Script (`migrate_asmg_units.py`)
- Created migration script to add `asmg_units` column to existing `master_cases` table
- Calculates ASMG units for all existing cases
- Provides verification of migration success

## Benefits

### Performance Improvements
- **Faster page loads**: No need to calculate ASMG units on every request
- **Efficient sorting**: Database-level sorting instead of Python-level sorting
- **Reduced CPU usage**: Calculations done once during case creation/update

### Code Simplification
- Removed complex on-the-fly calculation logic
- Simplified data retrieval in `get_master_cases()`
- Consistent sorting behavior for all fields

### Data Consistency
- ASMG units are calculated and stored when cases are created/updated
- Values are consistent across all views and reports
- No risk of calculation errors during display

## Migration Results
- Successfully migrated 74 existing cases
- All cases now have ASMG units stored in the database
- Sorting by ASMG units works correctly in both ascending and descending order

## Testing Verification
- ✅ ASMG units sorting (ascending): 7.90 → 41.50
- ✅ ASMG units sorting (descending): 41.50 → 7.90
- ✅ All other sorting fields continue to work
- ✅ Case grouping still calculates and stores ASMG units for new cases
- ✅ Page load performance improved

## Future Considerations
- If ASMG temporal rules change, existing cases will retain their original calculated values
- New cases will use the updated rules
- Consider adding a "recalculate ASMG units" feature if rule changes need to be applied retroactively

## Files Modified
1. `database_models.py` - Added asmg_units column
2. `case_grouper.py` - Added ASMG units calculation during case creation/update
3. `data_analyzer.py` - Simplified to use stored ASMG units
4. `migrate_asmg_units.py` - New migration script

## Files Created
1. `migrate_asmg_units.py` - Migration script for existing data
2. `ASMG_UNITS_DATABASE_STORAGE_SUMMARY.md` - This summary document 