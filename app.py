import os
import secrets
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
# Use environment variable for secret key, or generate a random one
app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(32)

# Custom template filter for month names
@app.template_filter('month_name')
def month_name(month_number):
    """Convert month number to month name."""
    import calendar
    return calendar.month_name[month_number]

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
        try:
            analyzer.plot_income_trend(save_path=str(reports_dir / 'income_trend.png'))
            analyzer.plot_seasonal_trends(save_path=str(reports_dir / 'seasonal_trends.png'))
            analyzer.plot_procedure_profitability(save_path=str(reports_dir / 'procedure_profitability.png'))
            analyzer.plot_payer_performance(save_path=str(reports_dir / 'payer_performance.png'))
        except Exception as chart_error:
            app.logger.warning(f"Error generating charts: {str(chart_error)}")

        # Get master case analysis
        master_case_analysis = analyzer.get_master_case_analysis()
        
        # Debug output
        app.logger.info(f"Master case analysis result: {master_case_analysis}")
        app.logger.info(f"Type of master_case_analysis: {type(master_case_analysis)}")
        if master_case_analysis:
            app.logger.info(f"Total cases: {master_case_analysis.get('total_cases', 'N/A')}")
            app.logger.info(f"Keys in master_case_analysis: {list(master_case_analysis.keys()) if isinstance(master_case_analysis, dict) else 'Not a dict'}")
        else:
            app.logger.warning("master_case_analysis is None or empty")

        return render_template('analysis.html', mca=master_case_analysis)
    except Exception as e:
        app.logger.error(f"Analysis page error: {str(e)}\n{traceback.format_exc()}")
        flash(f"Error generating analysis: {str(e)}", 'danger')
        return render_template('analysis.html', mca={})

def regenerate_master_cases():
    """Clear and rebuild master cases from all transactions."""
    from case_grouper import CaseGrouper
    from database_models import get_session, MasterCase
    session = get_session()
    try:
        grouper = CaseGrouper(session)
        session.query(MasterCase).delete(synchronize_session=False)
        session.commit()
        grouper.group_transactions_into_cases()
        stats = grouper.get_case_statistics()
        return stats
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error regenerating master cases: {str(e)}")
        return None
    finally:
        session.close()

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
                # Automatically regenerate master cases
                stats = regenerate_master_cases()
                flash(f'File "{filename}" uploaded and processed successfully! Master cases regenerated ({stats["total_cases"]} cases).', 'success')
            else:
                flash(f'Error processing file "{filename}". Check logs for details.', 'danger')
        except Exception as e:
            app.logger.error(f"Upload processing error: {str(e)}\n{traceback.format_exc()}")
            flash(f'Error processing file "{filename}": {str(e)}', 'danger')
            
        return redirect(url_for('index'))
    else:
        flash('Invalid file type. Please upload a PDF.', 'danger')
        return redirect(url_for('index'))

@app.route('/batch_upload', methods=['POST'])
def batch_upload():
    """Handle batch file upload and processing."""
    if 'files' not in request.files:
        flash('No files selected', 'warning')
        return redirect(url_for('index'))
    
    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        flash('No files selected', 'warning')
        return redirect(url_for('index'))
    
    successful_files = []
    failed_files = []
    
    try:
        for file in files:
            if file and allowed_file(file.filename):
                try:
                    # Save file temporarily
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    
                    # Process the file
                    processor = ReportProcessor(archive_processed=True)
                    success = processor.process_single_file(filepath)
                    
                    if success:
                        successful_files.append(filename)
                    else:
                        failed_files.append(filename)
                        
                except Exception as e:
                    app.logger.error(f"Batch upload error for {file.filename}: {str(e)}")
                    failed_files.append(file.filename)
            else:
                failed_files.append(file.filename)
        
        # Automatically regenerate master cases after batch upload
        stats = regenerate_master_cases()
        flash(f'Batch processing completed: {len(successful_files)} successful, {len(failed_files)} failed. Master cases regenerated ({stats["total_cases"]} cases).', 'success')
        if successful_files:
            flash(f'Successfully processed: {", ".join(successful_files)}', 'success')
        if failed_files:
            flash(f'Failed to process: {", ".join(failed_files)}', 'danger')
            
    except Exception as e:
        app.logger.error(f"Batch upload error: {str(e)}")
        flash(f'Error during batch processing: {str(e)}', 'danger')

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

