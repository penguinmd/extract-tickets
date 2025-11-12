# Architecture Documentation

## System Overview

The Medical Compensation Analysis System is a Flask-based web application designed to extract, store, and analyze medical compensation data from PDF reports.

## Technology Stack

- **Backend**: Python 3.8+, Flask
- **Database**: SQLite with SQLAlchemy ORM
- **PDF Processing**: pdfplumber
- **Data Analysis**: pandas, numpy
- **Visualization**: matplotlib, seaborn
- **Frontend**: HTML templates (Jinja2), Bootstrap

## Core Components

### 1. Data Extraction Layer (`data_extractor.py`)

**Purpose**: Extract structured data from PDF compensation reports

**Key Features**:
- Hybrid PDF parsing (table extraction + text parsing)
- Handles three data types: summary compensation, charge transactions, ticket tracking
- Robust parsing for variable-length patient names
- Supports multiple service types (Anesthesia, Medical, Modifier)

**Design Patterns**:
- Single Responsibility: One class handles all PDF extraction logic
- Template Method: Common extraction flow with specialized handlers

### 2. Data Loading Layer (`data_loader.py`)

**Purpose**: Insert extracted data into the database with validation

**Key Features**:
- Type conversion and validation before database insertion
- Duplicate detection and handling
- Referential integrity maintenance
- Automatic case grouping trigger

**Type Conversions**:
- Numeric fields: String → REAL
- Date fields: M/D/YY string → Date object
- String fields: Validated and cleaned

### 3. Data Analysis Layer (`data_analyzer.py`)

**Purpose**: Provide analytics and visualizations

**Key Features**:
- Summary statistics
- Trend analysis
- CPT code profitability tracking
- ASMG units calculations
- Chart generation

**Query Optimization**:
- Uses SQLAlchemy ORM for safe query construction
- Indexed columns for fast lookups
- Batch processing for large datasets

### 4. Case Grouping (`case_grouper.py`)

**Purpose**: Group charge transactions into master cases by patient ticket

**Algorithm**:
1. Fetch transactions in batches (default: 1000)
2. Group by patient ticket number
3. Aggregate time, units, and other metrics
4. Calculate ASMG units based on temporal rules
5. Link transactions to master cases

**Performance Considerations**:
- Batch processing to handle 100K+ transactions
- Idempotent design (safe to re-run)
- Efficient date handling (supports both date objects and strings)

### 5. ASMG Calculator (`asmg_calculator.py`)

**Purpose**: Calculate ASMG units based on temporal rules

**Formula**:
```
ASMG Units = (Anes Units × Multiplier) + (Anes Time ÷ Divisor) + (Med Units × Multiplier)
```

**Default Rule** (effective 2025-01-01):
- Anes Units Multiplier: 0.5
- Anes Time Divisor: 10.0
- Med Units Multiplier: 0.6

**Temporal Rules**:
- Rules are date-based
- Most recent rule for a given date is used
- Supports rule changes over time

### 6. Web Application (`app.py`)

**Routes**:
- `/` - Dashboard with summary statistics
- `/compensation` - Monthly compensation data
- `/tickets` - Detailed charge transactions
- `/cases` - Master cases with ASMG units
- `/analysis` - Visual analytics and charts
- `/asmg_rules` - ASMG rules management
- `/cpt_codes` - CPT code analysis
- `/upload` - File upload handler
- `/batch_upload` - Batch file upload handler

**Security Features**:
- Environment variable for secret key
- File upload validation
- SQL injection prevention via SQLAlchemy
- Input sanitization

## Database Schema

### Tables

#### monthly_summary
- **Purpose**: Store monthly compensation summary
- **Key Fields**: pay_period_start_date, pay_period_end_date, gross_pay
- **Relationships**: One-to-many with charge_transactions and anesthesia_cases
- **Indexes**: pay_period_end_date

#### charge_transactions
- **Purpose**: Store individual charge transactions
- **Key Fields**: phys_ticket_ref, cpt_code, date_of_service, anes_time_min, anes_base_units
- **Type Changes** (v2.0):
  - Numeric fields now use REAL instead of String
  - Date fields now use Date instead of String
- **Relationships**: Many-to-one with monthly_summary, many-to-one with master_cases
- **Indexes**: phys_ticket_ref, date_of_service, cpt_code

#### master_cases
- **Purpose**: Group transactions by patient ticket number
- **Key Fields**: patient_ticket_number, total_anes_time, total_anes_base_units, asmg_units
- **Calculated Fields**: ASMG units (stored for performance)
- **Relationships**: One-to-many with charge_transactions
- **Indexes**: patient_ticket_number, date_of_service

#### anesthesia_cases
- **Purpose**: Store ticket tracking report data
- **Key Fields**: case_id, case_type, date_closed, commission_earned
- **Relationships**: Many-to-one with monthly_summary

#### asmg_temporal_rules
- **Purpose**: Store temporal rules for ASMG calculations
- **Key Fields**: effective_date, anes_units_multiplier, anes_time_divisor, med_units_multiplier
- **Usage**: Applied based on case date_of_service

