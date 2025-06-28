import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
from pathlib import Path
import traceback

from process_reports import ReportProcessor
from data_analyzer import CompensationAnalyzer

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

@app.route('/tickets')
def tickets():
    """Ticket/transaction data page."""
    try:
        analyzer = CompensationAnalyzer()
        
        # Get charge transactions
        transactions_df = analyzer.get_charge_transactions()
        
        return render_template('tickets.html',
                             transactions_data=transactions_df.to_dict(orient='records') if not transactions_df.empty else [])
    except Exception as e:
        app.logger.error(f"Tickets page error: {str(e)}\n{traceback.format_exc()}")
        flash(f"Error loading ticket data: {str(e)}", 'danger')
        return render_template('tickets.html', transactions_data=[])

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

if __name__ == '__main__':
    # Ensure directories exist
    Path('static').mkdir(exist_ok=True)
    Path('static/reports').mkdir(exist_ok=True)
    Path('data').mkdir(exist_ok=True)
    
    app.run(debug=True, port=5003)