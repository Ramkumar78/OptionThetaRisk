import pandas as pd
import pytest
from option_auditor.common.serialization import serialize_ohlc_data

def test_serialize_ohlc_data_simple():
    data = {
        'Open': [100.0, 101.0],
        'High': [105.0, 106.0],
        'Low': [95.0, 96.0],
        'Close': [102.0, 103.0],
        'Volume': [1000, 2000]
    }
    index = pd.to_datetime(['2023-01-01', '2023-01-02'])
    df = pd.DataFrame(data, index=index)

    result = serialize_ohlc_data(df, "TEST")

    assert len(result) == 2
    assert result[0]['time'] == '2023-01-01'
    assert result[0]['open'] == 100.0
    assert result[0]['close'] == 102.0

def test_serialize_ohlc_data_multiindex():
    # Create MultiIndex DataFrame
    tuples = [('TEST', 'Open'), ('TEST', 'High'), ('TEST', 'Low'), ('TEST', 'Close'), ('TEST', 'Volume')]
    index = pd.MultiIndex.from_tuples(tuples)
    data = [[100.0, 105.0, 95.0, 102.0, 1000], [101.0, 106.0, 96.0, 103.0, 2000]]
    df = pd.DataFrame(data, index=pd.to_datetime(['2023-01-01', '2023-01-02']), columns=index)

    result = serialize_ohlc_data(df, "TEST")

    assert len(result) == 2
    assert result[0]['open'] == 100.0

def test_serialize_ohlc_data_lowercase_cols():
    data = {
        'open': [100.0],
        'high': [105.0],
        'low': [95.0],
        'close': [102.0],
        'volume': [1000]
    }
    index = pd.to_datetime(['2023-01-01'])
    df = pd.DataFrame(data, index=index)

    result = serialize_ohlc_data(df, "TEST")

    assert len(result) == 1
    assert result[0]['open'] == 100.0

def test_serialize_ohlc_data_empty():
    df = pd.DataFrame()
    result = serialize_ohlc_data(df, "TEST")
    assert result == []

def test_serialize_ohlc_data_missing_ticker_in_multiindex():
    tuples = [('OTHER', 'Open')]
    index = pd.MultiIndex.from_tuples(tuples)
    df = pd.DataFrame([[100.0]], index=pd.to_datetime(['2023-01-01']), columns=index)

    with pytest.raises(ValueError):
        serialize_ohlc_data(df, "TEST")

def test_serialize_ohlc_data_drops_incomplete_rows():
    data = {
        'Open': [100.0, None],
        'High': [105.0, 106.0],
        'Low': [95.0, 96.0],
        'Close': [102.0, 103.0],
        'Volume': [1000, 2000]
    }
    index = pd.to_datetime(['2023-01-01', '2023-01-02'])
    df = pd.DataFrame(data, index=index)

    result = serialize_ohlc_data(df, "TEST")
    assert len(result) == 1
    assert result[0]['time'] == '2023-01-01'
