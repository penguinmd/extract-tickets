# Analytics Refactor Design Document

**Project**: Medical Compensation Analysis System
**Version**: 3.0.0
**Date**: 2025-11-11
**Author**: Architecture Team
**Status**: Approved for Implementation

---

## Executive Summary

This document outlines a comprehensive refactoring of the Medical Compensation Analysis System to add advanced analytics, forecasting, billing audit capabilities, and data export features. The refactor moves from a monolithic presentation-focused architecture to a clean three-layer architecture that separates data access, business logic, and presentation concerns.

**Timeline**: 5-6 weeks
**Risk Level**: Medium (phased migration with rollback capability)
**Business Value**: High (addresses all critical user needs)

---

## Problem Statement

### Current Pain Points

The user receives monthly PDF compensation reports from a billing company but lacks visibility into:

1. **Case Completeness**: Cannot verify if all performed cases appear in billing reports
2. **Comparative Analysis**: No month-over-month or year-over-year comparison capability
3. **Income Forecasting**: Cannot predict future compensation based on historical trends
4. **Workload Tracking**: Limited insight into productivity, case volume, and efficiency metrics
5. **Data Export**: Cannot extract data for accountant, tax prep, or external analysis
6. **Data Protection**: No backup/restore capability for historical data
7. **Billing Validation**: Cannot audit billing company for accuracy or missing cases
8. **Executive View**: Lacks bird's-eye view with drill-down capability

### User Requirements (Validated)

**Critical (P0)**:
- Case completeness verification
- Comparative analysis (MoM, YoY, QoQ)
- CSV/Excel data export
- Database backup/restore
- Executive dashboard with drill-down

**Important (P1)**:
- Workload metrics and productivity tracking
- Income forecasting with confidence intervals
- ASMG calculation reports
- Billing audit trail
- Performance benchmarks

---

## Architectural Design

### Three-Layer Architecture

The refactored system follows a strict separation of concerns:

```
┌─────────────────────────────────────────────────┐
│         Presentation Layer (Flask)              │
│  Routes, Templates, Export Handlers, UI Logic   │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│         Analytics Engine (Business Logic)        │
│  Metrics, Comparisons, Forecasting, Auditing    │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│         Data Access Layer (Repositories)         │
│  Database Queries, CRUD, Backup/Restore         │
└─────────────────────────────────────────────────┘
```

**Key Principles**:
- Each layer only communicates with the layer directly below
- Analytics engine has no Flask dependencies (enables CLI tools, testing)
- Data layer has no business logic (pure data access)
- Presentation layer has minimal logic (orchestration only)

### Module Structure

```
extract-tickets/
├── data/                          # Data Access Layer (NEW)
│   ├── __init__.py
│   ├── models.py                  # Renamed from database_models.py
│   ├── repositories.py            # All database queries
│   └── backup.py                  # Backup/restore utilities
│
├── analytics/                     # Analytics Engine (NEW)
│   ├── __init__.py
│   ├── metrics.py                 # Core metric calculations
│   ├── comparisons.py             # Period-over-period analysis
│   ├── forecasting.py             # Income prediction models
│   ├── audit.py                   # Case completeness, billing validation
│   └── reports.py                 # ASMG reports, formatted output
│
├── exports/                       # Export Engine (NEW)
│   ├── __init__.py
│   ├── csv_exporter.py           # CSV export with configurable fields
│   ├── excel_exporter.py         # Excel with formatting and charts
│   └── pdf_exporter.py           # Professional PDF reports
│
├── app.py                        # Flask application (UPDATED)
├── templates/                    # Jinja2 templates (UPDATED)
│   ├── insights.html            # NEW: Executive dashboard
│   ├── audit.html               # NEW: Billing audit page
│   └── ...                      # Existing templates updated with export buttons
│
├── data_extractor.py            # Unchanged
├── data_loader.py               # UPDATED: Use data.repositories
├── case_grouper.py              # UPDATED: Use data.repositories
├── data_analyzer.py             # DEPRECATED: Logic moved to analytics/
│
└── cli_tools/                   # NEW: Command-line utilities
    ├── backup.py                # python backup.py create/restore
    └── export.py                # python export.py --type=csv --range=2024
```

