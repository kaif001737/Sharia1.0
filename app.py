from flask import Flask, render_template, request
import yfinance as yf
import pandas as pd

app = Flask(__name__)

def format_currency(val, is_price=False):
    if val is None or pd.isna(val) or val == 'N/A':
        return 'N/A'
    try:
        val = float(val)
        if is_price:
            return f"₹{val:,.2f}"
        if val >= 1e12:
            return f"₹{val / 1e12:.2f}T"
        elif val >= 1e9:
            return f"₹{val / 1e9:.2f}B"
        elif val >= 1e6:
            return f"₹{val / 1e6:.2f}M"
        else:
            return f"₹{val:,.2f}"
    except Exception:
        return str(val)

def get_exchange_rate(from_currency):
    if not from_currency or from_currency.upper() == 'INR':
        return 1.0
    try:
        pair = f"{from_currency.upper()}INR=X"
        ticker = yf.Ticker(pair)
        rate = ticker.info.get('regularMarketPrice') or ticker.info.get('previousClose')
        if rate:
            return float(rate)
    except Exception:
        pass
    # Fallbacks if ticker fetch fails
    fallbacks = {
        'USD': 83.5,
        'EUR': 90.0,
        'GBP': 105.0,
        'CAD': 61.0,
        'AUD': 55.0,
        'JPY': 0.55
    }
    return fallbacks.get(from_currency.upper(), 1.0)

def extract_financial_data(ticker, info):
    market_cap = info.get('marketCap')
    if not market_cap:
        shares = info.get('sharesOutstanding') or info.get('impliedSharesOutstanding')
        price = info.get('currentPrice') or info.get('previousClose')
        if shares and price:
            market_cap = shares * price

    debt = info.get('totalDebt')
    cash = info.get('totalCash')
    receivables = None

    bs = None
    try:
        bs = ticker.balance_sheet
    except Exception:
        pass

    if bs is not None and not bs.empty:
        if not debt:
            if 'Total Debt' in bs.index:
                debt = float(bs.loc['Total Debt'].iloc[0])
            elif 'Long Term Debt' in bs.index:
                lt_debt = float(bs.loc['Long Term Debt'].iloc[0]) if not pd.isna(bs.loc['Long Term Debt'].iloc[0]) else 0
                st_debt = float(bs.loc['Current Debt'].iloc[0]) if 'Current Debt' in bs.index and not pd.isna(bs.loc['Current Debt'].iloc[0]) else 0
                debt = lt_debt + st_debt

        if not cash:
            for key in ['Cash Cash Equivalents And Short Term Investments', 'Cash And Cash Equivalents', 'Cash Financial']:
                if key in bs.index:
                    cash = float(bs.loc[key].iloc[0])
                    break

        for key in ['Accounts Receivable', 'Receivables']:
            if key in bs.index:
                receivables = float(bs.loc[key].iloc[0])
                break

    revenue = info.get('totalRevenue')
    if not revenue:
        try:
            financials = ticker.financials
            if financials is not None and not financials.empty and 'Total Revenue' in financials.index:
                revenue = float(financials.loc['Total Revenue'].iloc[0])
        except Exception:
            pass

    return {
        'market_cap': float(market_cap) if market_cap is not None else None,
        'debt': float(debt) if debt is not None else None,
        'cash': float(cash) if cash is not None else None,
        'receivables': float(receivables) if receivables is not None else None,
        'revenue': float(revenue) if revenue is not None else None
    }

