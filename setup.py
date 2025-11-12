"""
Setup script for the Medical Compensation Analysis Pipeline.
Run this script to initialize the project.
"""

import os
import sys
from pathlib import Path
from database_models import create_database

def setup_project():
    """Initialize the project structure and database."""
    print("Setting up Medical Compensation Analysis Pipeline...")
    print("=" * 50)
    
    # Create necessary directories
    directories = ['data', 'archive', 'reports', 'logs']
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✓ Created directory: {directory}")
    
    # Create database
    print("\nCreating database...")
    try:
        create_database()
        print("✓ Database created successfully")
    except Exception as e:
        print(f"✗ Error creating database: {e}")
        return False
    
    # Create sample configuration
    config_content = """# Medical Compensation Analysis Pipeline Configuration

## Directory Structure
- data/: Place your PDF reports here for processing
- archive/: Processed files are moved here automatically
- reports/: Generated analysis reports and visualizations
- logs/: Processing and error logs

## Usage Examples

### Process a single file:
python process_reports.py data/your_report.pdf

### Process all files in data directory:
python process_reports.py data/

### Generate analysis:
python data_analyzer.py

### Test extraction on sample file:
python data_extractor.py
"""
    
    with open('CONFIG.md', 'w') as f:
        f.write(config_content)
    print("✓ Created configuration file: CONFIG.md")
    
    print("\n" + "=" * 50)
    print("Setup complete!")
    print("\nNext steps:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Place your PDF reports in the 'data/' directory")
    print("3. Run: python process_reports.py data/")
    print("4. Generate analysis: python data_analyzer.py")
    
    return True

if __name__ == "__main__":
    setup_project()