---

## New Features

### 1. Executive Insights Dashboard (`/insights`)

**Purpose**: Bird's-eye view with drill-down capability

**Components**:
- **At-a-Glance Cards**: Current month income, YTD, vs last year (% change indicators)
- **Comparison Charts**: Side-by-side month comparisons with date range selector
- **Workload Metrics**: Cases/month, avg case time, productivity index
- **Income Velocity**: Running totals, burn rate, year-end projections
- **Alert System**: Flags for unusual drops, potential missing cases
- **Export Options**: Every chart has PNG/CSV/Excel export

**Implementation**:
```python
# analytics/metrics.py
class WorkloadMetrics:
    def cases_per_period(self, start_date, end_date, granularity='month')
    def average_case_duration(self, date_range)
    def productivity_index(self, date_range)  # cases per hour
    def case_mix_distribution(self, date_range)  # by CPT code

# analytics/comparisons.py
class PeriodComparison:
    def month_over_month(self, metric, num_months=12)
    def year_over_year(self, metric, years=[2023, 2024, 2025])
    def quarter_over_quarter(self, metric)
    def percent_change_analysis(self, current, previous)
```

**UI/UX**:
- Responsive grid layout with collapsible sections
- Interactive charts (hover for details)
- Date range picker for all comparisons
- Export button on every chart/table
- Alert badges for anomalies

### 2. Billing Audit & Case Tracking (`/audit`)

**Purpose**: Verify billing company accuracy and completeness

**Components**:
- **Expected vs Actual**: Compare user's case log against billed cases
- **Missing Case Detection**: Cases in user log but not in billing
- **Discrepancy Report**: Billing items not recognized by user
- **Transaction Timeline**: Visual representation of billing dates
- **Audit Trail Export**: Generate reports for disputes

**Implementation**:
```python
# analytics/audit.py
class BillingAudit:
    def compare_case_logs(self, user_log, billing_data)
    def find_missing_cases(self, expected_cases, actual_cases)
    def detect_discrepancies(self, threshold=0.1)  # 10% variance
    def generate_audit_report(self, date_range)
    def calculate_expected_income(self, historical_avg, case_count)

# data/models.py (NEW TABLE)
class UserCaseLog(Base):
    __tablename__ = 'user_case_log'
    id = Column(Integer, primary_key=True)
    case_date = Column(Date, nullable=False)
    patient_ticket = Column(String, nullable=True)
    cpt_codes = Column(String, nullable=True)  # Comma-separated
    notes = Column(String, nullable=True)
    verified_in_billing = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Workflow**:
1. User uploads personal case log (CSV: date, ticket, CPT codes)
2. System matches against billing data
3. Flags cases in log but not billed (missing)
4. Flags billed cases not in log (unexpected)
5. Generate audit report with evidence for billing company

### 3. Income Forecasting Engine

**Purpose**: Predict future compensation with confidence intervals

**Models**:
1. **Historical Averaging**: Simple 3/6/12 month rolling average
2. **Seasonal Adjustment**: Account for typical slow/busy periods
3. **Trend Analysis**: Linear regression on historical data
4. **Confidence Intervals**: Show range of likely outcomes

**Implementation**:
```python
# analytics/forecasting.py
class IncomeForecast:
    def rolling_average_forecast(self, months_back=6, months_forward=3)
    def seasonal_adjusted_forecast(self, years_history=2)
    def trend_line_forecast(self, method='linear')
    def confidence_interval(self, forecast, confidence=0.95)
    def scenario_analysis(self, base_case, optimistic, pessimistic)

    def forecast_next_quarter(self):
        """Combined forecast using all models"""
        historical = self.rolling_average_forecast()
        seasonal = self.seasonal_adjusted_forecast()
        trend = self.trend_line_forecast()
        return self._weighted_average([historical, seasonal, trend])
