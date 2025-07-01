#!/usr/bin/env python3
"""
Test script for master case analysis.
"""

from data_analyzer import CompensationAnalyzer

def test_master_case_analysis():
    """Test the master case analysis functionality."""
    try:
        analyzer = CompensationAnalyzer()
        
        # Test master case analysis
        print("Testing master case analysis...")
        analysis = analyzer.get_master_case_analysis()
        
        print(f"Analysis result: {analysis}")
        
        if analysis and 'total_cases' in analysis:
            print(f"✅ Total cases: {analysis['total_cases']}")
            print(f"✅ Total anesthesia time: {analysis.get('total_anes_time', 0)}")
            print(f"✅ Total anesthesia units: {analysis.get('total_anes_units', 0)}")
            print(f"✅ Total medical units: {analysis.get('total_med_units', 0)}")
            print(f"✅ Total ASMG units: {analysis.get('total_asmg_units', 0)}")
            
            if 'longest_case' in analysis:
                print(f"✅ Longest case: {analysis['longest_case']}")
            
            if 'productivity' in analysis:
                print(f"✅ Productivity data available")
                
            if 'regional_anesthesia' in analysis:
                print(f"✅ Regional anesthesia data available")
                
            if 'cpt_analysis' in analysis:
                print(f"✅ CPT analysis data available")
                
        else:
            print("❌ No analysis data returned")
            
    except Exception as e:
        print(f"❌ Error testing master case analysis: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_master_case_analysis() 