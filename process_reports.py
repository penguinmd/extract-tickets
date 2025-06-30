"""
Main script for processing medical compensation reports.
Implements batch processing for historical data and single file processing.
"""

import os
import logging
import argparse
from pathlib import Path
from datetime import datetime
from data_extractor import MedicalReportExtractor
from data_loader import DataLoader
from database_models import create_database

# Set up logging
def setup_logging(log_file='processing.log'):
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

logger = logging.getLogger(__name__)

class ReportProcessor:
    """Main class for processing compensation reports."""
    
    def __init__(self, archive_processed=True):
        self.extractor = MedicalReportExtractor()
        self.loader = DataLoader()
        self.archive_processed = archive_processed
        self.stats = {
            'total_files': 0,
            'processed_successfully': 0,
            'failed_files': [],
            'skipped_files': []
        }
    
    def process_single_file(self, file_path: str) -> bool:
        """
        Process a single PDF report file, with checks for duplicates.
        
        Args:
            file_path (str): Path to the PDF file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            file_name = os.path.basename(file_path)
            
            # Skip if already processed
            if self._is_already_processed(file_name):
                logger.info(f"Skipping already processed file: {file_name}")
                self.stats['skipped_files'].append(file_name)
                return True # Return True to not count as a failure

            logger.info(f"Processing file: {file_path}")
            
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return False
            
            summary_data, charge_transactions, ticket_tracking = self.extractor.extract_data_from_report(file_path)
            
            success = self.loader.load_report_data(summary_data, charge_transactions, ticket_tracking)
            
            if success:
                logger.info(f"Successfully processed: {file_path}")
                if self.archive_processed:
                    self._archive_file(file_path)
                return True
            else:
                logger.error(f"Failed to load data for: {file_path}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing {file_path}: {str(e)}")
            return False
    
    def process_directory(self, directory_path: str) -> dict:
        """
        Process all PDF files in a directory.
        
        Args:
            directory_path (str): Path to directory containing PDF files
            
        Returns:
            dict: Processing statistics
        """
        try:
            directory = Path(directory_path)
            if not directory.exists():
                logger.error(f"Directory not found: {directory_path}")
                return self.stats
            
            # Find all PDF files
            pdf_files = list(directory.glob("*.pdf"))
            self.stats['total_files'] = len(pdf_files)
            
            logger.info(f"Found {len(pdf_files)} PDF files in {directory_path}")
            
            if not pdf_files:
                logger.warning("No PDF files found in directory")
                return self.stats
            
            # Process each file
            for pdf_file in pdf_files:
                try:
                    success = self.process_single_file(str(pdf_file))
                    
                    if success:
                        self.stats['processed_successfully'] += 1
                    else:
                        self.stats['failed_files'].append(str(pdf_file))
                        
                except Exception as e:
                    logger.error(f"Unexpected error processing {pdf_file}: {str(e)}")
                    self.stats['failed_files'].append(str(pdf_file))
            
            # Log final statistics
            self._log_processing_stats()
            
            return self.stats
            
        except Exception as e:
            logger.error(f"Error processing directory {directory_path}: {str(e)}")
            return self.stats
    
    def _archive_file(self, file_path: str):
        """Move processed file to archive subdirectory."""
        try:
            file_path = Path(file_path)
            archive_dir = file_path.parent / "archive"
            
            # Create archive directory if it doesn't exist
            archive_dir.mkdir(exist_ok=True)
            
            # Move file to archive
            archive_path = archive_dir / file_path.name
            
            # If file already exists in archive, add timestamp
            if archive_path.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                name_parts = file_path.stem, timestamp, file_path.suffix
                archive_path = archive_dir / f"{name_parts[0]}_{name_parts[1]}{name_parts[2]}"
            
            file_path.rename(archive_path)
            logger.info(f"Archived file to: {archive_path}")
            
        except Exception as e:
            logger.warning(f"Could not archive file {file_path}: {str(e)}")
    
    def _is_already_processed(self, filename: str) -> bool:
        """Check if a file has already been processed by checking the database."""
        from database_models import get_session, MonthlySummary
        session = get_session()
        try:
            return session.query(MonthlySummary).filter_by(source_file=filename).count() > 0
        finally:
            session.close()

    def _log_processing_stats(self):
        """Log processing statistics."""
        logger.info("=== PROCESSING STATISTICS ===")
        logger.info(f"Total files found: {self.stats['total_files']}")
        logger.info(f"Successfully processed: {self.stats['processed_successfully']}")
        logger.info(f"Failed files: {len(self.stats['failed_files'])}")
        logger.info(f"Skipped files: {len(self.stats['skipped_files'])}")
        
        if self.stats['failed_files']:
            logger.warning("Failed files:")
            for failed_file in self.stats['failed_files']:
                logger.warning(f"  - {failed_file}")
        
        if self.stats['skipped_files']:
            logger.info("Skipped files:")
            for skipped_file in self.stats['skipped_files']:
                logger.info(f"  - {skipped_file}")

def process_pdf_files(file_paths):
    """
    Convenience function to process a list of PDF files.
    
    Args:
        file_paths: List of paths to PDF files
        
    Returns:
        dict: Processing statistics
    """
    processor = ReportProcessor(archive_processed=False)
    stats = {
        'total_files': 0,
        'processed_successfully': 0,
        'failed_files': []
    }
    
    for file_path in file_paths:
        stats['total_files'] += 1
        try:
            success = processor.process_single_file(file_path)
            if success:
                stats['processed_successfully'] += 1
            else:
                stats['failed_files'].append(file_path)
        except Exception as e:
            logger.error(f"Error processing {file_path}: {str(e)}")
            stats['failed_files'].append(file_path)
    
    return stats

def process_single_report(file_path):
    """
    Convenience function to process a single PDF file.
    
    Args:
        file_path: Path to PDF file
        
    Returns:
        bool: True if successful, False otherwise
    """
    processor = ReportProcessor(archive_processed=False)
    return processor.process_single_file(file_path)

def main():
    """Main function with command line interface."""
    parser = argparse.ArgumentParser(description='Process medical compensation reports')
    parser.add_argument('path', help='Path to PDF file or directory containing PDF files')
    parser.add_argument('--no-archive', action='store_true',
                       help='Do not archive processed files')
    parser.add_argument('--log-file', default='processing.log',
                       help='Log file path (default: processing.log)')
    parser.add_argument('--create-db', action='store_true',
                       help='Create database tables before processing')
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.log_file)
    
    # Create database if requested
    if args.create_db:
        logger.info("Creating database tables...")
        create_database()
    
    # Initialize processor
    processor = ReportProcessor(archive_processed=not args.no_archive)
    
    # Determine if path is file or directory
    path = Path(args.path)
    
    if path.is_file():
        # Process single file
        logger.info(f"Processing single file: {path}")
        success = processor.process_single_file(str(path))
        
        if success:
            logger.info("File processed successfully")
        else:
            logger.error("File processing failed")
            exit(1)
            
    elif path.is_dir():
        # Process directory
        logger.info(f"Processing directory: {path}")
        stats = processor.process_directory(str(path))
        
        if stats['processed_successfully'] == 0:
            logger.error("No files were processed successfully")
            exit(1)
        else:
            logger.info(f"Processing complete. {stats['processed_successfully']} files processed successfully.")
    
    else:
        logger.error(f"Path not found: {path}")
        exit(1)

if __name__ == "__main__":
    main()