def shariah_check(
    industry,
    debt,
    market_cap,
    cash,
    receivables,
    total_revenue,
    non_halal_income=0
):
    forbidden = [
        "Bank",
        "Insurance",
        "Alcohol",
        "Tobacco",
        "Gambling",
        "Adult Entertainment",
        "Weapons"
    ]

    industry_compliant = True
    industry_matched = None
    if industry and isinstance(industry, str):
        for item in forbidden:
            if item.lower() in industry.lower():
                industry_compliant = False
                industry_matched = item
                break

    if not market_cap or market_cap == 0:
        return {
            'compliant': False,
            'status': 'Non-Shariah ❌',
            'industry_compliant': industry_compliant,
            'industry_matched': industry_matched,
            'debt_ratio': None,
            'cash_ratio': None,
            'receivable_ratio': None,
            'income_ratio': None,
            'reasons': ['Market Capitalization is missing or zero.'],
            'details': {
                'debt_ratio_pct': 'N/A',
                'cash_ratio_pct': 'N/A',
                'receivable_ratio_pct': 'N/A',
                'income_ratio_pct': 'N/A',
                'debt_progress_pct': 0,
                'cash_progress_pct': 0,
                'receivable_progress_pct': 0,
                'income_progress_pct': 0,
                'debt_is_compliant': False,
                'cash_is_compliant': False,
                'receivable_is_compliant': False,
                'income_is_compliant': False,
                'debt_val': 'N/A',
                'cash_val': 'N/A',
                'receivable_val': 'N/A',
                'revenue_val': 'N/A',
                'market_cap_val': 'N/A'
            }
        }

    d = debt if (debt is not None and not pd.isna(debt)) else 0
    c = cash if (cash is not None and not pd.isna(cash)) else 0
    r = receivables if (receivables is not None and not pd.isna(receivables)) else 0
    rev = total_revenue if (total_revenue is not None and not pd.isna(total_revenue)) else 0

    debt_ratio = d / market_cap
    cash_ratio = c / market_cap
    receivable_ratio = r / market_cap
    income_ratio = (non_halal_income / rev) if rev and rev > 0 else 0

    reasons = []
    if not industry_compliant:
        reasons.append(f"Forbidden Industry: Involved in {industry_matched or industry}")
    if debt_ratio >= 0.33:
        reasons.append(f"Debt Ratio too high: {debt_ratio:.2%} >= 33% (Limit: 33%)")
    if cash_ratio >= 0.33:
        reasons.append(f"Cash & Securities Ratio too high: {cash_ratio:.2%} >= 33% (Limit: 33%)")
    if receivable_ratio >= 0.49:
        reasons.append(f"Receivables Ratio too high: {receivable_ratio:.2%} >= 49% (Limit: 49%)")
    if income_ratio >= 0.05:
        reasons.append(f"Non-Halal Income Ratio too high: {income_ratio:.2%} >= 5% (Limit: 5%)")

    compliant = len(reasons) == 0

    return {
        'compliant': compliant,
        'status': 'Shariah Compliant ✅' if compliant else 'Non-Shariah ❌',
        'industry_compliant': industry_compliant,
        'industry_matched': industry_matched,
        'debt_ratio': debt_ratio,
        'cash_ratio': cash_ratio,
        'receivable_ratio': receivable_ratio,
        'income_ratio': income_ratio,
        'reasons': reasons,
        'details': {
            'debt_ratio_pct': f"{debt_ratio * 100:.2f}%",
            'cash_ratio_pct': f"{cash_ratio * 100:.2f}%",
            'receivable_ratio_pct': f"{receivable_ratio * 100:.2f}%",
            'income_ratio_pct': f"{income_ratio * 100:.2f}%",
            'debt_progress_pct': min(debt_ratio * 100, 100),
            'cash_progress_pct': min(cash_ratio * 100, 100),
            'receivable_progress_pct': min(receivable_ratio * 100, 100),
            'income_progress_pct': min(income_ratio * 100, 100),
            'debt_is_compliant': debt_ratio < 0.33,
            'cash_is_compliant': cash_ratio < 0.33,
            'receivable_is_compliant': receivable_ratio < 0.49,
            'income_is_compliant': income_ratio < 0.05,
            'debt_val': format_currency(d),
            'cash_val': format_currency(c),
            'receivable_val': format_currency(r),
            'revenue_val': format_currency(rev),
            'market_cap_val': format_currency(market_cap)
        }
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    symbol = request.form.get('symbol')

    try:
        company = yf.Ticker(symbol)
        info = company.info

        fin_data = extract_financial_data(company, info)

        # Get original currency and rate to INR
        currency = info.get('currency') or info.get('financialCurrency') or 'USD'
        rate = get_exchange_rate(currency)

        # Convert raw financial data to INR
        for key in ['market_cap', 'debt', 'cash', 'receivables', 'revenue']:
            if fin_data[key] is not None:
                fin_data[key] *= rate

        # Get price and convert to INR
        price_val = info.get('currentPrice') or info.get('previousClose')
        price_inr = None
        if price_val:
            price_inr = float(price_val) * rate

        shariah_res = shariah_check(
            industry=info.get('industry', ''),
            debt=fin_data['debt'],
            market_cap=fin_data['market_cap'],
            cash=fin_data['cash'],
            receivables=fin_data['receivables'],
            total_revenue=fin_data['revenue'],
            non_halal_income=0
        )

        # Cut short summary to first 2 sentences for a brief overview
        summary = info.get('longBusinessSummary', 'No description available.')
        short_summary = 'No description available.'
        if summary and summary != 'No description available.':
            sentences = [s.strip() for s in summary.split('. ') if s.strip()]
            if len(sentences) > 2:
                short_summary = '. '.join(sentences[:2]) + '.'
            elif len(sentences) > 0:
                short_summary = '. '.join(sentences) + '.'

        data = {
            'name': info.get('longName', 'N/A'),
            'symbol': symbol.upper(),
            'price': format_currency(price_inr, is_price=True),
            'market_cap': format_currency(fin_data['market_cap']),
            'revenue': format_currency(fin_data['revenue']),
            'employees': f"{info.get('fullTimeEmployees', 0):,}" if info.get('fullTimeEmployees') else 'N/A',
            'sector': info.get('sector', 'N/A'),
            'industry': info.get('industry', 'N/A'),
            'website': info.get('website', 'N/A'),
            'summary': short_summary,
            'shariah': shariah_res
        }

        return render_template('index.html', company=data)

    except Exception as e:
        return render_template(
            'index.html',
            error=f"Company not found. Error: {str(e)}"
        )

if __name__ == '__main__':
    app.run(debug=True)