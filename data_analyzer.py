"""
Data analysis module for medical compensation reports.
Provides insights and visualizations based on the stored data.
"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import text
from datetime import datetime, timedelta
import logging
from database_models import engine, get_session, MasterCase
from asmg_calculator import ASMGCalculator
import sqlalchemy

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set style for plots
plt.style.use('default')
sns.set_palette("husl")

class CompensationAnalyzer:
    """Class for analyzing compensation and practice data."""
    
    def __init__(self):
        self.engine = engine
        self.session = get_session()
    
    def __del__(self):
        """Close session when object is destroyed."""
        if hasattr(self, 'session') and self.session:
            self.session.close()
    
    def get_summary_statistics(self) -> dict:
        """Get basic summary statistics for the dashboard."""
        try:
            stats = {}
            
            # Total reports processed
            query = "SELECT COUNT(*) as total_reports FROM monthly_summary"
            result = pd.read_sql(query, self.engine)
            stats['total_reports'] = result['total_reports'].iloc[0] if not result.empty else 0
            
            # Total transactions
            try:
                query = "SELECT COUNT(*) as total_transactions FROM charge_transactions"
                result = pd.read_sql(query, self.engine)
                stats['total_transactions'] = result['total_transactions'].iloc[0] if not result.empty else 0
            except:
                stats['total_transactions'] = 0
            
            # Latest gross pay
            query = """
            SELECT gross_pay, pay_period_end_date
            FROM monthly_summary
            ORDER BY pay_period_end_date DESC
            LIMIT 1
            """
            result = pd.read_sql(query, self.engine)
            if not result.empty:
                stats['latest_gross_pay'] = result['gross_pay'].iloc[0] or 0
                stats['latest_period'] = result['pay_period_end_date'].iloc[0]
            else:
                stats['latest_gross_pay'] = 0
                stats['latest_period'] = None
            
            # Total billed amount
            try:
                query = "SELECT SUM(billed_amount) as total_billed FROM charge_transactions"
                result = pd.read_sql(query, self.engine)
                stats['total_billed'] = result['total_billed'].iloc[0] if not result.empty and result['total_billed'].iloc[0] else 0
            except:
                stats['total_billed'] = 0
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting summary statistics: {str(e)}")
            return {
                'total_reports': 0,
                'total_transactions': 0,
                'latest_gross_pay': 0,
                'latest_period': None,
                'total_billed': 0
            }
    
    def get_monthly_income_trend(self, months=36) -> pd.DataFrame:
        """
        Get monthly income trend over specified number of months.
        
        Args:
            months (int): Number of months to analyze (default: 36)
            
        Returns:
            DataFrame: Monthly income data
        """
        query = """
        SELECT 
            pay_period_end_date,
            gross_pay,
            total_commission,
            base_salary,
            bonus_amount
        FROM monthly_summary 
        WHERE pay_period_end_date >= date('now', '-{} months')
        ORDER BY pay_period_end_date
        """.format(months)
        
        df = pd.read_sql_query(query, self.engine)
        numeric_cols = ['gross_pay', 'total_commission', 'base_salary', 'bonus_amount']
        df[numeric_cols] = df[numeric_cols].fillna(0)
        df['pay_period_end_date'] = pd.to_datetime(df['pay_period_end_date'])
        
        return df
    
    def get_procedure_profitability(self) -> pd.DataFrame:
        """
        Analyze profitability by CPT code.
        
        Returns:
            DataFrame: CPT code analysis
        """
        query = """
        SELECT 
            cpt_code,
            COUNT(*) as frequency,
            AVG(CAST(anes_time_min AS REAL)) as avg_time,
            AVG(CAST(anes_base_units AS REAL)) as avg_anes_units,
            AVG(CAST(med_base_units AS REAL)) as avg_med_units,
            SUM(CAST(anes_time_min AS REAL)) as total_time,
            SUM(CAST(anes_base_units AS REAL)) as total_anes_units,
            SUM(CAST(med_base_units AS REAL)) as total_med_units
        FROM charge_transactions 
        WHERE cpt_code IS NOT NULL AND cpt_code != ''
        GROUP BY cpt_code
        HAVING frequency >= 2  -- Only include codes with at least 2 occurrences
        ORDER BY frequency DESC
        """
        
        df = pd.read_sql_query(query, self.engine)
        numeric_cols = ['frequency', 'avg_time', 'avg_anes_units', 'avg_med_units', 'total_time', 'total_anes_units', 'total_med_units']
        df[numeric_cols] = df[numeric_cols].fillna(0)
        return df
    
    def get_payer_performance(self) -> pd.DataFrame:
        """
        Analyze performance by insurance carrier.
        
        Returns:
            DataFrame: Insurance carrier analysis
        """
        query = """
        SELECT 
            pay_code as insurance_carrier,
            COUNT(*) as claim_count,
            AVG(CAST(anes_time_min AS REAL)) as avg_time,
            AVG(CAST(anes_base_units AS REAL)) as avg_anes_units,
            AVG(CAST(med_base_units AS REAL)) as avg_med_units,
            SUM(CAST(anes_time_min AS REAL)) as total_time,
            SUM(CAST(anes_base_units AS REAL)) as total_anes_units,
            SUM(CAST(med_base_units AS REAL)) as total_med_units
        FROM charge_transactions 
        WHERE pay_code IS NOT NULL AND pay_code != ''
        GROUP BY pay_code
        HAVING claim_count >= 5  -- Only include carriers with at least 5 claims
        ORDER BY total_anes_units DESC
        """
        
        df = pd.read_sql_query(query, self.engine)
        numeric_cols = ['claim_count', 'avg_time', 'avg_anes_units', 'avg_med_units', 'total_time', 'total_anes_units', 'total_med_units']
        df[numeric_cols] = df[numeric_cols].fillna(0)
        return df

    def get_charge_transactions(self, sort_by='phys_ticket_ref', sort_order='asc') -> pd.DataFrame:
        """
        Fetch all charge transactions with sorting.
        
        Args:
            sort_by (str): Column to sort by.
            sort_order (str): 'asc' or 'desc'.

        Returns:
            DataFrame: All charge transactions.
        """
        try:
            # Validate sort_by to prevent SQL injection
            from database_models import ChargeTransaction
            allowed_columns = [c.name for c in ChargeTransaction.__table__.columns]
            if sort_by not in allowed_columns:
                sort_by = 'phys_ticket_ref'

            # Validate sort_order
            if sort_order.lower() not in ['asc', 'desc']:
                sort_order = 'asc'

            query = f"SELECT * FROM charge_transactions ORDER BY {sort_by} {sort_order.upper()}"
            df = pd.read_sql_query(query, self.engine)
            
            if not df.empty:
                possible_numeric_cols = ['billed_amount', 'paid_amount', 'time_min', 'anes_base_units', 'med_base_units', 'other_units', 'chg_amt']
                existing_numeric_cols = [col for col in possible_numeric_cols if col in df.columns]
                
                if existing_numeric_cols:
                    df[existing_numeric_cols] = df[existing_numeric_cols].fillna(0)
            
            return df
        except Exception as e:
            logger.error(f"Error getting charge transactions: {str(e)}")
            return pd.DataFrame()

    def get_master_cases(self, sort_by='date_of_service', sort_order='desc') -> pd.DataFrame:
        """
        Retrieves all master cases from the database with sorting.
        
        Args:
            sort_by (str): Field to sort by (default: date_of_service)
            sort_order (str): Sort order ('asc' or 'desc', default: 'desc')
            
        Returns:
            DataFrame: Master cases data with stored ASMG units
        """
        try:
            from database_models import MasterCase
            
            # Build query with sorting
            query = self.session.query(MasterCase)
            
            # Add sorting - now asmg_units is a database column so it can be sorted at DB level
            if hasattr(MasterCase, sort_by):
                sort_column = getattr(MasterCase, sort_by)
                if sort_order.lower() == 'desc':
                    query = query.order_by(sort_column.desc())
                else:
                    query = query.order_by(sort_column.asc())
            else:
                # Default sorting by date descending
                query = query.order_by(MasterCase.date_of_service.desc())
            
            # Convert to DataFrame
            df = pd.read_sql(query.statement, self.session.bind)
            
            # Convert date columns
            if 'date_of_service' in df.columns:
                df['date_of_service'] = pd.to_datetime(df['date_of_service'])
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting master cases: {str(e)}")
            return pd.DataFrame()
    
    def get_seasonal_trends(self) -> pd.DataFrame:
        """
        Analyze seasonal trends in income and case volume.
        
        Returns:
            DataFrame: Seasonal analysis
        """
        query = """
        SELECT 
            CAST(strftime('%m', pay_period_end_date) AS INTEGER) as month,
            AVG(gross_pay) as avg_monthly_income,
            AVG(total_commission) as avg_commission,
            COUNT(*) as report_count
        FROM monthly_summary
        GROUP BY month
        ORDER BY month
        """
        
        df = pd.read_sql_query(query, self.engine)
        
        numeric_cols = ['avg_monthly_income', 'avg_commission', 'report_count']
        df[numeric_cols] = df[numeric_cols].fillna(0)

        # Add month names
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        df['month_name'] = df['month'].apply(lambda x: month_names[x-1])
        
        return df
    
    def get_commission_correlation(self) -> pd.DataFrame:
        """
        Analyze correlation between billed amounts and commission.
        
        Returns:
            DataFrame: Correlation analysis data
        """
        query = """
        SELECT 
            s.total_commission,
            s.gross_pay,
            s.pay_period_end_date,
            COALESCE(SUM(t.billed_amount), 0) as total_billed,
            COALESCE(SUM(t.paid_amount), 0) as total_paid,
            COALESCE(COUNT(t.id), 0) as transaction_count
        FROM monthly_summary s
        LEFT JOIN charge_transactions t ON s.id = t.summary_id
        GROUP BY s.id, s.total_commission, s.gross_pay, s.pay_period_end_date
        ORDER BY s.pay_period_end_date
        """
        
        df = pd.read_sql_query(query, self.engine)
        numeric_cols = ['total_commission', 'gross_pay', 'total_billed', 'total_paid', 'transaction_count']
        df[numeric_cols] = df[numeric_cols].fillna(0)
        df['pay_period_end_date'] = pd.to_datetime(df['pay_period_end_date'])
        
        return df
    
    def plot_income_trend(self, save_path=None):
        """Plot monthly income trend."""
        df = self.get_monthly_income_trend()
        
        # ADD THIS FIX:
        numeric_cols = ['gross_pay', 'total_commission', 'base_salary', 'bonus_amount']
        df[numeric_cols] = df[numeric_cols].fillna(0)
        
        if df.empty:
            logger.warning("No data available for income trend analysis")
            return
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        ax.plot(df['pay_period_end_date'], df['gross_pay'], 
               marker='o', linewidth=2, label='Gross Pay')
        ax.plot(df['pay_period_end_date'], df['total_commission'], 
               marker='s', linewidth=2, label='Total Commission')
        
        ax.set_title('Monthly Income Trend', fontsize=16, fontweight='bold')
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Amount ($)', fontsize=12)
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # Format y-axis as currency
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Income trend plot saved to: {save_path}")
        
        plt.close(fig)
    
    def plot_procedure_profitability(self, top_n=15, save_path=None):
        """Plot top procedures by frequency and profitability."""
        df = self.get_procedure_profitability()
        
        numeric_cols = ['frequency', 'avg_time', 'avg_anes_units', 'avg_med_units', 'total_time', 'total_anes_units', 'total_med_units']
        df[numeric_cols] = df[numeric_cols].fillna(0)
        
        if df.empty:
            logger.warning("No data available for procedure profitability analysis")
            return
        
        # Get top N procedures by frequency
        top_procedures = df.head(top_n)
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        
        # Plot 1: Frequency
        bars1 = ax1.bar(range(len(top_procedures)), top_procedures['frequency'])
        ax1.set_title(f'Top {top_n} Procedures by Frequency', fontsize=14, fontweight='bold')
        ax1.set_xlabel('CPT Code', fontsize=12)
        ax1.set_ylabel('Frequency', fontsize=12)
        ax1.set_xticks(range(len(top_procedures)))
        ax1.set_xticklabels(top_procedures['cpt_code'], rotation=45)
        
        # Add value labels on bars
        for i, bar in enumerate(bars1):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}', ha='center', va='bottom')
        
        # Plot 2: Average time
        bars2 = ax2.bar(range(len(top_procedures)), top_procedures['avg_time'])
        ax2.set_title(f'Average Time by CPT Code', fontsize=14, fontweight='bold')
        ax2.set_xlabel('CPT Code', fontsize=12)
        ax2.set_ylabel('Average Time (min)', fontsize=12)
        ax2.set_xticks(range(len(top_procedures)))
        ax2.set_xticklabels(top_procedures['cpt_code'], rotation=45)
        
        # Add value labels on bars
        for i, bar in enumerate(bars2):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}', ha='center', va='bottom')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Procedure profitability plot saved to: {save_path}")
        
        plt.close(fig)
    
    def plot_payer_performance(self, top_n=10, save_path=None):
        """Plot top insurance carriers by total payments."""
        df = self.get_payer_performance()
        
        numeric_cols = ['claim_count', 'avg_time', 'avg_anes_units', 'avg_med_units', 'total_time', 'total_anes_units', 'total_med_units']
        df[numeric_cols] = df[numeric_cols].fillna(0)
        
        if df.empty:
            logger.warning("No data available for payer performance analysis")
            return
        
        top_payers = df.head(top_n)
        
        fig, ax = plt.subplots(figsize=(12, 8))
        
        bars = ax.barh(range(len(top_payers)), top_payers['total_time'])
        ax.set_title(f'Top {top_n} Insurance Carriers by Total Time', 
                    fontsize=14, fontweight='bold')
        ax.set_xlabel('Total Time (min)', fontsize=12)
        ax.set_ylabel('Insurance Carrier', fontsize=12)
        ax.set_yticks(range(len(top_payers)))
        ax.set_yticklabels(top_payers['insurance_carrier'])
        
        # Add value labels on bars
        for i, bar in enumerate(bars):
            width = bar.get_width()
            ax.text(width, bar.get_y() + bar.get_height()/2.,
                   f'{width:.1f}', ha='left', va='center')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Payer performance plot saved to: {save_path}")
        
        plt.close(fig)
    
    def plot_seasonal_trends(self, save_path=None):
        """Plot seasonal trends in income."""
        df = self.get_seasonal_trends()
        
        numeric_cols = ['avg_monthly_income', 'avg_commission', 'report_count']
        df[numeric_cols] = df[numeric_cols].fillna(0)
        
        if df.empty:
            logger.warning("No data available for seasonal trends analysis")
            return
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        ax.plot(df['month_name'], df['avg_monthly_income'], 
               marker='o', linewidth=3, markersize=8)
        
        ax.set_title('Seasonal Income Trends', fontsize=16, fontweight='bold')
        ax.set_xlabel('Month', fontsize=12)
        ax.set_ylabel('Average Monthly Income ($)', fontsize=12)
        ax.grid(True, alpha=0.3)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Seasonal trends plot saved to: {save_path}")
        
        plt.close(fig)
    
    def plot_commission_correlation(self, save_path=None):
        """Plot correlation between billed amounts and commission."""
        df = self.get_commission_correlation()
        
        numeric_cols = ['total_commission', 'gross_pay', 'total_billed', 'total_paid', 'transaction_count']
        df[numeric_cols] = df[numeric_cols].fillna(0)
        
        if df.empty:
            logger.warning("No data available for commission correlation analysis")
            return
        
        # Remove rows with zero values for better correlation
        df_clean = df[(df['total_billed'] > 0) & (df['total_commission'] > 0)]
        
        if df_clean.empty:
            logger.warning("No valid data for commission correlation analysis")
            return
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        scatter = ax.scatter(df_clean['total_billed'], df_clean['total_commission'], 
                           alpha=0.6, s=60)
        
        # Add trend line
        z = np.polyfit(df_clean['total_billed'], df_clean['total_commission'], 1)
        p = np.poly1d(z)
        ax.plot(df_clean['total_billed'], p(df_clean['total_billed']), 
               "r--", alpha=0.8, linewidth=2)
        
        # Calculate correlation
        correlation = df_clean['total_billed'].corr(df_clean['total_commission'])
        
        ax.set_title(f'Commission vs Total Billed (Correlation: {correlation:.3f})', 
                    fontsize=14, fontweight='bold')
        ax.set_xlabel('Total Billed Amount ($)', fontsize=12)
        ax.set_ylabel('Total Commission ($)', fontsize=12)
        ax.grid(True, alpha=0.3)
        
        # Format axes as currency
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Commission correlation plot saved to: {save_path}")
        
        plt.close(fig)
    
    def generate_summary_report(self):
        """Generate a comprehensive summary report."""
        print("=" * 60)
        print("MEDICAL PRACTICE COMPENSATION ANALYSIS REPORT")
        print("=" * 60)
        print(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Basic statistics
        income_df = self.get_monthly_income_trend()
        if not income_df.empty:
            print("INCOME SUMMARY:")
            print(f"  Total months analyzed: {len(income_df)}")
            print(f"  Average monthly gross pay: ${income_df['gross_pay'].mean():,.2f}")
            print(f"  Highest monthly gross pay: ${income_df['gross_pay'].max():,.2f}")
            print(f"  Lowest monthly gross pay: ${income_df['gross_pay'].min():,.2f}")
            print(f"  Total gross pay (period): ${income_df['gross_pay'].sum():,.2f}")
            print()
        
        # Procedure analysis
        procedure_df = self.get_procedure_profitability()
        if not procedure_df.empty:
            print("PROCEDURE ANALYSIS:")
            print(f"  Total unique CPT codes: {len(procedure_df)}")
            print(f"  Most frequent procedure: {procedure_df.iloc[0]['cpt_code']} ({procedure_df.iloc[0]['frequency']} times)")
            print(f"  Highest paying procedure: {procedure_df.loc[procedure_df['avg_time'].idxmax()]['cpt_code']} (${procedure_df['avg_time'].max():,.2f})")
            print()
        
        # Payer analysis
        payer_df = self.get_payer_performance()
        if not payer_df.empty:
            print("PAYER ANALYSIS:")
            print(f"  Total insurance carriers: {len(payer_df)}")
            print(f"  Top payer: {payer_df.iloc[0]['insurance_carrier']} (${payer_df.iloc[0]['total_time']:,.2f})")
            print(f"  Average payment rate: {payer_df['avg_time'].mean():.1f}%")
            print()

    def get_available_years(self):
        """Return a sorted list of all years present in MasterCase.date_of_service."""
        session = get_session()
        try:
            years = session.query(sqlalchemy.extract('year', MasterCase.date_of_service)).distinct().all()
            years = sorted({int(y[0]) for y in years if y[0] is not None})
            return years
        finally:
            session.close()

    def get_master_case_analysis(self, year=None):
        """Get comprehensive analysis of master cases for a specific year (or latest year if not provided)."""
        session = get_session()
        try:
            cases = session.query(MasterCase).filter(MasterCase.date_of_service.isnot(None)).all()
            available_years = sorted({c.date_of_service.year for c in cases if c.date_of_service})
            if not available_years:
                return {}
            if year is None:
                year = max(available_years)
            # Filter cases for the selected year
            cases_for_year = [c for c in cases if c.date_of_service and c.date_of_service.year == year]
            # Pass all cases for year-over-year, but only cases_for_year for monthly, weekly, etc.
            yearly_data = self._analyze_yearly_data(cases)
            monthly_data = self._analyze_monthly_data(cases_for_year, year)
            weekly_data = self._analyze_weekly_data(cases_for_year, year)
            seasonal_data = self._analyze_seasonal_data(cases_for_year, year)
            regional_data = self._analyze_regional_anesthesia(cases_for_year, year)
            cpt_data = self._analyze_cpt_codes(cases_for_year, year)
            # Find extremes in the selected year
            if cases_for_year:
                longest_case = max(cases_for_year, key=lambda x: x.total_anes_time or 0)
                most_anes_units = max(cases_for_year, key=lambda x: x.total_anes_base_units or 0)
                most_med_units = max(cases_for_year, key=lambda x: x.total_med_base_units or 0)
                most_asmg_units = max(cases_for_year, key=lambda x: x.asmg_units or 0)
            else:
                longest_case = most_anes_units = most_med_units = most_asmg_units = None
            return {
                'total_cases': len(cases_for_year),
                'total_anes_time': sum(c.total_anes_time or 0 for c in cases_for_year),
                'total_anes_units': sum(c.total_anes_base_units or 0 for c in cases_for_year),
                'total_med_units': sum(c.total_med_base_units or 0 for c in cases_for_year),
                'total_asmg_units': sum(c.asmg_units or 0 for c in cases_for_year),
                'longest_case': {
                    'ticket': longest_case.patient_ticket_number if longest_case else None,
                    'time': longest_case.total_anes_time if longest_case else None,
                    'date': longest_case.date_of_service if longest_case else None
                },
                'most_anes_units': {
                    'ticket': most_anes_units.patient_ticket_number if most_anes_units else None,
                    'units': most_anes_units.total_anes_base_units if most_anes_units else None,
                    'date': most_anes_units.date_of_service if most_anes_units else None
                },
                'most_med_units': {
                    'ticket': most_med_units.patient_ticket_number if most_med_units else None,
                    'units': most_med_units.total_med_base_units if most_med_units else None,
                    'date': most_med_units.date_of_service if most_med_units else None
                },
                'most_asmg_units': {
                    'ticket': most_asmg_units.patient_ticket_number if most_asmg_units else None,
                    'units': most_asmg_units.asmg_units if most_asmg_units else None,
                    'date': most_asmg_units.date_of_service if most_asmg_units else None
                },
                'yearly_analysis': yearly_data,
                'monthly_analysis': monthly_data,
                'weekly_analysis': weekly_data,
                'seasonal_analysis': seasonal_data,
                'regional_anesthesia': regional_data,
                'cpt_analysis': cpt_data,
                'selected_year': year,
                'available_years': available_years
            }
        finally:
            session.close()

    def _analyze_yearly_data(self, cases):
        """Analyze data by year with year-over-year comparisons."""
        from collections import defaultdict
        import datetime
        
        yearly_stats = defaultdict(lambda: {
            'cases': 0, 'total_time': 0, 'total_anes_units': 0, 
            'total_med_units': 0, 'total_asmg_units': 0,
            'avg_time_per_case': 0, 'avg_anes_units_per_case': 0,
            'avg_med_units_per_case': 0, 'avg_asmg_units_per_case': 0
        })
        
        current_year = datetime.date.today().year
        
        for case in cases:
            if case.date_of_service:
                year = case.date_of_service.year
                yearly_stats[year]['cases'] += 1
                yearly_stats[year]['total_time'] += case.total_anes_time or 0
                yearly_stats[year]['total_anes_units'] += case.total_anes_base_units or 0
                yearly_stats[year]['total_med_units'] += case.total_med_base_units or 0
                yearly_stats[year]['total_asmg_units'] += case.asmg_units or 0
        
        # Calculate averages
        for year in yearly_stats:
            if yearly_stats[year]['cases'] > 0:
                yearly_stats[year]['avg_time_per_case'] = yearly_stats[year]['total_time'] / yearly_stats[year]['cases']
                yearly_stats[year]['avg_anes_units_per_case'] = yearly_stats[year]['total_anes_units'] / yearly_stats[year]['cases']
                yearly_stats[year]['avg_med_units_per_case'] = yearly_stats[year]['total_med_units'] / yearly_stats[year]['cases']
                yearly_stats[year]['avg_asmg_units_per_case'] = yearly_stats[year]['total_asmg_units'] / yearly_stats[year]['cases']
        
        # Year-over-year growth calculations
        years = sorted(yearly_stats.keys())
        yoy_growth = {}
        
        for i, year in enumerate(years[1:], 1):
            prev_year = years[i-1]
            yoy_growth[year] = {
                'cases_growth': self._calculate_growth_rate(
                    yearly_stats[prev_year]['cases'], yearly_stats[year]['cases']),
                'time_growth': self._calculate_growth_rate(
                    yearly_stats[prev_year]['total_time'], yearly_stats[year]['total_time']),
                'asmg_units_growth': self._calculate_growth_rate(
                    yearly_stats[prev_year]['total_asmg_units'], yearly_stats[year]['total_asmg_units'])
            }
        
        return {
            'yearly_stats': dict(yearly_stats),
            'yoy_growth': yoy_growth,
            'current_year': current_year,
            'years_with_data': years
        }

    def _analyze_monthly_data(self, cases, year):
        import datetime
        today = datetime.date.today()
        is_current_year = (year == today.year)
        last_month = today.month if is_current_year else 12
        # Prepare stats for all months up to current month
        monthly_stats = {m: {'cases': 0, 'total_time': 0, 'total_anes_units': 0, 'total_med_units': 0, 'total_asmg_units': 0} for m in range(1, last_month+1)}
        for case in cases:
            if case.date_of_service and case.date_of_service.year == year:
                month = case.date_of_service.month
                if month in monthly_stats:
                    monthly_stats[month]['cases'] += 1
                    monthly_stats[month]['total_time'] += case.total_anes_time or 0
                    monthly_stats[month]['total_anes_units'] += case.total_anes_base_units or 0
                    monthly_stats[month]['total_med_units'] += case.total_med_base_units or 0
                    monthly_stats[month]['total_asmg_units'] += case.asmg_units or 0
        # Year-to-date is the sum for the selected year up to current month
        ytd_stats = {
            'cases': sum(monthly_stats[m]['cases'] for m in monthly_stats),
            'total_time': sum(monthly_stats[m]['total_time'] for m in monthly_stats),
            'total_anes_units': sum(monthly_stats[m]['total_anes_units'] for m in monthly_stats),
            'total_med_units': sum(monthly_stats[m]['total_med_units'] for m in monthly_stats),
            'total_asmg_units': sum(monthly_stats[m]['total_asmg_units'] for m in monthly_stats),
        }
        
        # Calculate average weekly ASMG units for year-to-date
        # Count weeks from start of year to the last date in the data
        from datetime import date
        start_of_year = date(year, 1, 1)
        
        # Find the latest date in the cases for this year
        latest_date = None
        for case in cases:
            if case.date_of_service and case.date_of_service.year == year:
                if latest_date is None or case.date_of_service > latest_date:
                    latest_date = case.date_of_service
        
        # Use the latest date from data, or current date if no data
        end_date = latest_date if latest_date else (date.today() if is_current_year else date(year, 12, 31))
        weeks_elapsed = (end_date - start_of_year).days / 7
        ytd_stats['avg_weekly_asmg_units'] = ytd_stats['total_asmg_units'] / weeks_elapsed if weeks_elapsed > 0 else 0
        return {
            'monthly_stats': {year: monthly_stats},
            'monthly_averages': {},
            'ytd_stats': ytd_stats,
            'current_year': year,
            'current_month': last_month
        }

    def _analyze_seasonal_data(self, cases, year):
        """Analyze seasonal patterns and trends."""
        from collections import defaultdict
        import datetime
        
        seasonal_stats = defaultdict(lambda: {
            'cases': 0, 'total_time': 0, 'total_anes_units': 0, 
            'total_med_units': 0, 'total_asmg_units': 0
        })
        
        for case in cases:
            if case.date_of_service:
                month = case.date_of_service.month
                if month in [12, 1, 2]:
                    season = 'Winter'
                elif month in [3, 4, 5]:
                    season = 'Spring'
                elif month in [6, 7, 8]:
                    season = 'Summer'
                else:
                    season = 'Fall'
                
                seasonal_stats[season]['cases'] += 1
                seasonal_stats[season]['total_time'] += case.total_anes_time or 0
                seasonal_stats[season]['total_anes_units'] += case.total_anes_base_units or 0
                seasonal_stats[season]['total_med_units'] += case.total_med_base_units or 0
                seasonal_stats[season]['total_asmg_units'] += case.asmg_units or 0
        
        # Calculate seasonal averages
        for season in seasonal_stats:
            if seasonal_stats[season]['cases'] > 0:
                seasonal_stats[season]['avg_time_per_case'] = seasonal_stats[season]['total_time'] / seasonal_stats[season]['cases']
                seasonal_stats[season]['avg_anes_units_per_case'] = seasonal_stats[season]['total_anes_units'] / seasonal_stats[season]['cases']
                seasonal_stats[season]['avg_med_units_per_case'] = seasonal_stats[season]['total_med_units'] / seasonal_stats[season]['cases']
                seasonal_stats[season]['avg_asmg_units_per_case'] = seasonal_stats[season]['total_asmg_units'] / seasonal_stats[season]['cases']
        
        return dict(seasonal_stats)

    def _calculate_growth_rate(self, old_value, new_value):
        """Calculate percentage growth rate."""
        if old_value == 0:
            return 999999 if new_value > 0 else 0
        return ((new_value - old_value) / old_value) * 100

    def _analyze_weekly_data(self, cases, year):
        import datetime
        today = datetime.date.today()
        is_current_year = (year == today.year)
        last_week = today.isocalendar()[1] if is_current_year else datetime.date(year, 12, 28).isocalendar()[1]
        weekly_stats = {w: {'cases': 0, 'total_time': 0, 'total_anes_units': 0, 'total_med_units': 0, 'total_asmg_units': 0} for w in range(1, last_week+1)}
        for case in cases:
            if case.date_of_service and case.date_of_service.year == year:
                week = case.date_of_service.isocalendar()[1]
                if week in weekly_stats:
                    weekly_stats[week]['cases'] += 1
                    weekly_stats[week]['total_time'] += case.total_anes_time or 0
                    weekly_stats[week]['total_anes_units'] += case.total_anes_base_units or 0
                    weekly_stats[week]['total_med_units'] += case.total_med_base_units or 0
                    weekly_stats[week]['total_asmg_units'] += case.asmg_units or 0
        return weekly_stats

    def _analyze_regional_anesthesia(self, cases, year):
        """
        Analyze regional anesthesia cases (cases with medical units).
        
        Args:
            cases: List of MasterCase objects
            
        Returns:
            dict: Regional anesthesia analysis
        """
        from collections import defaultdict
        
        # Filter cases with medical units (regional anesthesia)
        regional_cases = [case for case in cases if case.total_med_base_units and case.total_med_base_units > 0]
        
        if not regional_cases:
            return {
                'total_regional_cases': 0,
                'percentage_of_total': 0,
                'total_med_units': 0,
                'average_med_units_per_case': 0,
                'by_temporal_period': {}
            }
        
        # Basic metrics
        total_regional_cases = len(regional_cases)
        total_med_units = sum(case.total_med_base_units for case in regional_cases)
        average_med_units_per_case = total_med_units / total_regional_cases
        percentage_of_total = (total_regional_cases / len(cases)) * 100 if cases else 0
        
        # Analyze by temporal periods (using ASMG rules)
        temporal_analysis = defaultdict(lambda: {'cases': 0, 'total_med_units': 0})
        
        for case in regional_cases:
            if case.date_of_service:
                # Determine temporal period based on ASMG rules
                try:
                    from asmg_calculator import ASMGCalculator
                    calculator = ASMGCalculator(self.session)
                    rule = calculator.get_applicable_rule(case.date_of_service)
                    period = rule.description if rule and rule.description else 'Unknown'
                except:
                    period = 'Unknown'
                
                temporal_analysis[period]['cases'] += 1
                temporal_analysis[period]['total_med_units'] += case.total_med_base_units
        
        return {
            'total_regional_cases': total_regional_cases,
            'percentage_of_total': percentage_of_total,
            'total_med_units': total_med_units,
            'average_med_units_per_case': average_med_units_per_case,
            'by_temporal_period': dict(temporal_analysis)
        }

    def _analyze_cpt_codes(self, cases, year):
        """
        Analyze CPT codes across all cases.
        
        Args:
            cases: List of MasterCase objects
            
        Returns:
            dict: CPT code analysis
        """
        from collections import defaultdict
        
        cpt_frequency = defaultdict(int)
        cpt_time = defaultdict(list)
        cpt_anes_units = defaultdict(list)
        
        for case in cases:
            if case.cpt_code:
                # Split multiple CPT codes
                cpt_codes = [code.strip() for code in case.cpt_code.split(',')]
                for cpt in cpt_codes:
                    if cpt:
                        cpt_frequency[cpt] += 1
                        if case.total_anes_time:
                            cpt_time[cpt].append(case.total_anes_time)
                        if case.total_anes_base_units:
                            cpt_anes_units[cpt].append(case.total_anes_base_units)
        
        # Get most common CPT codes
        most_common_cpt = sorted(cpt_frequency.items(), key=lambda x: x[1], reverse=True)
        
        # Calculate averages for each CPT
        cpt_averages = {}
        for cpt in cpt_frequency.keys():
            avg_time = sum(cpt_time[cpt]) / len(cpt_time[cpt]) if cpt_time[cpt] else 0
            avg_anes_units = sum(cpt_anes_units[cpt]) / len(cpt_anes_units[cpt]) if cpt_anes_units[cpt] else 0
            
            cpt_averages[cpt] = {
                'frequency': cpt_frequency[cpt],
                'average_time': avg_time,
                'average_anes_units': avg_anes_units
            }
        
        return {
            'most_common': most_common_cpt[:10],  # Top 10
            'total_unique_cpt_codes': len(cpt_frequency),
            'cpt_details': cpt_averages
        }

    def get_cpt_codes_with_history(self) -> dict:
        """
        Get CPT codes with their anesthesia base units and historical tracking.
        Focuses on standard units (whole/half numbers) and excludes split cases.
        Analyzes the last 5 years of data to track changes in anesthesia base units.
        
        Returns:
            dict: CPT codes with current units, historical changes, and statistics
        """
        try:
            from datetime import date, timedelta
            from collections import defaultdict
            
            # Get data from the last 5 years
            five_years_ago = date.today() - timedelta(days=5*365)
            
            query = """
            SELECT 
                ct.cpt_code,
                ct.anes_base_units,
                ct.anes_time_min,
                ct.date_of_service,
                ct.created_at
            FROM charge_transactions ct
            WHERE ct.cpt_code IS NOT NULL 
                AND ct.cpt_code != ''
                AND ct.anes_base_units IS NOT NULL
                AND ct.anes_base_units != ''
                AND ct.date_of_service IS NOT NULL
                AND ct.date_of_service != ''
            ORDER BY ct.cpt_code, ct.date_of_service
            """
            
            df = pd.read_sql_query(query, self.engine)
            
            if df.empty:
                return {}
            
            # Convert date_of_service to datetime - handle M/D/YY format
            df['date_of_service'] = pd.to_datetime(df['date_of_service'], format='%m/%d/%y', errors='coerce')
            df['created_at'] = pd.to_datetime(df['created_at'])
            
            # Filter to last 5 years
            df = df[df['date_of_service'] >= pd.Timestamp(five_years_ago)]
            
            # Convert anes_base_units to numeric
            df['anes_base_units'] = pd.to_numeric(df['anes_base_units'], errors='coerce')
            df['anes_time_min'] = pd.to_numeric(df['anes_time_min'], errors='coerce')
            
            # Filter to standard units only (whole numbers or half numbers)
            # This excludes split cases with decimal values like 1.23, 2.67, etc.
            df['is_standard_unit'] = (df['anes_base_units'] % 1 == 0) | (df['anes_base_units'] % 1 == 0.5)
            df = df[df['is_standard_unit'] == True]
            
            logger.info(f"Filtered to {len(df)} standard unit cases (excluded {5600 - len(df)} split cases)")
            
            # Group by CPT code and analyze
            cpt_data = {}
            
            for cpt_code in df['cpt_code'].unique():
                cpt_df = df[df['cpt_code'] == cpt_code].copy()
                
                if cpt_df.empty:
                    continue
                
                # Get current anesthesia base units (most recent non-null value)
                non_null_units = cpt_df['anes_base_units'].dropna()
                current_anes_units = non_null_units.iloc[-1] if not non_null_units.empty else None
                
                # Track historical changes
                history = []
                seen_units = set()
                
                # Group by year and get unique anesthesia base units
                cpt_df['year'] = cpt_df['date_of_service'].dt.year
                yearly_units = cpt_df.groupby('year')['anes_base_units'].agg(['mean', 'min', 'max']).reset_index()
                
                for _, row in yearly_units.iterrows():
                    year = int(row['year'])
                    avg_units = row['mean']
                    min_units = row['min']
                    max_units = row['max']
                    
                    # Only add to history if units changed
                    if avg_units not in seen_units:
                        seen_units.add(avg_units)
                        history.append({
                            'date': f"{year}",
                            'anes_units': f"{avg_units:.2f}",
                            'min_units': f"{min_units:.2f}",
                            'max_units': f"{max_units:.2f}"
                        })
                
                # Calculate statistics
                frequency = len(cpt_df)
                avg_time = cpt_df['anes_time_min'].mean() if not cpt_df['anes_time_min'].isna().all() else 0
                last_updated = cpt_df['created_at'].max().strftime('%Y-%m-%d') if not cpt_df['created_at'].isna().all() else 'N/A'
                
                cpt_data[cpt_code] = {
                    'current_anes_units': f"{current_anes_units:.1f}" if current_anes_units is not None else 'N/A',
                    'history': history,
                    'frequency': frequency,
                    'average_time': avg_time,
                    'last_updated': last_updated,
                    'has_changes': len(history) > 1,
                    'is_medical_procedure': current_anes_units == 0.0
                }
            
            # Sort by frequency (most used first)
            sorted_cpt_data = dict(sorted(cpt_data.items(), key=lambda x: x[1]['frequency'], reverse=True))
            
            return sorted_cpt_data
            
        except Exception as e:
            logger.error(f"Error getting CPT codes with history: {str(e)}")
            return {}

def main():
    """Main function for running analysis."""
    import numpy as np
    
    analyzer = CompensationAnalyzer()
    
    # Generate summary report
    analyzer.generate_summary_report()
    
    # Generate all plots
    print("Generating visualizations...")
    analyzer.plot_income_trend(save_path='income_trend.png')
    analyzer.plot_procedure_profitability(save_path='procedure_profitability.png')
    analyzer.plot_payer_performance(save_path='payer_performance.png')
    analyzer.plot_seasonal_trends(save_path='seasonal_trends.png')
    analyzer.plot_commission_correlation(save_path='commission_correlation.png')
    
    print("Analysis complete!")

if __name__ == "__main__":
    import numpy as np  # Import here to avoid issues if not available
    main()