#!/usr/bin/env python3
"""
Setup script for Medical Compensation Analysis System.
Handles installation, directory creation, and database initialization.
"""

import os
import sys
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def create_directories():
    """Create necessary directories for the application."""
    directories = [
        'data',
        'data/archive',
        'logs',
        'static',
        'static/reports',
    ]

    logger.info("Creating application directories...")
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logger.info(f"  ✓ {directory}")


def initialize_database():
    """Initialize the database with proper schema."""
    logger.info("Initializing database...")
    try:
        from database_models import create_database
        create_database()
        logger.info("  ✓ Database initialized")
    except Exception as e:
        logger.error(f"  ✗ Database initialization failed: {str(e)}")
        return False
    return True


def initialize_asmg_rules():
    """Initialize default ASMG calculation rules."""
    logger.info("Initializing ASMG rules...")
    try:
        from asmg_calculator import ASMGCalculator
        calculator = ASMGCalculator()
        calculator.initialize_default_rules()
        logger.info("  ✓ ASMG rules initialized")
    except Exception as e:
        logger.error(f"  ✗ ASMG rules initialization failed: {str(e)}")
        return False
    return True


def check_dependencies():
    """Check if all required dependencies are installed."""
    logger.info("Checking dependencies...")

    required_packages = [
        'flask',
        'pandas',
        'pdfplumber',
        'matplotlib',
        'seaborn',
        'sqlalchemy',
        'werkzeug',
    ]

    missing_packages = []

    for package in required_packages:
        try:
            __import__(package.lower().replace('-', '_'))
            logger.info(f"  ✓ {package}")
        except ImportError:
            missing_packages.append(package)
            logger.error(f"  ✗ {package} (missing)")

    if missing_packages:
        logger.error("\nMissing dependencies detected!")
        logger.error("Please install them using:")
        logger.error(f"  pip install {' '.join(missing_packages)}")
        logger.error("\nOr install all dependencies at once:")
        logger.error("  pip install -r requirements.txt")
        return False

    logger.info("All dependencies are installed!")
    return True


def create_env_template():
    """Create a template .env file if it doesn't exist."""
    env_file = Path('.env')

    if env_file.exists():
        logger.info("Environment file already exists")
        return

    logger.info("Creating .env template...")
    env_content = """# Flask Configuration
SECRET_KEY=your-secret-key-here

# Database Configuration (optional, defaults to SQLite)
# DATABASE_URL=sqlite:///compensation.db

# Upload Configuration
UPLOAD_FOLDER=data

# Flask Debug Mode (set to False in production)
FLASK_DEBUG=True

# Server Configuration
FLASK_HOST=0.0.0.0
FLASK_PORT=8888
"""

    with open(env_file, 'w') as f:
        f.write(env_content)

    logger.info("  ✓ .env template created")
    logger.info("  Please update .env with your actual configuration")


def main():
    """Main setup function."""
    print("=" * 70)
    print("MEDICAL COMPENSATION ANALYSIS SYSTEM - SETUP")
    print("=" * 70)
    print()

    # Step 1: Check dependencies
    if not check_dependencies():
        sys.exit(1)

    print()

    # Step 2: Create directories
    create_directories()

    print()

    # Step 3: Create environment file template
    create_env_template()

    print()

    # Step 4: Initialize database
    if not initialize_database():
        logger.warning("Database initialization failed - you may need to run this manually")

    print()

    # Step 5: Initialize ASMG rules
    if not initialize_asmg_rules():
        logger.warning("ASMG rules initialization failed - you may need to run this manually")

    print()
    print("=" * 70)
    print("SETUP COMPLETE!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  1. Review and update .env file with your configuration")
    print("  2. Place PDF compensation reports in the 'data/' directory")
    print("  3. Start the application:")
    print("       python app.py")
    print("  4. Access the web interface at:")
    print("       http://localhost:8888")
    print()
    print("For command-line processing:")
    print("  python process_reports.py data/your-report.pdf")
    print()
    print("For batch processing:")
    print("  python process_reports.py data/")
    print()


if __name__ == "__main__":
    main()
