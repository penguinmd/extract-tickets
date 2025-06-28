# Medical Compensation Analysis System

A comprehensive web-based system for analyzing medical compensation reports with automated PDF data extraction, database storage, and interactive analytics dashboard.

## 🌟 Features

- **Automated PDF Processing**: Extract data from medical compensation reports
- **Multi-Page Web Dashboard**: Clean, professional interface with separate sections
- **Data Analysis**: Visual charts and insights for compensation trends
- **Privacy Compliant**: Automatic patient data anonymization
- **Robust Data Pipeline**: Error handling and data validation

## 📱 Web Interface

### Dashboard Pages
- **Dashboard (/)**: Overview with key statistics and file upload
- **Compensation (/compensation)**: Monthly compensation data and summaries
- **Tickets (/tickets)**: Detailed transaction data with search and filtering
- **Analysis (/analysis)**: Visual analytics with charts and insights

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Virtual environment (recommended)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd extract-tickets
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize database**
   ```bash
   python database_models.py
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Access the web interface**
   Open http://localhost:5003 in your browser

## 📊 Usage

### Upload Reports
1. Navigate to the Dashboard
2. Use the file upload section to select PDF compensation reports
3. Files are automatically processed and archived

### View Data
- **Compensation**: View monthly compensation summaries
- **Tickets**: Browse detailed transaction data with filtering
- **Analysis**: Explore visual analytics and trends

### Command Line Processing
```bash
# Process single file
python process_reports.py "path/to/report.pdf"

# Process directory (batch)
python process_reports.py "path/to/directory/" --create-db

# Test extraction only
python data_extractor.py
```

## 🏗️ Architecture

### Core Components
- **`app.py`**: Flask web application with multi-page interface
- **`data_extractor.py`**: PDF data extraction with hybrid parsing
- **`data_loader.py`**: Database operations and data loading
- **`data_analyzer.py`**: Analytics and visualization generation
- **`process_reports.py`**: Orchestration and batch processing
- **`database_models.py`**: SQLAlchemy database schema

### Data Flow
```
PDF Report → Data Extractor → Data Loader → SQLite Database → Web Dashboard
```

### Database Schema
- **monthly_summary**: Compensation summary data
- **charge_transactions**: Detailed transaction records
- **anesthesia_cases**: Case tracking information

## 🔧 Configuration

### Environment Variables
Create a `.env` file for configuration:
```
FLASK_ENV=development
DATABASE_URL=sqlite:///compensation.db
UPLOAD_FOLDER=data
```

### File Structure
```
extract-tickets/
├── app.py                 # Flask web application
├── data_extractor.py      # PDF data extraction
├── data_loader.py         # Database operations
├── data_analyzer.py       # Analytics and charts
├── process_reports.py     # Batch processing
├── database_models.py     # Database schema
├── requirements.txt       # Python dependencies
├── templates/             # HTML templates
│   ├── base.html
│   ├── dashboard.html
│   ├── compensation.html
│   ├── tickets.html
│   └── analysis.html
├── static/               # Static assets
├── data/                 # Upload directory
└── data/archive/         # Processed files
```

## 📈 Analytics Features

### Available Charts
- **Income Trends**: Monthly compensation over time
- **Seasonal Analysis**: Seasonal patterns and variations
- **Procedure Profitability**: Most profitable procedure types
- **Payer Performance**: Insurance carrier analysis

### Data Insights
- Monthly compensation summaries
- Transaction volume analysis
- CPT code frequency and profitability
- Insurance carrier payment patterns

## 🔒 Privacy & Security

- **Data Anonymization**: Patient names automatically removed
- **Local Storage**: All data stored locally in SQLite database
- **Secure Processing**: No data transmitted to external services
- **File Archiving**: Processed files moved to secure archive

## 🛠️ Development

### Testing
```bash
# Test data extraction
python data_extractor.py

# Test data loading
python data_loader.py

# Test complete pipeline
python process_reports.py "test_file.pdf" --no-archive
```

### Adding New Features
1. **New Analysis**: Add methods to `data_analyzer.py`
2. **New Pages**: Create templates and routes in `app.py`
3. **New Data Fields**: Update `database_models.py` and migration scripts

## 📝 License

Private repository - All rights reserved

## 🤝 Contributing

This is a private repository. Contact the repository owner for contribution guidelines.

## 📞 Support

For issues or questions, please contact the repository maintainer.

---

**Note**: This system is designed for medical compensation analysis and includes privacy protections for sensitive healthcare data.