import pandas as pd
import requests
import logging

logger = logging.getLogger("SP500_Data")

def get_sp500_tickers():
    """
    Fetches the current S&P 500 tickers from Wikipedia.
    Fallbacks to a smaller liquid list if scraping fails.
    """
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = pd.read_html(url)
        df = tables[0]
        tickers = df['Symbol'].tolist()

        # Clean tickers (replace dots with hyphens for some APIs,
        # but Yahoo prefers 'BRK-B' or 'BRK.B' depending on version.
        # Usually dot is safer for yfinance in some versions, but let's standardise.)
        tickers = [t.replace('.', '-') for t in tickers]

        logger.info(f"Successfully fetched {len(tickers)} S&P 500 tickers.")
        return tickers

    except Exception as e:
        logger.error(f"Failed to fetch S&P 500 from Wikipedia: {e}")
        # Fallback to Top 50 Liquid Tech/Etc if scraping fails (Safety Net)
        return [
            "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK-B", "LLY", "AVGO",
            "V", "JPM", "XOM", "WMT", "UNH", "MA", "PG", "JNJ", "HD", "COST", "ORCL", "MRK",
            "ABBV", "CVX", "BAC", "KO", "CRM", "NFLX", "AMD", "PEP", "TMO", "LIN", "WFC",
            "ADBE", "DIS", "MCD", "CSCO", "ACN", "ABT", "QCOM", "CAT", "VZ", "INTU", "IBM",
            "AMAT", "CMCSA", "PFE", "UBER", "GE", "ISRG"
        ]