```

**Storage**:
```python
# data/models.py (NEW TABLE)
class ForecastSnapshot(Base):
    __tablename__ = 'forecast_snapshots'
    id = Column(Integer, primary_key=True)
    created_date = Column(Date, nullable=False)
    forecast_date = Column(Date, nullable=False)
    predicted_amount = Column(REAL, nullable=False)
    actual_amount = Column(REAL, nullable=True)  # Filled in later
    confidence_level = Column(REAL, nullable=True)  # 0.95 = 95%
    model_used = Column(String, nullable=True)  # 'rolling_avg', 'seasonal', etc.
```

**UI Components**:
- Forecast chart showing next 3/6/12 months
- Confidence bands (shaded region)
- "What-if" calculator: Adjust case volume assumptions
- Accuracy tracking: Compare past forecasts to actuals

### 4. Universal Export System

**Purpose**: Extract data in multiple formats for external use

**Formats**:
- **CSV**: Raw data with all fields
- **Excel**: Formatted with embedded charts, multiple sheets
- **PDF**: Professional reports with ASMG calculations

**Implementation**:
```python
# exports/csv_exporter.py
class CSVExporter:
    def export_compensation_summary(self, date_range, filepath)
    def export_transactions(self, filters, filepath)
    def export_master_cases(self, filters, filepath)
    def export_forecast(self, forecast_data, filepath)

# exports/excel_exporter.py
class ExcelExporter:
    def export_workbook(self, data_dict, filepath):
        """Create multi-sheet Excel with formatting"""
        # Sheet 1: Summary
        # Sheet 2: Monthly breakdown
        # Sheet 3: Transactions
        # Sheet 4: Charts (embedded)

    def add_chart_to_sheet(self, sheet, chart_type, data_range)

# exports/pdf_exporter.py
class PDFExporter:
    def generate_asmg_report(self, case_data, filepath)
    def generate_audit_report(self, audit_results, filepath)
    def generate_monthly_summary(self, month, year, filepath)
