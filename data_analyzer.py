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
from database_models import engine, get_session
from asmg_calculator import ASMGCalculator

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
            AVG(billed_amount) as avg_billed,
            AVG(paid_amount) as avg_paid,
            SUM(billed_amount) as total_billed,
            SUM(paid_amount) as total_paid,
            (AVG(paid_amount) / NULLIF(AVG(billed_amount), 0)) * 100 as payment_rate
        FROM charge_transactions 
        WHERE cpt_code IS NOT NULL AND cpt_code != ''
        GROUP BY cpt_code
        HAVING frequency >= 5  -- Only include codes with at least 5 occurrences
        ORDER BY frequency DESC
        """
        
        df = pd.read_sql_query(query, self.engine)
        numeric_cols = ['frequency', 'avg_billed', 'avg_paid', 'total_billed', 'total_paid', 'payment_rate']
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
            insurance_carrier,
            COUNT(*) as claim_count,
            AVG(billed_amount) as avg_billed,
            AVG(paid_amount) as avg_paid,
            SUM(billed_amount) as total_billed,
            SUM(paid_amount) as total_paid,
            (SUM(paid_amount) / NULLIF(SUM(billed_amount), 0)) * 100 as overall_payment_rate
        FROM charge_transactions 
        WHERE insurance_carrier IS NOT NULL AND insurance_carrier != ''
        GROUP BY insurance_carrier
        HAVING claim_count >= 10  -- Only include carriers with at least 10 claims
        ORDER BY total_paid DESC
        """
        
        df = pd.read_sql_query(query, self.engine)
        numeric_cols = ['claim_count', 'avg_billed', 'avg_paid', 'total_billed', 'total_paid', 'overall_payment_rate']
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
        
        numeric_cols = ['frequency', 'avg_billed', 'avg_paid', 'total_billed', 'total_paid', 'payment_rate']
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
        
        # Plot 2: Average payment
        bars2 = ax2.bar(range(len(top_procedures)), top_procedures['avg_paid'])
        ax2.set_title(f'Average Payment by CPT Code', fontsize=14, fontweight='bold')
        ax2.set_xlabel('CPT Code', fontsize=12)
        ax2.set_ylabel('Average Payment ($)', fontsize=12)
        ax2.set_xticks(range(len(top_procedures)))
        ax2.set_xticklabels(top_procedures['cpt_code'], rotation=45)
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
        
        # Add value labels on bars
        for i, bar in enumerate(bars2):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'${height:,.0f}', ha='center', va='bottom')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Procedure profitability plot saved to: {save_path}")
        
        plt.close(fig)
    
    def plot_payer_performance(self, top_n=10, save_path=None):
        """Plot top insurance carriers by total payments."""
        df = self.get_payer_performance()
        
        numeric_cols = ['claim_count', 'avg_billed', 'avg_paid', 'total_billed', 'total_paid', 'overall_payment_rate']
        df[numeric_cols] = df[numeric_cols].fillna(0)
        
        if df.empty:
            logger.warning("No data available for payer performance analysis")
            return
        
        top_payers = df.head(top_n)
        
        fig, ax = plt.subplots(figsize=(12, 8))
        
        bars = ax.barh(range(len(top_payers)), top_payers['total_paid'])
        ax.set_title(f'Top {top_n} Insurance Carriers by Total Payments', 
                    fontsize=14, fontweight='bold')
        ax.set_xlabel('Total Payments ($)', fontsize=12)
        ax.set_ylabel('Insurance Carrier', fontsize=12)
        ax.set_yticks(range(len(top_payers)))
        ax.set_yticklabels(top_payers['insurance_carrier'])
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
        
        # Add value labels on bars
        for i, bar in enumerate(bars):
            width = bar.get_width()
            ax.text(width, bar.get_y() + bar.get_height()/2.,
                   f'${width:,.0f}', ha='left', va='center', fontweight='bold')
        
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
            print(f"  Highest paying procedure: {procedure_df.loc[procedure_df['avg_paid'].idxmax()]['cpt_code']} (${procedure_df['avg_paid'].max():,.2f})")
            print()
        
        # Payer analysis
        payer_df = self.get_payer_performance()
        if not payer_df.empty:
            print("PAYER ANALYSIS:")
            print(f"  Total insurance carriers: {len(payer_df)}")
            print(f"  Top payer: {payer_df.iloc[0]['insurance_carrier']} (${payer_df.iloc[0]['total_paid']:,.2f})")
            print(f"  Average payment rate: {payer_df['overall_payment_rate'].mean():.1f}%")
            print()

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