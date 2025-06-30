#!/usr/bin/env python3
"""Test the Mo service type fix"""

from data_extractor import MedicalReportExtractor

# Test lines with Mo service type
test_lines = [
    '61411904 Gorman Jean UF Mo 99100 PPO 4/25/25 5/13/25 0 0.00 0.0 1.0 124.00 UTCS 100 0.00 0.00 0.00 0 0.00 0.00 0.00',
    '61411908 Yee Isabella L UF Mo 99100 HMO 4/28/25 5/13/25 0 0.00 0.0 1.0 124.00 UTCS 100 0.00 0.00 0.00 0 0.00 0.00 0.00',
    '61411952 Geis Cappie A UF Mo 99100 PPO 5/15/25 5/21/25 0 0.00 0.0 1.0 124.00 UTCS 100 0.00 0.00 0.00 0 0.00 0.00 0.00'
]

extractor = MedicalReportExtractor()

print("=== TESTING Mo SERVICE TYPE PARSING ===")
for line in test_lines:
    print(f"\nTesting: {line[:50]}...")
    result = extractor._parse_charge_transaction_line(line)
    if result:
        print("✓ PARSED SUCCESSFULLY")
        print(f"  Ticket: {result.get('Phys Ticket Ref#')}")
        print(f"  Site: {result.get('Site Code')}")
        print(f"  Service: {result.get('Serv Type')}")
        print(f"  CPT: {result.get('CPT Code')}")
        print(f"  Pay Code: {result.get('Pay Code')}")
    else:
        print("✗ FAILED TO PARSE")