```

**Export Configuration**:
```python
# User-configurable export templates
export_templates = {
    'tax_prep': {
        'format': 'excel',
        'sheets': ['monthly_summary', 'ytd_totals'],
        'fields': ['date', 'gross_pay', 'commission', 'bonus']
    },
    'billing_audit': {
        'format': 'pdf',
        'sections': ['expected_cases', 'billed_cases', 'discrepancies']
    }
}
```

**UI Integration**:
- Export button on every page/chart
- Export modal: Choose format, date range, fields
- Scheduled exports: Auto-generate monthly summary
- Download history: Track what was exported when

### 5. Backup & Restore Utilities

**Purpose**: Protect historical data and enable disaster recovery

**Implementation**:
```python
# data/backup.py
class DatabaseBackup:
    def create_backup(self, backup_dir='backups/', compress=True):
        """Create timestamped backup with checksum"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f"compensation_backup_{timestamp}.db"
        # SQLite backup with integrity check
        # Generate SHA256 checksum
        # Compress with gzip if requested
        return backup_path

    def restore_backup(self, backup_file, verify_checksum=True):
        """Restore database from backup"""
        # Verify checksum
        # Create restore point of current DB
        # Replace current DB with backup
        # Verify restored DB integrity

    def list_backups(self, backup_dir='backups/'):
        """List available backups with metadata"""
        # Return list with: filename, date, size, checksum

    def cleanup_old_backups(self, keep_daily=30, keep_monthly='all'):
        """Implement retention policy"""
        # Keep daily backups for 30 days
        # Keep one backup per month forever
```

**CLI Tools**:
```bash
# Create backup
python cli_tools/backup.py create

# List available backups
python cli_tools/backup.py list

# Restore specific backup
python cli_tools/backup.py restore backups/compensation_backup_20250111_143022.db

# Verify backup integrity
python cli_tools/backup.py verify backups/compensation_backup_20250111_143022.db
```

**Automated Backups**:
- Daily backup at 2 AM (if app running)
- Backup before any schema migration
- Backup before bulk import
- Configurable retention policy

---

## Database Schema Changes

### New Tables

```python
# Audit log for all data changes
class AuditLog(Base):
    __tablename__ = 'audit_log'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    action_type = Column(String, nullable=False)  # 'insert', 'update', 'delete'
    entity_type = Column(String, nullable=False)  # 'charge_transaction', etc.
    entity_id = Column(Integer, nullable=False)
    old_value = Column(String, nullable=True)  # JSON snapshot
    new_value = Column(String, nullable=True)  # JSON snapshot
    notes = Column(String, nullable=True)

# Forecast tracking for accuracy measurement
class ForecastSnapshot(Base):
    __tablename__ = 'forecast_snapshots'
    id = Column(Integer, primary_key=True)
    created_date = Column(Date, nullable=False)
    forecast_date = Column(Date, nullable=False)
    predicted_amount = Column(REAL, nullable=False)
    actual_amount = Column(REAL, nullable=True)
    confidence_level = Column(REAL, nullable=True)
    model_used = Column(String, nullable=True)

# User's personal case log for billing verification
class UserCaseLog(Base):
    __tablename__ = 'user_case_log'
    id = Column(Integer, primary_key=True)
    case_date = Column(Date, nullable=False)
    patient_ticket = Column(String, nullable=True)
    cpt_codes = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    verified_in_billing = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# Export history tracking
class ExportLog(Base):
    __tablename__ = 'export_log'
    id = Column(Integer, primary_key=True)
    export_date = Column(DateTime, default=datetime.utcnow)
    export_type = Column(String, nullable=False)  # 'csv', 'excel', 'pdf'
    entity_type = Column(String, nullable=False)  # 'compensation', 'transactions'
    date_range_start = Column(Date, nullable=True)
    date_range_end = Column(Date, nullable=True)
    filename = Column(String, nullable=False)
    file_size = Column(Integer, nullable=True)
```

---

## Migration Strategy

### Phase A: Extract Data Layer (Week 1-2)

**Goals**:
- Create `data/` module with clean separation
- Move all database queries to repositories
- Maintain backward compatibility

**Tasks**:
1. Create `data/models.py` (rename `database_models.py`)
2. Create `data/repositories.py` with repository pattern:
   ```python
   class MonthlySummaryRepository:
       def find_by_date_range(self, start, end)
       def find_by_id(self, id)
       def save(self, summary)
       def delete(self, id)

   class ChargeTransactionRepository:
       def find_by_ticket(self, ticket_number)
       def find_by_date_range(self, start, end)
       def find_by_cpt_code(self, cpt_code)

   class MasterCaseRepository:
       def find_by_patient_ticket(self, ticket)
       def find_by_date_range(self, start, end)
       def get_statistics(self, filters)
   ```
3. Add comprehensive unit tests for each repository
4. Create backward compatibility shims in old files

**Testing**:
- Unit test each repository method with known data
- Integration test: Query via repository, verify results match old queries
- Performance test: Ensure no regression on large datasets

**Rollback**: Keep old code intact, can revert by removing `data/` module

### Phase B: Build Analytics Engine (Week 2-3)

**Goals**:
- Extract all business logic from presentation layer
- Implement new analytics capabilities
- Enable testability and CLI tools

**Tasks**:
1. Create `analytics/metrics.py`:
   - Migrate calculations from `data_analyzer.py`
   - Add workload, productivity, efficiency metrics

2. Create `analytics/comparisons.py`:
   - Month-over-month, year-over-year, quarter-over-quarter
   - Percent change analysis
   - Trend detection

3. Create `analytics/forecasting.py`:
   - Historical averaging models
   - Seasonal adjustment
   - Trend line fitting
   - Confidence intervals

4. Create `analytics/audit.py`:
   - Case completeness verification
   - Billing discrepancy detection
   - Expected vs actual comparisons

5. Create `analytics/reports.py`:
   - ASMG calculation reports
   - Monthly summary reports
   - Audit reports

**Testing**:
- Unit test each analytics function with known inputs/outputs
- Regression test: Ensure existing charts produce identical results
- Accuracy test: Validate forecast models against historical data

**Rollback**: Analytics engine isolated, can disable new features

### Phase C: Refactor Presentation Layer (Week 3-4)

**Goals**:
- Update Flask routes to use analytics engine
- Create new pages for insights and audit
- Add export capabilities everywhere

**Tasks**:
1. Update `app.py`:
   - Replace direct database queries with repository calls
   - Replace inline calculations with analytics engine calls
   - Add export endpoints for each page

2. Create new routes:
   ```python
   @app.route('/insights')
   def insights():
       # Executive dashboard

   @app.route('/audit')
   def audit():
       # Billing audit page

   @app.route('/forecast')
   def forecast():
       # Income forecasting

   @app.route('/export/<entity_type>/<format>')
   def export_data(entity_type, format):
       # Universal export endpoint
   ```

3. Update templates:
   - Add export button to all existing pages
   - Create `insights.html`
   - Create `audit.html`
   - Create `forecast.html`

4. Create `exports/` module:
   - CSV exporter with configurable fields
   - Excel exporter with formatting
   - PDF exporter with professional layout

**Testing**:
- UI regression test: All existing pages render correctly
- Export test: Verify each format produces valid output
- Integration test: End-to-end user workflows

**Rollback**: Can disable new routes, existing pages unaffected

### Phase D: Backup System & Polish (Week 4-5)

**Goals**:
- Implement backup/restore utilities
- Performance tuning and caching
- Documentation and deployment

**Tasks**:
1. Create `data/backup.py`:
   - Automated daily backups
   - Manual backup CLI tool
   - Restore with verification
   - Retention policy implementation

2. Create `cli_tools/`:
   - `backup.py`: Command-line backup/restore
   - `export.py`: Command-line data export

3. Performance optimization:
   - Add caching for expensive analytics
   - Optimize database queries
   - Add pagination for large datasets

4. Documentation:
   - Update README with new features
   - Create user guide for new pages
   - Document export formats and options
   - Document backup/restore procedures

5. Deployment:
   - Test with production data
   - User acceptance testing
   - Deploy to production
   - Monitor for issues

**Testing**:
- Backup/restore test: Verify data integrity
- Performance test: Measure analytics response times
- Load test: Simulate multiple concurrent users
- UAT: User validates all features

---

## Risk Mitigation

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Database migration fails | Low | High | Automated backups before migration, comprehensive testing, rollback scripts |
| Performance regression | Medium | Medium | Performance benchmarks in tests, caching strategy, database indexes already in place |
| Forecast model inaccuracy | Medium | Low | Multiple models with confidence intervals, track accuracy over time, user can adjust assumptions |
| Export failures on large datasets | Medium | Medium | Pagination, background job processing, progress indicators |
| Data loss during refactor | Low | High | Git worktree isolation, comprehensive backups, phased rollout |

### Process Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Scope creep | Medium | Medium | Strict adherence to approved design, defer nice-to-haves to v3.1 |
| Timeline overrun | Medium | Low | Phased approach allows early value delivery, can defer Phase D if needed |
| Incomplete testing | Low | High | Test requirements defined upfront, automated test suite, UAT before production |
| User confusion with new UI | Medium | Low | Progressive disclosure, tooltips, user guide, can disable features individually |

### Rollback Strategy

Each phase is isolated:
- **Phase A**: Can revert by removing `data/` module, old code intact
- **Phase B**: Can disable analytics features, no impact on existing functionality
- **Phase C**: Can disable new routes, existing pages unaffected
- **Phase D**: Can disable automated backups, CLI tools optional

Git worktree development means main branch remains stable until ready to merge.

---

## Success Metrics

### Immediate (Week 1-2)
- [ ] Data layer extracted with 100% test coverage
- [ ] All existing functionality still works
- [ ] No performance regression

### Short-term (Week 3-4)
- [ ] Executive insights dashboard operational
- [ ] Export functionality on all pages
- [ ] Backup/restore CLI tools working

### Medium-term (Week 5-6)
- [ ] Billing audit catches at least one discrepancy
- [ ] Forecast accuracy within 15% of actual
- [ ] User can complete monthly review in <10 minutes (down from ~30)

### Long-term (3+ months)
- [ ] All monthly reports uploaded and analyzed
- [ ] Forecast model accuracy improves with more data
- [ ] User identifies billing errors totaling >$X
- [ ] Time saved on monthly analysis: 20+ hours/year

---

## Future Enhancements (Post-v3.0)

**Out of scope for initial implementation**:
- Mobile app
- Multi-user authentication
- Cloud deployment
- Real-time PDF monitoring
- Machine learning forecast models
- Integration with accounting software
- Automated case log import from scheduling system
- Payer contract analysis

These can be considered for v3.1+ based on user feedback and priorities.

---

## Appendices

### A. File Structure (Complete)

```
extract-tickets/
├── data/                          # NEW: Data Access Layer
│   ├── __init__.py
│   ├── models.py                  # Renamed from database_models.py
│   ├── repositories.py            # All database queries
│   └── backup.py                  # Backup/restore utilities
│
├── analytics/                     # NEW: Analytics Engine
│   ├── __init__.py
│   ├── metrics.py                 # Core metrics
│   ├── comparisons.py             # Period comparisons
│   ├── forecasting.py             # Income forecasting
│   ├── audit.py                   # Billing verification
│   └── reports.py                 # Report generation
│
├── exports/                       # NEW: Export Engine
│   ├── __init__.py
│   ├── csv_exporter.py
│   ├── excel_exporter.py
│   └── pdf_exporter.py
│
├── cli_tools/                     # NEW: Command-line tools
│   ├── backup.py
│   └── export.py
│
├── docs/                          # NEW: Documentation
│   └── plans/
│       └── 2025-11-11-analytics-refactor-design.md
│
├── backups/                       # NEW: Backup storage
│
├── templates/                     # UPDATED: Templates
│   ├── base.html
│   ├── dashboard.html
│   ├── compensation.html
│   ├── tickets.html
│   ├── analysis.html
│   ├── insights.html              # NEW
│   ├── audit.html                 # NEW
│   └── forecast.html              # NEW
│
├── static/
├── tests/                         # NEW: Test suite
│   ├── test_repositories.py
│   ├── test_analytics.py
│   ├── test_exports.py
│   └── test_integration.py
│
├── app.py                        # UPDATED: Flask app
├── data_extractor.py             # Unchanged
├── data_loader.py                # UPDATED: Use repositories
├── case_grouper.py               # UPDATED: Use repositories
├── asmg_calculator.py            # Unchanged
├── data_analyzer.py              # DEPRECATED
├── setup_app.py                  # UPDATED: Initialize new tables
├── requirements.txt              # UPDATED: New dependencies
└── README.md                     # UPDATED: Document new features
```

### B. New Dependencies

```txt
# requirements.txt additions
openpyxl>=3.1.0          # Excel export
reportlab>=4.0.0         # PDF generation
pandas>=2.0.0            # Data manipulation (already present)
numpy>=1.24.0            # Numerical computing for forecasting
matplotlib>=3.7.0        # Charting (already present)
seaborn>=0.12.0          # Statistical visualization (already present)
```

### C. API Examples

```python
# Using the analytics engine
from analytics.metrics import WorkloadMetrics
from analytics.comparisons import PeriodComparison
from analytics.forecasting import IncomeForecast

# Calculate workload metrics
metrics = WorkloadMetrics(db_session)
cases_per_month = metrics.cases_per_period('2024-01-01', '2024-12-31')
productivity = metrics.productivity_index('2024-01-01', '2024-12-31')

# Compare periods
comparisons = PeriodComparison(db_session)
mom_change = comparisons.month_over_month('gross_pay', num_months=12)
yoy_change = comparisons.year_over_year('case_count', years=[2023, 2024])

# Generate forecast
forecast = IncomeForecast(db_session)
next_quarter = forecast.forecast_next_quarter()
confidence_band = forecast.confidence_interval(next_quarter, confidence=0.95)

# Export data
from exports.excel_exporter import ExcelExporter
exporter = ExcelExporter()
exporter.export_workbook({
    'summary': monthly_summaries,
    'transactions': charge_transactions,
    'forecast': forecast_data
}, 'output.xlsx')
```

---

## Approval & Sign-off

**Design Approved By**: User
**Approval Date**: 2025-11-11
**Ready for Implementation**: Yes
**Next Steps**: Create git worktree, begin Phase A implementation