@app.route('/debug_analysis')
def debug_analysis():
    """Debug endpoint to test analysis data."""
    try:
        analyzer = CompensationAnalyzer()
        master_case_analysis = analyzer.get_master_case_analysis()
        
        return jsonify({
            'type': str(type(master_case_analysis)),
            'is_none': master_case_analysis is None,
            'is_empty': len(master_case_analysis) == 0 if master_case_analysis else True,
            'keys': list(master_case_analysis.keys()) if master_case_analysis else [],
            'total_cases': master_case_analysis.get('total_cases', 'N/A') if master_case_analysis else 'N/A',
            'sample_data': master_case_analysis
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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

@app.route('/cpt_codes')
def cpt_codes():
    """CPT codes page with anesthesia base units and historical tracking."""
    try:
        analyzer = CompensationAnalyzer()
        
        # Get CPT codes analysis with historical tracking
        cpt_data = analyzer.get_cpt_codes_with_history()
        
        return render_template('cpt_codes.html', cpt_data=cpt_data)
    except Exception as e:
        app.logger.error(f"CPT codes page error: {str(e)}\n{traceback.format_exc()}")
        flash(f"Error loading CPT codes data: {str(e)}", 'danger')
        return render_template('cpt_codes.html', cpt_data={})

@app.route('/cpt_codes/export')
def export_cpt_codes():
    """Export CPT codes data as CSV."""
    try:
        analyzer = CompensationAnalyzer()
        cpt_data = analyzer.get_cpt_codes_with_history()
        
        # Create CSV data
        csv_data = []
        csv_data.append(['CPT Code', 'Current Anesthesia Base Units'])
        
        for cpt_code, data in cpt_data.items():
            current_units = data.get('current_anes_units', 'N/A')
            
            csv_data.append([
                cpt_code,
                current_units
            ])
        
        # Create CSV response
        import io
        import csv
        from flask import Response
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerows(csv_data)
        
        output.seek(0)
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=cpt_codes_analysis.csv'}
        )
        
    except Exception as e:
        app.logger.error(f"CPT codes export error: {str(e)}\n{traceback.format_exc()}")
        flash(f"Error exporting CPT codes: {str(e)}", 'danger')
        return redirect(url_for('cpt_codes'))

@app.route('/asmg_rules')
def asmg_rules():
    """ASMG temporal rules management page."""
    try:
        from asmg_calculator import ASMGCalculator
        
        calculator = ASMGCalculator()
        rules = calculator.get_all_rules()
        
        return render_template('asmg_rules.html', rules=rules)
    except Exception as e:
        app.logger.error(f"ASMG rules page error: {str(e)}\n{traceback.format_exc()}")
        flash(f"Error loading ASMG rules: {str(e)}", 'danger')
        return render_template('asmg_rules.html', rules=[])

@app.route('/asmg_rules/add', methods=['POST'])
def add_asmg_rule():
    """Add or update an ASMG temporal rule."""
    try:
        from asmg_calculator import ASMGCalculator
        from datetime import datetime
        
        # Get form data
        effective_date = datetime.strptime(request.form['effective_date'], '%Y-%m-%d').date()
        anes_units_multiplier = float(request.form['anes_units_multiplier'])
        anes_time_divisor = float(request.form['anes_time_divisor'])
        med_units_multiplier = float(request.form['med_units_multiplier'])
        description = request.form.get('description', '')
        
        calculator = ASMGCalculator()
        success = calculator.add_rule(
            effective_date=effective_date,
            anes_units_multiplier=anes_units_multiplier,
            anes_time_divisor=anes_time_divisor,
            med_units_multiplier=med_units_multiplier,
            description=description
        )
        
        if success:
            flash('ASMG rule added/updated successfully!', 'success')
        else:
            flash('Error adding ASMG rule. Please try again.', 'danger')
            
    except Exception as e:
        app.logger.error(f"Error adding ASMG rule: {str(e)}\n{traceback.format_exc()}")
        flash(f'Error adding ASMG rule: {str(e)}', 'danger')
    
    return redirect(url_for('asmg_rules'))

@app.route('/asmg_rules/delete/<int:rule_id>', methods=['POST'])
def delete_asmg_rule(rule_id):
    """Delete an ASMG temporal rule."""
    try:
        from asmg_calculator import ASMGCalculator
        
        calculator = ASMGCalculator()
        success = calculator.delete_rule(rule_id)
        
        if success:
            flash('ASMG rule deleted successfully!', 'success')
        else:
            flash('Error deleting ASMG rule. Please try again.', 'danger')
            
    except Exception as e:
        app.logger.error(f"Error deleting ASMG rule: {str(e)}\n{traceback.format_exc()}")
        flash(f'Error deleting ASMG rule: {str(e)}', 'danger')
    
    return redirect(url_for('asmg_rules'))

if __name__ == '__main__':
    # Ensure directories exist
    Path('static').mkdir(exist_ok=True)
    Path('static/reports').mkdir(exist_ok=True)
    Path('data').mkdir(exist_ok=True)
    
    app.run(debug=True, port=8888)