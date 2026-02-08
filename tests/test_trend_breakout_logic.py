import pytest
import pandas as pd
from datetime import datetime, timedelta
from option_auditor.common.data_utils import _calculate_trend_breakout_date

def create_ohlc_df(days=100, start_price=100.0):
    """
    Helper function to generate a mock OHLC DataFrame.
    """
    dates = [datetime(2023, 1, 1) + timedelta(days=i) for i in range(days)]
    data = []
    price = start_price

    for i in range(days):
        open_p = price
        high_p = price + 1.0
        low_p = price - 1.0
        close_p = price
        volume = 1000

        data.append({
            "Date": dates[i],
            "Open": open_p,
            "High": high_p,
            "Low": low_p,
            "Close": close_p,
            "Volume": volume
        })

    df = pd.DataFrame(data)
    df.set_index("Date", inplace=True)
    return df

def test_successful_breakout():
    """
    Test Case 1: A successful breakout above the 50-day high.
    Expected: Returns the date of the breakout.
    """
    df = create_ohlc_df(days=100, start_price=100.0)

    # Day 0-59: Price fluctuates around 100
    # Day 60: Breakout!
    breakout_idx = 60
    breakout_date = df.index[breakout_idx]

    # Set the breakout price significantly higher than the previous 50-day high
    # Previous Highs are around 101. Let's make it 105.
    df.loc[breakout_date, "Close"] = 105.0
    df.loc[breakout_date, "High"] = 106.0
    df.loc[breakout_date, "Low"] = 104.0

    # Days 61+: Maintain the new trend level to avoid hitting Low_20
    # Low_20 will be lagging. If we keep price at 105, Low_20 will eventually catch up to ~104.
    for i in range(breakout_idx + 1, 100):
        current_date = df.index[i]
        df.loc[current_date, "Close"] = 105.0
        df.loc[current_date, "High"] = 106.0
        df.loc[current_date, "Low"] = 104.0

    result = _calculate_trend_breakout_date(df)
    assert result == breakout_date.strftime("%Y-%m-%d")

def test_not_in_trend_below_low_20():
    """
    Test Case 2: An 'N/A' result when the price is below the 20-day low.
    Expected: Returns "N/A".
    """
    df = create_ohlc_df(days=100, start_price=100.0)

    # Establish a trend first so we have valid indicators
    # But then crash the price at the end

    # Breakout at day 60
    breakout_idx = 60
    for i in range(breakout_idx, 90):
        current_date = df.index[i]
        df.loc[current_date, "Close"] = 105.0
        df.loc[current_date, "High"] = 106.0
        df.loc[current_date, "Low"] = 104.0

    # Day 90+: Crash below Low_20
    # Low_20 would be around 104.
    # We drop price to 100.
    for i in range(90, 100):
        current_date = df.index[i]
        df.loc[current_date, "Close"] = 100.0
        df.loc[current_date, "High"] = 101.0
        df.loc[current_date, "Low"] = 99.0

    result = _calculate_trend_breakout_date(df)
    assert result == "N/A"

def test_insufficient_data():
    """
    Test Case 3: The behavior when there is exactly 49 days of data.
    Expected: Returns "N/A".
    """
    df = create_ohlc_df(days=49, start_price=100.0)
    result = _calculate_trend_breakout_date(df)
    assert result == "N/A"

def test_backwards_search_logic():
    """
    Test Case 4: Backwards search logic to find the earliest valid breakout date in a trend.
    Scenario:
    - Trend 1 starts (Day 60)
    - Trend 1 ends (Day 90, falls below Low_20)
    - Trend 2 starts (Day 110, breaks above 50-day High)
    - Current day (Day 150) is still in Trend 2.
    Expected: Returns the date of the second breakout (Day 110).
    """
    df = create_ohlc_df(days=150, start_price=100.0)

    # --- Phase 1: Initial Flat Period (Day 0-59) ---
    # Price 100. High 101. Low 99.

    # --- Phase 2: First Breakout (Day 60) ---
    # Breakout > High_50 (which is 101).
    breakout1_idx = 60
    for i in range(breakout1_idx, 90):
        current_date = df.index[i]
        df.loc[current_date, "Close"] = 105.0
        df.loc[current_date, "High"] = 106.0
        df.loc[current_date, "Low"] = 104.0

    # --- Phase 3: Trend Break (Day 90) ---
    # Price falls below Low_20.
    # Low_20 is ~104. We drop to 100.
    trend_break_idx = 90
    for i in range(trend_break_idx, 110):
        current_date = df.index[i]
        df.loc[current_date, "Close"] = 100.0
        df.loc[current_date, "High"] = 101.0
        df.loc[current_date, "Low"] = 99.0

    # --- Phase 4: Second Breakout (Day 110) ---
    # Needs to break High_50.
    # High_50 looks back 50 days (from day 60 to 109).
    # The max High in that period was 106 (from Phase 2).
    # So we need to break above 106. Let's go to 110.
    breakout2_idx = 110
    breakout2_date = df.index[breakout2_idx]

    for i in range(breakout2_idx, 150):
        current_date = df.index[i]
        df.loc[current_date, "Close"] = 110.0
        df.loc[current_date, "High"] = 111.0
        df.loc[current_date, "Low"] = 109.0

    result = _calculate_trend_breakout_date(df)

    # Assert return is NOT the first breakout, but the second one.
    assert result == breakout2_date.strftime("%Y-%m-%d")
    assert result != df.index[breakout1_idx].strftime("%Y-%m-%d")
