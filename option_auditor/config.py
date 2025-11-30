from typing import Dict

SYMBOL_DESCRIPTIONS: Dict[str, str] = {
    # Broad market ETFs and indices
    "SPY": "S&P 500 ETF", "QQQ": "Nasdaq-100 ETF", "DIA": "Dow Jones Industrial Average ETF",
    "IWM": "Russell 2000 ETF", "SPX": "S&P 500 Index", "XSP": "Mini S&P 500 Index",
    # Sector SPDRs
    "XLK": "Technology Select Sector SPDR ETF", "XLY": "Consumer Discretionary Select Sector SPDR ETF",
    "XLP": "Consumer Staples Select Sector SPDR ETF", "XLF": "Financial Select Sector SPDR ETF",
    "XLI": "Industrial Select Sector SPDR ETF", "XLV": "Health Care Select Sector SPDR ETF",
    "XLU": "Utilities Select Sector SPDR ETF", "XLB": "Materials Select Sector SPDR ETF",
    "XLRE": "Real Estate Select Sector SPDR ETF", "XLC": "Communication Services Select Sector SPDR ETF",
    "XLE": "Energy Select Sector SPDR ETF",
    # Commodities and rates ETFs
    "GLD": "SPDR Gold Shares", "SLV": "iShares Silver Trust", "TLT": "iShares 20+ Year Treasury Bond ETF",
    "IEF": "iShares 7-10 Year Treasury Bond ETF", "UNG": "United States Natural Gas Fund",
    # Single-name equities (common in fixtures)
    "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "NVIDIA", "AMD": "Advanced Micro Devices",
    "INTC": "Intel", "META": "Meta Platforms", "TSLA": "Tesla", "AMZN": "Amazon",
    "GOOGL": "Alphabet", "GOOG": "Alphabet", "ABNB": "Airbnb", "ORCL": "Oracle",
    "ADBE": "Adobe", "CRM": "Salesforce", "PYPL": "PayPal", "NKE": "Nike",
    "STZ": "Constellation Brands", "PFE": "Pfizer", "COIN": "Coinbase", "HOOD": "Robinhood Markets",
    "SMH": "VanEck Semiconductor ETF", "SOFI": "SoFi Technologies", "HIMS": "Hims & Hers Health",
    "KHC": "Kraft Heinz", "BMY": "Bristol Myers Squibb", "MCD": "McDonald's",
    "LULU": "Lululemon Athletica", "BRK/B": "Berkshire Hathaway Class B", "ENPH": "Enphase Energy",
    "AMAT": "Applied Materials",
}
