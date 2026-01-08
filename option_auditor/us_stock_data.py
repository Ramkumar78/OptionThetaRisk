import pandas as pd
import os

# US Sector and Ticker Definitions
# Source: S&P 500 Sector Components

SECTOR_NAMES = {
    "XLC": "Communication Services",
    "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples",
    "XLE": "Energy",
    "XLF": "Financials",
    "XLV": "Health Care",
    "XLI": "Industrials",
    "XLK": "Technology",
    "XLB": "Materials",
    "XLRE": "Real Estate",
    "XLU": "Utilities",
}

SECTOR_COMPONENTS = {
    "XLC": ["META", "GOOGL", "GOOG", "NFLX", "TMUS", "DIS", "CMCSA", "VZ", "T", "CHTR"],
    "XLY": ["AMZN", "TSLA", "HD", "MCD", "TJX", "BKNG", "LOW", "SBUX", "NKE", "MAR"],
    "XLP": ["WMT", "PG", "COST", "KO", "PEP", "PM", "MDLZ", "MO", "CL", "TGT"],
    "XLE": ["XOM", "CVX", "COP", "WMB", "MPC", "EOG", "SLB", "PSX", "VLO", "KMI"],
    "XLF": ["BRK-B", "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "AXP", "C"],
    "XLV": ["LLY", "JNJ", "ABBV", "UNH", "MRK", "ABT", "TMO", "ISRG", "AMGN", "BSX"],
    "XLI": ["GE", "CAT", "RTX", "UBER", "GEV", "BA", "ETN", "UNP", "HON", "DE"],
    "XLK": ["NVDA", "AAPL", "MSFT", "AVGO", "ORCL", "CRM", "ADBE", "AMD", "CSCO", "IBM"],
    "XLB": ["LIN", "NEM", "SHW", "ECL", "FCX", "APD", "NUE", "MLM", "VMC", "CTVA"],
    "XLRE": ["PLD", "AMT", "EQIX", "WELL", "PSA", "SPG", "DLR", "O", "CCI", "CBRE"],
    "XLU": ["NEE", "SO", "DUK", "CEG", "AEP", "SRE", "VST", "PEG", "ED", "D"],
    "WATCH": [
        "PLTR", "SOFI", "MSTR", "COIN", "INTC", "MU", "QCOM", "AMAT", "TXN", "ARM",
        "SMCI", "DELL", "HPQ", "PANW", "SNOW", "NOW", "SHOP", "PYPL", "SQ", "HOOD",
        "DKNG", "RBLX", "SNAP", "PINS", "CVNA", "AFRM", "UPST", "AI", "MARA", "RIOT",
        "CLSK", "F", "GM", "RIVN", "LCID", "TSM", "BABA", "PDD", "NIO", "JD",
        "SPOT", "ABNB", "DASH", "CCL", "AAL", "PFE", "CVS", "GILD", "OXY", "LULU"
    ]
}

SECTOR_NAMES["WATCH"] = "High Interest / Growth"


def get_united_states_stocks():
    """
    Returns a custom list of US tickers from us_sectors.csv
    Includes Top 10 by sector and high liquid symbols.
    """
    try:
        # Construct path to the CSV file
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        csv_path = os.path.join(base_dir, 'option_auditor', 'data', 'us_sectors.csv')

        if not os.path.exists(csv_path):
            print(f"Warning: US Sectors file not found at {csv_path}")
            return []

        df = pd.read_csv(csv_path)
        # Assumes the column name is 'Symbol'
        if 'Symbol' in df.columns:
            # Clean: Remove duplicates, strip whitespace
            tickers = df['Symbol'].astype(str).str.strip().unique().tolist()
            # Filter out empty strings or weird headers
            tickers = [t for t in tickers if t and t != 'nan' and not t.startswith('/')]
            return tickers
        else:
            # Fallback if no header
            return df.iloc[:, 0].astype(str).str.strip().unique().tolist()

    except Exception as e:
        print(f"Error loading US Sectors: {e}")
        return []
