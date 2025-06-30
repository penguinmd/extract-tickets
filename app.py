import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
from pathlib import Path
import traceback
import pandas as pd

from process_reports import ReportProcessor
from data_analyzer import CompensationAnalyzer
from database_models import get_session, MonthlySummary, ChargeTransaction, AnesthesiaCase

# Configuration
UPLOAD_FOLDER = 'data'
ALLOWED_EXTENSIONS = {'pdf'}

# Initialize Flask App
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'supersecretkey'  # Required for flashing messages

def allowed_file(filename):
    """Check if the file has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Main dashboard page - clean overview."""
    try:
        analyzer = CompensationAnalyzer()
        
        # Get basic summary statistics
        summary_stats = analyzer.get_summary_statistics()
        
        return render_template('dashboard.html', stats=summary_stats)
    except Exception as e:
        app.logger.error(f"Dashboard error: {str(e)}\n{traceback.format_exc()}")
        flash(f"Error loading dashboard: {str(e)}", 'danger')
        return render_template('dashboard.html', stats={})

@app.route('/compensation')
def compensation():
    """Compensation data page."""
    try:
        analyzer = CompensationAnalyzer()
        
        # Get monthly summary data
        summary_df = analyzer.get_monthly_income_trend()
        
        return render_template('compensation.html',
                             summary_data=summary_df.to_dict(orient='records') if not summary_df.empty else [])
    except Exception as e:
        app.logger.error(f"Compensation page error: {str(e)}\n{traceback.format_exc()}")
        flash(f"Error loading compensation data: {str(e)}", 'danger')
        return render_template('compensation.html', summary_data=[])

@app.route('/cases')
def cases():
    """Master cases page."""
    try:
        analyzer = CompensationAnalyzer()
        
        # Get sorting parameters from request
        sort_by = request.args.get('sort_by', 'date_of_service')
        sort_order = request.args.get('sort_order', 'desc')

        # Fetch and sort data
        cases_df = analyzer.get_master_cases(sort_by=sort_by, sort_order=sort_order)
        
        return render_template('cases.html', 
                             cases_data=cases_df.to_dict(orient='records') if not cases_df.empty else [],
                             sort_by=sort_by,
                             sort_order=sort_order)
    except Exception as e:
        app.logger.error(f"Cases page error: {str(e)}\n{traceback.format_exc()}")
        flash(f"Error loading master cases: {str(e)}", 'danger')
        return render_template('cases.html', cases_data=[], sort_by='date_of_service', sort_order='desc')

@app.route('/tickets')
def tickets():
    """Ticket/transaction data page with sorting."""
    try:
        analyzer = CompensationAnalyzer()
        
        # Get sorting parameters from request
        sort_by = request.args.get('sort_by', 'phys_ticket_ref')
        sort_order = request.args.get('sort_order', 'asc')

        # Fetch and sort data
        transactions_df = analyzer.get_charge_transactions(sort_by=sort_by, sort_order=sort_order)

        return render_template('tickets.html',
                             transactions_data=transactions_df.to_dict(orient='records') if not transactions_df.empty else [],
                             sort_by=sort_by,
                             sort_order=sort_order)
    except Exception as e:
        app.logger.error(f"Tickets page error: {str(e)}\n{traceback.format_exc()}")
        flash(f"Error loading ticket data: {str(e)}", 'danger')
        return render_template('tickets.html', transactions_data=[], sort_by='phys_ticket_ref', sort_order='asc')

@app.route('/analysis')
def analysis():
    """Analysis and charts page."""
    try:
        analyzer = CompensationAnalyzer()
        
        # Generate plots and save them
        reports_dir = Path('static/reports')
        reports_dir.mkdir(exist_ok=True)
        
        # Generate charts
        analyzer.plot_income_trend(save_path=str(reports_dir / 'income_trend.png'))
        analyzer.plot_seasonal_trends(save_path=str(reports_dir / 'seasonal_trends.png'))
        analyzer.plot_procedure_profitability(save_path=str(reports_dir / 'procedure_profitability.png'))
        analyzer.plot_payer_performance(save_path=str(reports_dir / 'payer_performance.png'))

        return render_template('analysis.html')
    except Exception as e:
        app.logger.error(f"Analysis page error: {str(e)}\n{traceback.format_exc()}")
        flash(f"Error generating analysis: {str(e)}", 'danger')
        return render_template('analysis.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file uploads."""
    if 'file' not in request.files:
        flash('No file part', 'warning')
        return redirect(url_for('index'))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No selected file', 'warning')
        return redirect(url_for('index'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        try:
            # Process the uploaded file
            processor = ReportProcessor(archive_processed=True)
            success = processor.process_single_file(file_path)
            
            if success:
                flash(f'File "{filename}" uploaded and processed successfully!', 'success')
            else:
                flash(f'Error processing file "{filename}". Check logs for details.', 'danger')
        except Exception as e:
            app.logger.error(f"Upload processing error: {str(e)}\n{traceback.format_exc()}")
            flash(f'Error processing file "{filename}": {str(e)}', 'danger')
            
        return redirect(url_for('index'))
    else:
        flash('Invalid file type. Please upload a PDF.', 'danger')
        return redirect(url_for('index'))

@app.route('/delete_report/<int:summary_id>', methods=['POST'])
def delete_report(summary_id):
    """Delete a report and all its associated data."""
    session = get_session()
    try:
        # Find the summary record
        summary = session.query(MonthlySummary).filter_by(id=summary_id).first()
        if not summary:
            flash('Report not found.', 'danger')
            return redirect(url_for('compensation'))

        # Delete associated records
        session.query(ChargeTransaction).filter_by(summary_id=summary_id).delete()
        session.query(AnesthesiaCase).filter_by(summary_id=summary_id).delete()
        
        # Delete the summary record
        session.delete(summary)
        
        session.commit()
        flash(f'Report "{summary.source_file}" and all its data have been deleted.', 'success')
    except Exception as e:
        session.rollback()
        app.logger.error(f"Error deleting report: {str(e)}\n{traceback.format_exc()}")
        flash(f'Error deleting report: {str(e)}', 'danger')
    finally:
        session.close()
        
    return redirect(url_for('compensation'))

@app.route('/health')
def health_check():
    """A simple health check endpoint."""
    return jsonify({"status": "ok"}), 200

@app.route('/delete', methods=['GET', 'POST'])
def delete_all_data():
    """Delete all data from the database."""
    if request.method == 'POST':
        session = get_session()
        try:
            session.query(ChargeTransaction).delete()
            session.query(AnesthesiaCase).delete()
            session.query(MonthlySummary).delete()
            session.commit()
            flash('All data has been deleted.', 'success')
        except Exception as e:
            session.rollback()
            app.logger.error(f"Error deleting all data: {str(e)}\n{traceback.format_exc()}")
            flash(f'Error deleting all data: {str(e)}', 'danger')
        finally:
            session.close()
        return redirect(url_for('delete_all_data'))
    return render_template('delete.html')

if __name__ == '__main__':
    # Ensure directories exist
    Path('static').mkdir(exist_ok=True)
    Path('static/reports').mkdir(exist_ok=True)
    Path('data').mkdir(exist_ok=True)
    
    app.run(debug=True, port=8888)