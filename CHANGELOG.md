# Changelog

All notable changes to the Medical Compensation Analysis System are documented in this file.

## [2.0.0] - 2025-01-12

### Added
- Database indexes for performance optimization on frequently queried columns
- Batch processing in `case_grouper.py` to handle 100K+ transactions efficiently
- Comprehensive `ARCHITECTURE.md` documentation
- Enhanced `setup_app.py` with dependency checking and environment setup
- Database migration script (`migrate_database_schema.py`) for schema upgrades
- Improved docstrings across all modules
- Type conversion and validation in `data_loader.py`
- Support for both date objects and strings in `case_grouper.py` (backward compatibility)

### Changed
- **BREAKING**: Database schema updated to use proper data types
  - Numeric fields (anes_time_min, anes_base_units, etc.): String → REAL
  - Date fields (date_of_service, date_of_post): String → Date
- Secret key now uses environment variable instead of hardcoded value
- Chart generation re-enabled in analysis page with error handling
- SQL queries now use SQLAlchemy ORM for safety (prevents SQL injection)
- README.md standardized to port 8888
- Improved error handling in batch upload process

### Fixed
- Unreachable code in `batch_upload` error handler
- SQL injection vulnerability in `data_analyzer.py` sort queries
- Port inconsistency between README (5003) and app.py (8888)
- Missing `pdfplumber` dependency in requirements.txt

### Removed
- 600+ lines of commented-out code:
  - Anonymization functions (no longer needed)
  - Chart generation comments
  - Database constraint comments
- Duplicate return statement in batch upload handler

### Security
- Secret key generation from environment variable with fallback
- SQL injection prevention via SQLAlchemy ORM
- Enhanced input validation in data loader

### Performance
- Database indexes added for:
  - `charge_transactions.phys_ticket_ref`
  - `charge_transactions.date_of_service`
  - `charge_transactions.cpt_code`
  - `master_cases.patient_ticket_number`
  - `master_cases.date_of_service`
  - `monthly_summary.pay_period_end_date`
- Batch processing in case grouper (1000 transactions per batch)
- Proper numeric types eliminate string-to-number conversion overhead

### Migration Notes
For users upgrading from v1.x:
1. Backup your database: `cp compensation.db compensation_backup.db`
2. Run migration: `python migrate_database_schema.py`
3. Verify data integrity
4. Update your `.env` file with `SECRET_KEY` if needed

## [1.0.0] - 2025-01-01

### Initial Release
- PDF extraction for compensation reports
- SQLite database with SQLAlchemy ORM
- Flask web dashboard with 5 main pages
- ASMG units calculation with temporal rules
- Master case grouping by patient ticket
- CPT code analysis and tracking
- Chart generation for trend analysis
- Command-line batch processing
- Automatic file archiving

### Features
- Extract summary, charge transactions, and ticket tracking from PDFs
- Store data in SQLite database
- Web interface for viewing and analyzing data
- Calculate ASMG units based on date-specific rules
- Group transactions into master cases
- Generate visual charts and analytics
- Process single files or batch directories
- Archive processed files automatically

### Known Limitations
- All fields stored as strings (fixed in v2.0)
- No database indexes (fixed in v2.0)
- Hardcoded secret key (fixed in v2.0)
- Port inconsistency in documentation (fixed in v2.0)
- Missing pdfplumber dependency (fixed in v2.0)

---

## Version History

- **v2.0.0** (2025-01-12) - Performance and Security Update
- **v1.0.0** (2025-01-01) - Initial Release

## Upgrade Path

### From v1.0 to v2.0
The v2.0 release includes database schema changes that require migration.

**Required Steps**:
1. Backup database
2. Run `python migrate_database_schema.py`
3. Test functionality
4. Update environment configuration

**What Changes**:
- Database field types upgraded to proper types
- Performance improvements via indexes
- Security enhancements

**Compatibility**:
- Old PDFs still work (no changes to extraction)
- Existing data migrated automatically
- No changes to web interface

### Future Versions
Future releases will maintain backward compatibility where possible and provide clear migration paths for breaking changes.

---

For detailed technical documentation, see [ARCHITECTURE.md](ARCHITECTURE.md)
For user guide, see [README.md](README.md)
