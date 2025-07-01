#!/usr/bin/env python3

import os
import glob
from process_reports import ReportProcessor
from data_loader import DataLoader
from case_grouper import CaseGrouper
from database_models import get_session, MasterCase
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def batch_process_files(file_paths, data_directory="data"):
    """
    Process multiple PDF files in batch.
    
    Args:
        file_paths: List of file paths to process
        data_directory: Directory to look for files if relative paths are provided
    """
    processor = ReportProcessor()
    loader = DataLoader()
    session = get_session()
    
    successful_files = []
    failed_files = []
    
    try:
        for file_path in file_paths:
            # Handle relative paths
            if not os.path.isabs(file_path):
                # If the file_path already contains the data directory, don't add it again
                if not file_path.startswith(data_directory):
                    file_path = os.path.join(data_directory, file_path)
            
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                failed_files.append((file_path, "File not found"))
                continue
            
            logger.info(f"Processing file: {file_path}")
            
            try:
                # Process the file (this handles extraction and loading)
                success = processor.process_single_file(file_path)
                
                if success:
                    logger.info(f"Successfully processed: {file_path}")
                    successful_files.append(file_path)
                else:
                    logger.error(f"Failed to process: {file_path}")
                    failed_files.append((file_path, "Processing failed"))
                    
            except Exception as e:
                logger.error(f"Error processing {file_path}: {str(e)}")
                failed_files.append((file_path, str(e)))
        
        # After all files are processed, regenerate master cases
        logger.info("Regenerating master cases from all transactions...")
        grouper = CaseGrouper(session)
        
        # Clear existing master cases
        session.query(MasterCase).delete(synchronize_session=False)
        session.commit()
        
        # Regenerate from all transactions
        grouper.group_transactions_into_cases()
        
        # Get final statistics
        stats = grouper.get_case_statistics()
        logger.info(f"Batch processing completed:")
        logger.info(f"  Successful files: {len(successful_files)}")
        logger.info(f"  Failed files: {len(failed_files)}")
        logger.info(f"  Total cases: {stats['total_cases']}")
        logger.info(f"  Total transactions: {stats['total_transactions']}")
        
        return successful_files, failed_files, stats
        
    except Exception as e:
        logger.error(f"Batch processing error: {str(e)}")
        return successful_files, failed_files, None
    finally:
        session.close()

def process_all_pdfs_in_directory(directory="data", pattern="*.pdf"):
    """
    Process all PDF files in a directory.
    
    Args:
        directory: Directory to scan for PDF files
        pattern: File pattern to match (default: "*.pdf")
    """
    pdf_files = glob.glob(os.path.join(directory, pattern))
    
    if not pdf_files:
        logger.warning(f"No PDF files found in {directory}")
        return [], [], None
    
    logger.info(f"Found {len(pdf_files)} PDF files to process")
    return batch_process_files(pdf_files, directory)

def main():
    """Main function for command line usage."""
    import sys
    
    if len(sys.argv) > 1:
        # Process specific files provided as command line arguments
        file_paths = sys.argv[1:]
        successful, failed, stats = batch_process_files(file_paths)
    else:
        # Process all PDF files in the data directory
        successful, failed, stats = process_all_pdfs_in_directory()
    
    # Print summary
    print("\n" + "="*50)
    print("BATCH PROCESSING SUMMARY")
    print("="*50)
    
    if successful:
        print(f"\n✅ Successfully processed ({len(successful)} files):")
        for file_path in successful:
            print(f"  - {os.path.basename(file_path)}")
    
    if failed:
        print(f"\n❌ Failed to process ({len(failed)} files):")
        for file_path, error in failed:
            print(f"  - {os.path.basename(file_path)}: {error}")
    
    if stats:
        print(f"\n📊 Final Statistics:")
        print(f"  Total Cases: {stats['total_cases']}")
        print(f"  Total Transactions: {stats['total_transactions']}")
        print(f"  Linked Transactions: {stats['linked_transactions']}")
        print(f"  Unlinked Transactions: {stats['unlinked_transactions']}")

if __name__ == "__main__":
    main() 