## Data Flow

```
┌─────────────────┐
│   PDF Report    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ data_extractor  │ ← Hybrid PDF parsing
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  data_loader    │ ← Type conversion & validation
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   SQLite DB     │
└────────┬────────┘
         │
         ├─────────────────────────┐
         │                         │
         ▼                         ▼
┌─────────────────┐       ┌─────────────────┐
│  case_grouper   │       │ data_analyzer   │
└────────┬────────┘       └────────┬────────┘
         │                         │
         ▼                         ▼
┌─────────────────┐       ┌─────────────────┐
│  master_cases   │       │     Charts      │
└─────────────────┘       └─────────────────┘
         │                         │
         └──────────┬──────────────┘
                    │
                    ▼
           ┌─────────────────┐
           │   Flask App     │
           └────────┬────────┘
                    │
                    ▼
           ┌─────────────────┐
           │  Web Dashboard  │
           └─────────────────┘
```

## File Structure

```
extract-tickets/
├── app.py                      # Flask web application
├── data_extractor.py           # PDF extraction logic
├── data_loader.py              # Database loading logic
├── data_analyzer.py            # Analytics and charts
├── case_grouper.py             # Case grouping logic
├── asmg_calculator.py          # ASMG units calculator
├── database_models.py          # SQLAlchemy models
├── process_reports.py          # CLI orchestration
├── setup_app.py                # Application setup script
├── migrate_database_schema.py  # Database migration script
├── requirements.txt            # Python dependencies
├── templates/                  # HTML templates
│   ├── base.html
│   ├── dashboard.html
│   ├── compensation.html
│   ├── tickets.html
│   ├── cases.html
│   ├── analysis.html
│   ├── asmg_rules.html
│   └── cpt_codes.html
├── static/                     # Static assets
│   └── reports/                # Generated charts
├── data/                       # PDF uploads
│   └── archive/                # Processed files
└── logs/                       # Application logs
```

## Design Principles

### 1. Separation of Concerns
- Extraction logic separate from loading logic
- Analysis separate from data storage
- Web layer separate from business logic

### 2. Privacy First
- No patient names stored in database
- PDF files automatically archived
- All data stored locally (no external services)

### 3. Idempotent Processing
- Safe to re-run processing on same file
- Duplicate detection prevents data corruption
- Case grouping can be regenerated

### 4. Performance Optimization
- Database indexes on frequently queried columns
- Batch processing for large datasets
- Proper data types for numeric operations
- Query optimization via SQLAlchemy ORM

### 5. Error Resilience
- Comprehensive error handling and logging
- Graceful degradation (charts fail independently)
- Data validation at multiple layers
- Type conversion with fallbacks

## Security Considerations

### Current Implementation
- Secret key from environment variable
- File upload validation (PDF only)
- SQL injection prevention via ORM
- Input sanitization

### Not Implemented (Single User)
- Authentication/Authorization
- Multi-user session management
- Role-based access control
- API rate limiting

## Performance Characteristics

### Scalability Limits
- **Transactions**: Handles 100K+ transactions via batch processing
- **Files**: No hard limit (one file per request)
- **Database**: SQLite suitable for single user; PostgreSQL for scale
- **Charts**: Generated on-demand (may be slow with large datasets)

### Optimization Strategies
- Database indexes on key columns
- Batch processing for case grouping
- Proper data types (REAL vs String)
- Query result caching in DataFrame

## Future Enhancements (Out of Scope)

- Multi-user authentication
- Real-time file monitoring
- Export to accounting systems
- Mobile responsive design
- Predictive analytics
- API for external integrations
- Cloud deployment
- PostgreSQL support
- Automated backup system

## Migration Guide

### From v1.0 (String fields) to v2.0 (Proper types)

1. Backup database: `cp compensation.db compensation_backup.db`
2. Run migration: `python migrate_database_schema.py`
3. Verify: Check that numeric queries work correctly
4. If issues: Restore from backup

### Database Schema Changes
- `charge_transactions.anes_time_min`: String → REAL
- `charge_transactions.anes_base_units`: String → REAL
- `charge_transactions.med_base_units`: String → REAL
- `charge_transactions.date_of_service`: String → Date
- Added indexes for performance

## Testing Strategy

### Unit Tests
- PDF extraction with sample files
- Type conversion functions
- ASMG calculations

### Integration Tests
- Full pipeline: PDF → Database → Web
- Case grouping with real data
- Chart generation

### Manual Testing
- Upload PDF via web interface
- Verify data in database
- Check charts render correctly
- Test sorting and filtering

## Maintenance

### Regular Tasks
- Monitor log files for errors
- Archive old PDF files
- Backup database regularly
- Review ASMG rules for updates

### Troubleshooting
- Check logs/ directory for error details
- Verify database schema: `sqlite3 compensation.db ".schema"`
- Test PDF extraction: `python data_extractor.py`
- Regenerate cases: `/cases` page includes regenerate button
