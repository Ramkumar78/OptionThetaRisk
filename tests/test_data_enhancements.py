import pytest
from datetime import date
from unittest.mock import patch
import pandas as pd
from option_auditor.common.data_utils import get_market_holidays, get_currency_symbol, convert_currency, fetch_exchange_rate
from option_auditor.models import calculate_regulatory_fees
from option_auditor.uk_stock_data import apply_currency_conversion as uk_convert
from option_auditor.india_stock_data import apply_currency_conversion as india_convert

def test_regulatory_fees_uk():
    # £10k Buy
    fee = calculate_regulatory_fees("RR.L", 100.0, 100, action="BUY")
    # 0.5% of 10,000 = 50
    assert fee == 50.0

    # Sell should be 0 (Stamp Duty is on Purchase)
    fee_sell = calculate_regulatory_fees("RR.L", 100.0, 100, action="SELL")
    assert fee_sell == 0.0

def test_regulatory_fees_india():
    # ₹10k Buy
    fee = calculate_regulatory_fees("RELIANCE.NS", 1000.0, 10, action="BUY")
    # 0.1% of 10,000 = 10
    assert fee == 10.0

    # Sell should be 10 (Delivery STT is on both)
    fee_sell = calculate_regulatory_fees("RELIANCE.NS", 1000.0, 10, action="SELL")
    assert fee_sell == 10.0

def test_market_holidays():
    lse = get_market_holidays('LSE')
    nse = get_market_holidays('NSE')
    nyse = get_market_holidays('NYSE')

    assert date(2024, 12, 25) in lse
    assert date(2024, 1, 26) in nse
    assert date(2024, 7, 4) in nyse

def test_currency_symbol():
    assert get_currency_symbol("VOD.L") == "GBP"
    assert get_currency_symbol("INFY.NS") == "INR"
    assert get_currency_symbol("AAPL") == "USD"
    assert get_currency_symbol("SAP.DE") == "EUR"

@patch('option_auditor.common.data_utils.fetch_exchange_rate')
def test_convert_currency(mock_rate):
    mock_rate.return_value = 1.5 # GBPUSD

    val = convert_currency(100, "GBP", "USD")
    assert val == 150.0

@patch('option_auditor.india_stock_data.fetch_exchange_rate')
def test_india_data_conversion(mock_rate):
    mock_rate.return_value = 0.012 # INR -> USD

    df = pd.DataFrame({'Open': [100.0], 'Close': [110.0]})
    converted = india_convert(df, target_currency='USD')

    assert converted['Open'].iloc[0] == 1.2
    assert converted['Close'].iloc[0] == 1.32

@patch('option_auditor.uk_stock_data.fetch_exchange_rate')
def test_uk_data_conversion(mock_rate):
    # UK Data is GBp (Pence). Target USD.
    # Rate GBP -> USD = 1.25
    mock_rate.return_value = 1.25

    df = pd.DataFrame({'Open': [100.0], 'Close': [200.0]}) # 100p = £1, 200p = £2

    # 100p = 1 GBP. 1 GBP * 1.25 = 1.25 USD.
    converted = uk_convert(df, target_currency='USD', source_currency='GBp')

    assert converted['Open'].iloc[0] == 1.25
    assert converted['Close'].iloc[0] == 2.50
