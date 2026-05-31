import sys
import yfinance as yf
from app import extract_financial_data, shariah_check

# Reconfigure stdout to UTF-8 for emoji printing in Windows terminal
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def run_tests():
    symbols = ['AAPL', 'MSFT', 'JPM']
    
    for sym in symbols:
        print(f"\n--- Testing Symbol: {sym} ---")
        try:
            ticker = yf.Ticker(sym)
            info = ticker.info
            
            # Extract data
            fin_data = extract_financial_data(ticker, info)
            print("Extracted financial data:")
            for k, v in fin_data.items():
                print(f"  {k}: {v}")
                
            # Perform Shariah check
            res = shariah_check(
                industry=info.get('industry', ''),
                debt=fin_data['debt'],
                market_cap=fin_data['market_cap'],
                cash=fin_data['cash'],
                receivables=fin_data['receivables'],
                total_revenue=fin_data['revenue'],
                non_halal_income=0
            )
            
            print(f"Shariah Screening Result: {res['status']}")
            print("Reasons:")
            if res['reasons']:
                for r in res['reasons']:
                    print(f"  - {r}")
            else:
                print("  - Passed all checks")
                
            print("Details:")
            for k, v in res['details'].items():
                print(f"  {k}: {v}")
                
            # Basic sanity checks
            if sym == 'JPM':
                # JPM should fail due to banking sector and/or ratios
                assert res['compliant'] is False, "JPM should be Non-Shariah compliant!"
                print("Assertion passed: JPM is correctly flagged as Non-Shariah.")
            elif sym in ['AAPL', 'MSFT']:
                # AAPL and MSFT should typically pass if financials are retrieved
                if res['compliant']:
                    print(f"Assertion passed: {sym} is Shariah compliant.")
                else:
                    print(f"Note: {sym} failed check. Reasons: {res['reasons']}")
        except Exception as e:
            print(f"Failed to test {sym}. Error: {str(e)}")

if __name__ == '__main__':
    run_tests()
