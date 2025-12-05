import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

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

TICKER_NAMES = {
    "ECL": "Ecolab Inc.",
    "PLTR": "Palantir Technologies Inc.",
    "SOFI": "SoFi Technologies, Inc.",
    "MSTR": "MicroStrategy Incorporated",
    "COIN": "Coinbase Global, Inc.",
    "INTC": "Intel Corporation",
    "MU": "Micron Technology, Inc.",
    "QCOM": "Qualcomm Incorporated",
    "AMAT": "Applied Materials, Inc.",
    "TXN": "Texas Instruments Incorporated",
    "ARM": "Arm Holdings plc",
    "SMCI": "Super Micro Computer, Inc.",
    "DELL": "Dell Technologies Inc.",
    "HPQ": "HP Inc.",
    "PANW": "Palo Alto Networks, Inc.",
    "SNOW": "Snowflake Inc.",
    "NOW": "ServiceNow, Inc.",
    "SHOP": "Shopify Inc.",
    "PYPL": "PayPal Holdings, Inc.",
    "SQ": "Block, Inc.",
    "HOOD": "Robinhood Markets, Inc.",
    "DKNG": "DraftKings Inc.",
    "RBLX": "Roblox Corporation",
    "SNAP": "Snap Inc.",
    "PINS": "Pinterest, Inc.",
    "CVNA": "Carvana Co.",
    "AFRM": "Affirm Holdings, Inc.",
    "UPST": "Upstart Holdings, Inc.",
    "AI": "C3.ai, Inc.",
    "MARA": "Marathon Digital Holdings, Inc.",
    "RIOT": "Riot Platforms, Inc.",
    "CLSK": "CleanSpark, Inc.",
    "F": "Ford Motor Company",
    "GM": "General Motors Company",
    "RIVN": "Rivian Automotive, Inc.",
    "LCID": "Lucid Group, Inc.",
    "TSM": "Taiwan Semiconductor Manufacturing",
    "BABA": "Alibaba Group Holding Limited",
    "PDD": "PDD Holdings Inc.",
    "NIO": "NIO Inc.",
    "JD": "JD.com, Inc.",
    "SPOT": "Spotify Technology S.A.",
    "ABNB": "Airbnb, Inc.",
    "DASH": "DoorDash, Inc.",
    "CCL": "Carnival Corporation & plc",
    "AAL": "American Airlines Group Inc.",
    "PFE": "Pfizer Inc.",
    "CVS": "CVS Health Corporation",
    "GILD": "Gilead Sciences, Inc.",
    "OXY": "Occidental Petroleum Corporation",
    "LULU": "Lululemon Athletica Inc.",
}

UK_EURO_TICKERS = [
    # Top 50 FTSE (UK)
    "AZN", "SHEL", "HSBA", "ULVR", "BP.", "RIO", "REL", "GSK", "DGE", "LSEG", "BATS", "GLEN", "BA.", "CNA", "NG.", "LLOY", "RR.", "BARC", "CPG", "NWG", "RKT", "VOD", "AAL", "SGE", "HLN", "EXR", "TSCO", "SSE", "MNG", "ADM", "III", "ANTO", "SPX", "STAN", "IMB", "WTB", "SVT", "AUTO", "SN.", "CRDA", "WPP", "SMIN", "DCC", "AV.", "LGEN", "KGF", "SBRY", "MKS", "LAND", "PSON",
    # Liquid UK
    "JD.", "IAG", "EZJ", "TUI", "AML", "IDS", "DLG", "ITM", "CINE", "PFC", "FRES", "KAP", "BOO", "ASOS", "HBR", "ENOG", "TLW", "CWR", "GNC", "THG", "DARK", "CURY", "DOM", "WKB", "SFOR", "QINET", "GREG", "PETS", "VMUK", "MRO", "INVP", "OCDO", "IGG", "CMC", "PLUS", "EMG", "HWDN", "COST", "BEZ", "SGRO", "BDEV", "PSN", "TW.", "RDW", "VISTRY", "BYG", "SAFE", "UTG", "BBOX", "GRG",
    # Top 50 Euro
    "ASML", "MC", "SAP", "RMS", "TTE", "SIE", "CDI", "AIR", "SAN", "IBE", "OR", "ALV", "SU", "EL", "AI", "BNP", "DTE", "ENEL", "DG", "BBVA", "CS", "BAS", "ADS", "MUV2", "IFX", "SAF", "ENI", "INGA", "ISP", "KER", "STLA", "AD", "VOW3", "BMW", "MBG", "BAYN", "DB1", "BN", "RI", "CRH", "G", "PHIA", "AH", "NOKIA", "VIV", "ORANGE", "KNEBV", "UMG", "HEIA", "ABI"
]

def get_uk_euro_tickers():
    """Returns normalized UK/Euro tickers list."""
    tickers = []

    # Process the raw list
    for t in UK_EURO_TICKERS:
        # Heuristic for UK tickers:
        # If user input has dot at end (e.g. "BP."), replace with .L
        if t.endswith("."):
            tickers.append(t[:-1] + ".L")
        else:
            # Check against known UK list (without dots)
            # Reconstruct sets for logic (using known UK tickers from the list)
            uk_set = {
                "AZN", "SHEL", "HSBA", "ULVR", "BP.", "RIO", "REL", "GSK", "DGE", "LSEG", "BATS", "GLEN", "BA.", "CNA", "NG.", "LLOY", "RR.", "BARC", "CPG", "NWG", "RKT", "VOD", "AAL", "SGE", "HLN", "EXR", "TSCO", "SSE", "MNG", "ADM", "III", "ANTO", "SPX", "STAN", "IMB", "WTB", "SVT", "AUTO", "SN.", "CRDA", "WPP", "SMIN", "DCC", "AV.", "LGEN", "KGF", "SBRY", "MKS", "LAND", "PSON",
                "JD.", "IAG", "EZJ", "TUI", "AML", "IDS", "DLG", "ITM", "CINE", "PFC", "FRES", "KAP", "BOO", "ASOS", "HBR", "ENOG", "TLW", "CWR", "GNC", "THG", "DARK", "CURY", "DOM", "WKB", "SFOR", "QINET", "GREG", "PETS", "VMUK", "MRO", "INVP", "OCDO", "IGG", "CMC", "PLUS", "EMG", "HWDN", "COST", "BEZ", "SGRO", "BDEV", "PSN", "TW.", "RDW", "VISTRY", "BYG", "SAFE", "UTG", "BBOX", "GRG"
            }

            # Simple check: if it's in the UK set (or has a dot version in UK set)
            if t in uk_set or (t + ".") in uk_set:
                 # It's UK but doesn't have the dot in the raw string here?
                 # Actually the raw string is exactly what is in the list.
                 # "AZN" is in the list. So append .L
                 tickers.append(t + ".L")
            else:
                # Assume Euro or US-listed Euro
                tickers.append(t)

    return list(set(tickers))

TICKER_NAMES = {
    "ECL": "Ecolab Inc.",
    "AZN": "AstraZeneca PLC",
    "SHEL": "Shell plc",
    "HSBA": "HSBC Holdings plc",
    "ULVR": "Unilever PLC",
    "BP": "BP p.l.c.",
    "RIO": "Rio Tinto Group",
    "REL": "RELX PLC",
    "GSK": "GSK plc",
    "DGE": "Diageo plc",
    "LSEG": "London Stock Exchange Group plc",
    "BATS": "British American Tobacco p.l.c.",
    "GLEN": "Glencore plc",
    "BA": "BAE Systems plc",
    "CNA": "Centrica plc",
    "NG": "National Grid plc",
    "LLOY": "Lloyds Banking Group plc",
    "RR": "Rolls-Royce Holdings plc",
    "BARC": "Barclays PLC",
    "CPG": "Compass Group PLC",
    "NWG": "NatWest Group plc",
    "RKT": "Reckitt Benckiser Group plc",
    "VOD": "Vodafone Group Plc",
    "AAL": "Anglo American plc",
    "SGE": "Sage Group plc",
    "HLN": "Haleon plc",
    "EXR": "Exor N.V.",
    "TSCO": "Tesco PLC",
    "SSE": "SSE plc",
    "MNG": "M&G plc",
    "ADM": "Admiral Group plc",
    "III": "3i Group plc",
    "ANTO": "Antofagasta plc",
    "SPX": "Spirax-Sarco Engineering plc",
    "STAN": "Standard Chartered PLC",
    "IMB": "Imperial Brands PLC",
    "WTB": "Whitbread PLC",
    "SVT": "Severn Trent Plc",
    "AUTO": "Auto Trader Group plc",
    "SN": "Smith & Nephew plc",
    "CRDA": "Croda International Plc",
    "WPP": "WPP plc",
    "SMIN": "Smiths Group plc",
    "DCC": "DCC plc",
    "AV": "Aviva plc",
    "LGEN": "Legal & General Group Plc",
    "KGF": "Kingfisher plc",
    "SBRY": "J Sainsbury plc",
    "MKS": "Marks and Spencer Group plc",
    "LAND": "Land Securities Group PLC",
    "PSON": "Pearson plc",
    "JD": "JD Sports Fashion plc",
    "IAG": "International Consolidated Airlines Group S.A.",
    "EZJ": "easyJet plc",
    "TUI": "TUI AG",
    "AML": "Aston Martin Lagonda Global Holdings plc",
    "IDS": "International Distributions Services plc",
    "DLG": "Direct Line Insurance Group plc",
    "ITM": "ITM Power Plc",
    "CINE": "Cineworld Group plc",
    "PFC": "Petrofac Limited",
    "FRES": "Fresnillo plc",
    "KAP": "Kazatomprom",
    "BOO": "boohoo group plc",
    "ASOS": "ASOS Plc",
    "HBR": "Harbour Energy plc",
    "ENOG": "Energean plc",
    "TLW": "Tullow Oil plc",
    "CWR": "Ceres Power Holdings plc",
    "GNC": "Greencore Group plc",
    "THG": "THG plc",
    "DARK": "Darktrace plc",
    "CURY": "Currys plc",
    "DOM": "Domino's Pizza Group plc",
    "WKB": "Warhammer (Games Workshop Group PLC)",
    "SFOR": "S4 Capital plc",
    "QINET": "QinetiQ Group plc",
    "GREG": "Greggs plc",
    "PETS": "Pets at Home Group Plc",
    "VMUK": "Virgin Money UK PLC",
    "MRO": "Melrose Industries PLC",
    "INVP": "Investec plc",
    "OCDO": "Ocado Group plc",
    "IGG": "IG Group Holdings plc",
    "CMC": "CMC Markets plc",
    "PLUS": "Plus500 Ltd",
    "EMG": "Man Group plc",
    "HWDN": "Howden Joinery Group Plc",
    "COST": "Costain Group PLC",
    "BEZ": "Beazley plc",
    "SGRO": "Segro Plc",
    "BDEV": "Barratt Developments plc",
    "PSN": "Persimmon Plc",
    "TW": "Taylor Wimpey plc",
    "RDW": "Redrow plc",
    "VISTRY": "Vistry Group PLC",
    "BYG": "Big Yellow Group PLC",
    "SAFE": "Safestore Holdings plc",
    "UTG": "Unite Group plc",
    "BBOX": "Tritax Big Box REIT plc",
    "GRG": "Greggs plc",
    "ASML": "ASML Holding N.V.",
    "MC": "LVMH Moët Hennessy - Louis Vuitton, SE",
    "SAP": "SAP SE",
    "RMS": "Hermès International",
    "TTE": "TotalEnergies SE",
    "SIE": "Siemens AG",
    "CDI": "Christian Dior SE",
    "AIR": "Airbus SE",
    "SAN": "Banco Santander, S.A.",
    "IBE": "Iberdrola, S.A.",
    "OR": "L'Oréal S.A.",
    "ALV": "Allianz SE",
    "SU": "Schneider Electric S.E.",
    "EL": "EssilorLuxottica",
    "AI": "Air Liquide S.A.",
    "BNP": "BNP Paribas S.A.",
    "DTE": "Deutsche Telekom AG",
    "ENEL": "Enel S.p.A.",
    "DG": "Vinci S.A.",
    "BBVA": "Banco Bilbao Vizcaya Argentaria, S.A.",
    "CS": "AXA S.A.",
    "BAS": "BASF SE",
    "ADS": "adidas AG",
    "MUV2": "Münchener Rückversicherungs-Gesellschaft",
    "IFX": "Infineon Technologies AG",
    "SAF": "Safran S.A.",
    "ENI": "Eni S.p.A.",
    "INGA": "ING Groep N.V.",
    "ISP": "Intesa Sanpaolo S.p.A.",
    "KER": "Kering S.A.",
    "STLA": "Stellantis N.V.",
    "AD": "Koninklijke Ahold Delhaize N.V.",
    "VOW3": "Volkswagen AG",
    "BMW": "Bayerische Motoren Werke AG",
    "MBG": "Mercedes-Benz Group AG",
    "BAYN": "Bayer AG",
    "DB1": "Deutsche Börse AG",
    "BN": "Danone S.A.",
    "RI": "Pernod Ricard S.A.",
    "CRH": "CRH plc",
    "G": "Assicurazioni Generali S.p.A.",
    "PHIA": "Koninklijke Philips N.V.",
    "AH": "Koninklijke Ahold Delhaize N.V.",
    "NOKIA": "Nokia Oyj",
    "VIV": "Vivendi SE",
    "ORANGE": "Orange S.A.",
    "KNEBV": "Kone Oyj",
    "UMG": "Universal Music Group N.V.",
    "HEIA": "Heineken N.V.",
    "ABI": "Anheuser-Busch InBev SA/NV",
    "LLY": "Eli Lilly and Company",
    "SPG": "Simon Property Group, Inc.",
    "CVX": "Chevron Corporation",
    "AVGO": "Broadcom Inc.",
    "SBUX": "Starbucks Corporation",
    "PEG": "Public Service Enterprise Group",
    "DLR": "Digital Realty Trust, Inc.",
    "MA": "Mastercard Incorporated",
    "APD": "Air Products and Chemicals, Inc",
    "AMD": "Advanced Micro Devices, Inc.",
    "MO": "Altria Group, Inc.",
    "CBRE": "CBRE Group Inc",
    "NUE": "Nucor Corporation",
    "JPM": "JP Morgan Chase & Co.",
    "ADBE": "Adobe Inc.",
    "PEP": "Pepsico, Inc.",
    "ABT": "Abbott Laboratories",
    "AMZN": "Amazon.com, Inc.",
    "EQIX": "Equinix, Inc.",
    "TGT": "Target Corporation",
    "NEM": "Newmont Corporation",
    "DIS": "Walt Disney Company (The)",
    "MDLZ": "Mondelez International, Inc.",
    "PG": "Procter & Gamble Company (The)",
    "TSLA": "Tesla, Inc.",
    "UNP": "Union Pacific Corporation",
    "V": "Visa Inc.",
    "VST": "Vistra Corp.",
    "DE": "Deere & Company",
    "TJX": "TJX Companies, Inc. (The)",
    "VZ": "Verizon Communications Inc.",
    "PSA": "Public Storage",
    "O": "Realty Income Corporation",
    "PLD": "Prologis, Inc.",
    "MS": "Morgan Stanley",
    "COST": "Costco Wholesale Corporation",
    "HD": "Home Depot, Inc. (The)",
    "SO": "Southern Company (The)",
    "BA": "Boeing Company (The)",
    "LOW": "Lowe's Companies, Inc.",
    "RTX": "RTX Corporation",
    "DUK": "Duke Energy Corporation (Holdin",
    "AMT": "American Tower Corporation (REI",
    "AXP": "American Express Company",
    "GE": "GE Aerospace",
    "TMUS": "T-Mobile US, Inc.",
    "UNH": "UnitedHealth Group Incorporated",
    "WFC": "Wells Fargo & Company",
    "KO": "Coca-Cola Company (The)",
    "AEP": "American Electric Power Company",
    "BKNG": "Booking Holdings Inc. Common St",
    "NFLX": "Netflix, Inc.",
    "MPC": "Marathon Petroleum Corporation",
    "ISRG": "Intuitive Surgical, Inc.",
    "FCX": "Freeport-McMoRan, Inc.",
    "GS": "Goldman Sachs Group, Inc. (The)",
    "GOOG": "Alphabet Inc.",
    "BSX": "Boston Scientific Corporation",
    "GOOGL": "Alphabet Inc.",
    "MRK": "Merck & Company, Inc.",
    "CRM": "Salesforce, Inc.",
    "CTVA": "Corteva, Inc.",
    "PSX": "Phillips 66",
    "CCI": "Crown Castle Inc.",
    "MAR": "Marriott International",
    "AAPL": "Apple Inc.",
    "COP": "ConocoPhillips",
    "WMB": "Williams Companies, Inc. (The)",
    "CMCSA": "Comcast Corporation",
    "CL": "Colgate-Palmolive Company",
    "PM": "Philip Morris International Inc",
    "WELL": "Welltower Inc.",
    "MLM": "Martin Marietta Materials, Inc.",
    "NEE": "NextEra Energy, Inc.",
    "MSFT": "Microsoft Corporation",
    "NVDA": "NVIDIA Corporation",
    "GEV": "GE Vernova Inc.",
    "CHTR": "Charter Communications, Inc.",
    "EOG": "EOG Resources, Inc.",
    "VMC": "Vulcan Materials Company (Holdi",
    "BAC": "Bank of America Corporation",
    "WMT": "Walmart Inc.",
    "UBER": "Uber Technologies, Inc.",
    "MCD": "McDonald's Corporation",
    "LIN": "Linde plc",
    "SHW": "Sherwin-Williams Company (The)",
    "CSCO": "Cisco Systems, Inc.",
    "T": "AT&T Inc.",
    "VLO": "Valero Energy Corporation",
    "TMO": "Thermo Fisher Scientific Inc",
    "SLB": "SLB Limited",
    "IBM": "International Business Machines",
    "BRK-B": "Berkshire Hathaway Inc. New",
    "JNJ": "Johnson & Johnson",
    "CAT": "Caterpillar, Inc.",
    "XOM": "Exxon Mobil Corporation",
    "CEG": "Constellation Energy Corporatio",
    "ABBV": "AbbVie Inc.",
    "HON": "Honeywell International Inc.",
    "D": "Dominion Energy, Inc.",
    "C": "Citigroup, Inc.",
    "NKE": "Nike, Inc.",
    "ETN": "Eaton Corporation, PLC",
    "KMI": "Kinder Morgan, Inc.",
    "META": "Meta Platforms, Inc.",
    "ED": "Consolidated Edison, Inc.",
    "ORCL": "Oracle Corporation",
    "SRE": "DBA Sempra",
    "AMGN": "Amgen Inc.",
}

def _screen_tickers(tickers: list, iv_rank_threshold: float, rsi_threshold: float, time_frame: str) -> list:
    """
    Internal helper to screen a list of tickers.
    """
    try:
        import pandas_ta as ta
    except ImportError as e:
        raise ImportError("The 'pandas_ta' library is required for the screener. Please install it with 'pip install pandas_ta'.") from e

    # Map time_frame to yfinance interval and resample rule
    yf_interval = "1d"
    resample_rule = None
    is_intraday = False

    # Default period
    period = "1y"

    if time_frame == "49m":
        yf_interval = "5m"
        resample_rule = "49min"
        is_intraday = True
        period = "1mo"
    elif time_frame == "98m":
        yf_interval = "5m"
        resample_rule = "98min"
        is_intraday = True
        period = "1mo"
    elif time_frame == "196m":
        yf_interval = "5m"
        resample_rule = "196min"
        is_intraday = True
        period = "1mo"
    elif time_frame == "1wk":
        yf_interval = "1wk"
        period = "2y" # Need more history for SMA50 on weekly
        is_intraday = False
    elif time_frame == "1mo":
        yf_interval = "1mo"
        period = "5y" # Need more history for SMA50 on monthly
        is_intraday = False

    # Batch download result container
    batch_data = None

    # If daily, try batch download first (avoid for new multi-year/weekly intervals to be safe, or just allow it)
    # yfinance batch download is usually fine for daily/weekly.
    if not is_intraday and tickers:
        try:
            # group_by='ticker' ensures we get a MultiIndex with Ticker as level 0
            # auto_adjust=True to suppress warning
            batch_data = yf.download(tickers, period=period, interval=yf_interval, group_by='ticker', threads=True, progress=False, auto_adjust=True)
        except Exception:
            batch_data = None

    def process_symbol(symbol):
        try:
            df = pd.DataFrame()

            # Fetch Data
            # If batch data exists and has this symbol, use it
            if batch_data is not None and symbol in batch_data.columns.levels[0]:
                df = batch_data[symbol].copy()
            else:
                # Sequential fetch (Intraday or Batch Fallback)
                # auto_adjust=False for intraday to prevent KeyError(Timestamp) bug
                # Use dedicated thread for this call via executor
                df = yf.download(symbol, period=period, interval=yf_interval, progress=False, auto_adjust=not is_intraday)

            # Clean NaNs
            df = df.dropna(how='all')

            if df.empty:
                return None

            # Flatten multi-index columns if present (yfinance update)
            if isinstance(df.columns, pd.MultiIndex):
                try:
                    df.columns = df.columns.get_level_values(0)
                except Exception:
                    pass

            # Calculate % Change before resampling
            pct_change_1d = None
            pct_change_1w = None

            try:
                if is_intraday:
                    # Logic for Intraday Data
                    unique_dates = sorted(list(set(df.index.date)))

                    if len(unique_dates) > 1:
                        # Find the last bar of the previous trading day
                        prev_date = unique_dates[-2]
                        # Filter for prev date
                        prev_day_df = df[df.index.date == prev_date]
                        if not prev_day_df.empty:
                            prev_close = float(prev_day_df['Close'].iloc[-1])
                            curr_close = float(df['Close'].iloc[-1])
                            pct_change_1d = ((curr_close - prev_close) / prev_close) * 100

                    # 1W Change: Approx 5 trading days ago
                    if len(unique_dates) > 5:
                         week_ago_date = unique_dates[-6] # 5 days ago approx
                         week_df = df[df.index.date == week_ago_date]
                         if not week_df.empty:
                             week_close = float(week_df['Close'].iloc[-1])
                             curr_close = float(df['Close'].iloc[-1])
                             pct_change_1w = ((curr_close - week_close) / week_close) * 100
                else:
                    # Logic for Daily/Weekly/Monthly Data
                    # 1D Change: Last bar vs Previous bar
                    if len(df) >= 2:
                        prev_close = float(df['Close'].iloc[-2])
                        curr_close = float(df['Close'].iloc[-1])
                        pct_change_1d = ((curr_close - prev_close) / prev_close) * 100

                    # 1W Change: Look back 5 bars if daily, else relative
                    if yf_interval == "1d":
                        if len(df) >= 6:
                            week_close = float(df['Close'].iloc[-6])
                            curr_close = float(df['Close'].iloc[-1])
                            pct_change_1w = ((curr_close - week_close) / week_close) * 100
                    elif yf_interval == "1wk":
                         # For weekly, pct_change_1d is essentially 1W change
                         # pct_change_1w (meaning a longer lookback) could be 1 month?
                         # Let's keep logic simple: 1W change for weekly IS the 1D change
                         # But to fill the UI column "1W %", we might copy it?
                         # Let's leave pct_change_1w as None or try 4 weeks back?
                         if len(df) >= 5:
                             month_close = float(df['Close'].iloc[-5])
                             curr_close = float(df['Close'].iloc[-1])
                             pct_change_1w = ((curr_close - month_close) / month_close) * 100
                    elif yf_interval == "1mo":
                        # For monthly, pct_change_1d is 1 Month change
                        pass
            except Exception:
                pass

            # Resample if needed
            if resample_rule:
                agg_dict = {
                    'Open': 'first',
                    'High': 'max',
                    'Low': 'min',
                    'Close': 'last',
                    'Volume': 'sum'
                }
                agg_dict = {k: v for k, v in agg_dict.items() if k in df.columns}

                df = df.resample(resample_rule).agg(agg_dict)
                df = df.dropna()

            # 3. Calculate Indicators
            # Check length for SMA 50
            if len(df) < 50:
                # Can't calculate SMA 50
                return None

            rsi_series = ta.rsi(df['Close'], length=14)
            if rsi_series is None:
                return None
            df['RSI'] = rsi_series

            sma_series = ta.sma(df['Close'], length=50)
            if sma_series is None:
                return None
            df['SMA_50'] = sma_series

            atr_series = ta.atr(df['High'], df['Low'], df['Close'], length=14)
            current_atr = atr_series.iloc[-1] if atr_series is not None and not atr_series.empty else 0.0

            current_price = float(df['Close'].iloc[-1])
            current_rsi = float(df['RSI'].iloc[-1])
            current_sma = float(df['SMA_50'].iloc[-1])

            # Fetch PE Ratio (Separate blocking call if not cached, risky inside thread but better than sequential)
            pe_ratio = "N/A"
            try:
                t = yf.Ticker(symbol)
                info = t.info
                if info and 'trailingPE' in info and info['trailingPE'] is not None:
                    pe_ratio = f"{info['trailingPE']:.2f}"
            except Exception:
                pass

            # 4. Apply Rules
            trend = "BULLISH" if current_price > current_sma else "BEARISH"
            signal = "WAIT"
            is_green = False

            if trend == "BULLISH":
                if 30 <= current_rsi <= rsi_threshold:
                    signal = "🟢 GREEN LIGHT (Buy Dip)"
                    is_green = True
                elif current_rsi > 70:
                    signal = "🔴 OVERBOUGHT"
                elif current_rsi < 30:
                    signal = "🔵 OVERSOLD"
            else:
                # Bearish Trend
                if current_rsi < 30:
                    signal = "🔵 OVERSOLD (Bearish)"
                elif current_rsi > 70:
                    signal = "🔴 OVERBOUGHT (Bearish)"

            # Use TICKER_NAMES if available
            company_name = TICKER_NAMES.get(symbol, symbol)

            return {
                "ticker": symbol,
                "company_name": company_name,
                "price": current_price,
                "pct_change_1d": pct_change_1d,
                "pct_change_1w": pct_change_1w,
                "rsi": current_rsi,
                "sma_50": current_sma,
                "trend": trend,
                "signal": signal,
                "is_green": is_green,
                "iv_rank": "N/A*",
                "atr": current_atr,
                "pe_ratio": pe_ratio
            }

        except Exception:
            return None

    results = []

    # Use ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_symbol = {executor.submit(process_symbol, sym): sym for sym in tickers}
        for future in as_completed(future_to_symbol):
            try:
                data = future.result()
                if data:
                    results.append(data)
            except Exception:
                pass

    return results

def screen_market(iv_rank_threshold: float = 30.0, rsi_threshold: float = 50.0, time_frame: str = "1d") -> dict:
    """
    Screens the market for stocks grouped by sector.
    Returns:
        Dict[str, List[dict]]: Keys are 'Sector Name (Ticker)', Values are lists of ticker results.
    """
    all_tickers = []
    for t_list in SECTOR_COMPONENTS.values():
        all_tickers.extend(t_list)

    flat_results = _screen_tickers(list(set(all_tickers)), iv_rank_threshold, rsi_threshold, time_frame)

    # Index results by ticker for easy lookup
    result_map = {r['ticker']: r for r in flat_results}

    grouped_results = {}

    for sector_code, sector_name in SECTOR_NAMES.items():
        if sector_code not in SECTOR_COMPONENTS:
            continue

        display_name = f"{sector_name} ({sector_code})"
        components = SECTOR_COMPONENTS[sector_code]

        sector_rows = []
        for t in components:
            if t in result_map:
                sector_rows.append(result_map[t])

        if sector_rows:
            grouped_results[display_name] = sector_rows

    return grouped_results

def screen_sectors(iv_rank_threshold: float = 30.0, rsi_threshold: float = 50.0, time_frame: str = "1d") -> list:
    """
    Screens specific sectorial indices.
    """
    sectors = list(SECTOR_NAMES.keys())
    results = _screen_tickers(sectors, iv_rank_threshold, rsi_threshold, time_frame)

    # Enrich with full name
    for r in results:
        code = r['ticker']
        if code in SECTOR_NAMES:
            r['name'] = SECTOR_NAMES[code]
            r['company_name'] = SECTOR_NAMES[code]

    return results

def _prepare_data_for_ticker(ticker, data_source, time_frame, period, yf_interval, resample_rule, is_intraday):
    """Helper to prepare DataFrame for a single ticker."""
    import pandas as pd
    import yfinance as yf

    df = pd.DataFrame()

    # Extract from batch if available
    if data_source is not None:
        if isinstance(data_source.columns, pd.MultiIndex):
            try:
                 # Check Level 1 (standard) or Level 0 (group_by='ticker')
                if ticker in data_source.columns.get_level_values(1):
                    df = data_source.xs(ticker, axis=1, level=1).copy()
                elif ticker in data_source.columns.get_level_values(0):
                    df = data_source.xs(ticker, axis=1, level=0).copy()
            except Exception:
                pass
        else:
             df = data_source.copy()

    # If empty, sequential fetch
    if df.empty:
         try:
            df = yf.download(ticker, period=period, interval=yf_interval, progress=False, auto_adjust=not is_intraday)
         except Exception:
            pass

    # Clean NaNs
    df = df.dropna(how='all')
    if df.empty:
        return None

    # Flatten if needed
    if isinstance(df.columns, pd.MultiIndex):
        try:
            df.columns = df.columns.get_level_values(0)
        except Exception:
            pass

    # Resample if needed
    if resample_rule:
        agg_dict = {'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}
        agg_dict = {k: v for k, v in agg_dict.items() if k in df.columns}
        try:
            df = df.resample(resample_rule).agg(agg_dict)
            df = df.dropna()
        except Exception:
            pass

    return df

def screen_turtle_setups(ticker_list: list = None, time_frame: str = "1d") -> list:
    """
    Screens for Turtle Trading Setups (20-Day Breakouts).
    Supports multiple timeframes.
    """
    import yfinance as yf
    import pandas_ta as ta
    import pandas as pd

    if ticker_list is None:
        ticker_list = [
            "SPY", "QQQ", "IWM", "GLD", "SLV", "USO", "TLT", # ETFs
            "AAPL", "MSFT", "NVDA", "AMD", "TSLA", "META", "GOOGL", "AMZN", # Tech
            "JPM", "BAC", "XOM", "CVX", "PFE", "KO", "DIS" # Blue Chips
        ]
        if "WATCH" in SECTOR_COMPONENTS:
             ticker_list = list(set(ticker_list + SECTOR_COMPONENTS["WATCH"]))

    # Additional names for ETFs not in TICKER_NAMES
    ETF_NAMES = {
        "SPY": "SPDR S&P 500 ETF Trust",
        "QQQ": "Invesco QQQ Trust",
        "IWM": "iShares Russell 2000 ETF",
        "GLD": "SPDR Gold Shares",
        "SLV": "iShares Silver Trust",
        "USO": "United States Oil Fund, LP",
        "TLT": "iShares 20+ Year Treasury Bond ETF",
    }

    # Timeframe logic
    yf_interval = "1d"
    resample_rule = None
    is_intraday = False
    period = "3mo"

    if time_frame == "49m":
        yf_interval = "5m"
        resample_rule = "49min"
        is_intraday = True
        period = "1mo"
    elif time_frame == "98m":
        yf_interval = "5m"
        resample_rule = "98min"
        is_intraday = True
        period = "1mo"
    elif time_frame == "196m":
        yf_interval = "5m"
        resample_rule = "196min"
        is_intraday = True
        period = "1mo"
    elif time_frame == "1wk":
        yf_interval = "1wk"
        period = "2y"
    elif time_frame == "1mo":
        yf_interval = "1mo"
        period = "5y"

    results = []

    # Bulk download if not intraday
    data = None
    if not is_intraday:
        try:
            data = yf.download(ticker_list, period=period, interval=yf_interval, progress=False)
        except Exception:
            pass

    for ticker in ticker_list:
        try:
            df = _prepare_data_for_ticker(ticker, data, time_frame, period, yf_interval, resample_rule, is_intraday)

            if df is None or len(df) < 21:
                continue

            # --- TURTLE CALCULATIONS ---
            # 1. Donchian Channels (20-day High/Low)
            df['20_High'] = df['High'].rolling(window=20).max().shift(1)
            df['20_Low'] = df['Low'].rolling(window=20).min().shift(1)

            # 2. ATR (Volatility 'N')
            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=20)

            curr_close = float(df['Close'].iloc[-1])

            if pd.isna(df['20_High'].iloc[-1]) or pd.isna(df['ATR'].iloc[-1]):
                continue

            prev_high = float(df['20_High'].iloc[-1])
            prev_low = float(df['20_Low'].iloc[-1])
            atr = float(df['ATR'].iloc[-1])

            signal = "WAIT"
            buy_price = 0.0
            stop_loss = 0.0
            target = 0.0

            dist_to_breakout_high = (curr_close - prev_high) / prev_high

            # Buy Breakout
            if curr_close > prev_high:
                signal = "🚀 BREAKOUT (BUY)"
                buy_price = curr_close
                stop_loss = buy_price - (2 * atr)
                target = buy_price + (4 * atr)

            # Sell Breakout (Short)
            elif curr_close < prev_low:
                signal = "📉 BREAKDOWN (SELL)"
                buy_price = curr_close
                stop_loss = buy_price + (2 * atr) # Stop above entry for short
                target = buy_price - (4 * atr)    # Target below entry

            # Near High
            elif -0.02 <= dist_to_breakout_high <= 0:
                signal = "👀 WATCH (Near High)"
                buy_price = prev_high
                stop_loss = prev_high - (2 * atr)
                target = prev_high + (4 * atr)

            if signal != "WAIT":
                company_name = TICKER_NAMES.get(ticker, ETF_NAMES.get(ticker, ticker))
                results.append({
                    "ticker": ticker,
                    "company_name": company_name,
                    "price": curr_close,
                    "signal": signal,
                    "breakout_level": prev_high if "SELL" not in signal else prev_low,
                    "stop_loss": stop_loss,
                    "target": target,
                    "atr": atr,
                    "risk_per_share": abs(buy_price - stop_loss)
                })

        except Exception:
            continue

    return results

def screen_5_13_setups(ticker_list: list = None, time_frame: str = "1d") -> list:
    """
    Screens for 5/13 and 5/21 EMA Crossovers (Momentum Breakouts).
    """
    try:
        import pandas_ta as ta
    except ImportError:
        return []

    import yfinance as yf
    import pandas as pd

    if ticker_list is None:
        # Default liquid list + Crypto proxies usually traded with this system
        ticker_list = [
            "SPY", "QQQ", "IWM", "GLD", "SLV", "BITO", "COIN", "MSTR", # Crypto-adj
            "AAPL", "MSFT", "NVDA", "AMD", "TSLA", "META", "GOOGL", "AMZN",
            "NFLX", "JPM", "BAC", "XOM", "CVX", "PFE", "KO", "DIS"
        ]
        if "WATCH" in SECTOR_COMPONENTS:
             ticker_list = list(set(ticker_list + SECTOR_COMPONENTS["WATCH"]))

    # Additional names for ETFs not in TICKER_NAMES
    ETF_NAMES = {
        "SPY": "SPDR S&P 500 ETF Trust",
        "QQQ": "Invesco QQQ Trust",
        "IWM": "iShares Russell 2000 ETF",
        "GLD": "SPDR Gold Shares",
        "SLV": "iShares Silver Trust",
        "USO": "United States Oil Fund, LP",
        "TLT": "iShares 20+ Year Treasury Bond ETF",
        "BITO": "ProShares Bitcoin Strategy ETF",
    }

    # Timeframe logic
    yf_interval = "1d"
    resample_rule = None
    is_intraday = False
    period = "3mo"

    if time_frame == "49m":
        yf_interval = "5m"
        resample_rule = "49min"
        is_intraday = True
        period = "1mo"
    elif time_frame == "98m":
        yf_interval = "5m"
        resample_rule = "98min"
        is_intraday = True
        period = "1mo"
    elif time_frame == "196m":
        yf_interval = "5m"
        resample_rule = "196min"
        is_intraday = True
        period = "1mo"
    elif time_frame == "1wk":
        yf_interval = "1wk"
        period = "2y"
    elif time_frame == "1mo":
        yf_interval = "1mo"
        period = "5y"

    results = []

    # Bulk download if not intraday
    data = None
    if not is_intraday:
        try:
            data = yf.download(ticker_list, period=period, interval=yf_interval, progress=False)
        except Exception:
            pass

    for ticker in ticker_list:
        try:
            df = _prepare_data_for_ticker(ticker, data, time_frame, period, yf_interval, resample_rule, is_intraday)

            if df is None or len(df) < 22: # Need 21 for EMA 21
                continue

            # --- EMA CALCULATIONS ---
            df['EMA_5'] = ta.ema(df['Close'], length=5)
            df['EMA_13'] = ta.ema(df['Close'], length=13)
            df['EMA_21'] = ta.ema(df['Close'], length=21)

            # Current & Previous values
            curr_5 = df['EMA_5'].iloc[-1]
            curr_13 = df['EMA_13'].iloc[-1]
            curr_21 = df['EMA_21'].iloc[-1]

            prev_5 = df['EMA_5'].iloc[-2]
            prev_13 = df['EMA_13'].iloc[-2]
            prev_21 = df['EMA_21'].iloc[-2]

            curr_close = float(df['Close'].iloc[-1])

            signal = "WAIT"
            status_color = "gray"
            stop_loss = 0.0
            ema_slow = curr_13 # Default to 13

            # Logic 5/13:
            # 1. Fresh Breakout (Crossed TODAY)
            if curr_5 > curr_13 and prev_5 <= prev_13:
                signal = "🚀 FRESH 5/13 BREAKOUT"
                status_color = "green"
                ema_slow = curr_13
                stop_loss = curr_13 * 0.99

            # Logic 5/21:
            elif curr_5 > curr_21 and prev_5 <= prev_21:
                signal = "🚀 FRESH 5/21 BREAKOUT"
                status_color = "green"
                ema_slow = curr_21
                stop_loss = curr_21 * 0.99

            # 2. Trending (Held for >1 day)
            elif curr_5 > curr_13:
                # Check how far extended?
                dist = (curr_close - curr_13) / curr_13
                if dist < 0.01: # Price is pulling back to 13 EMA (Buy Support)
                    signal = "✅ 5/13 TREND (Buy Support)"
                    status_color = "blue"
                else:
                    signal = "📈 5/13 TRENDING"
                    status_color = "blue"
                ema_slow = curr_13
                stop_loss = curr_13 * 0.99

            elif curr_5 > curr_21:
                 signal = "📈 5/21 TRENDING"
                 status_color = "blue"
                 ema_slow = curr_21
                 stop_loss = curr_21 * 0.99

            # 3. Bearish Cross (Sell)
            if curr_5 < curr_13 and prev_5 >= prev_13:
                signal = "❌ 5/13 DUMP (Sell Signal)"
                status_color = "red"
                ema_slow = curr_13
                stop_loss = curr_13 * 1.01 # Stop above

            elif curr_5 < curr_21 and prev_5 >= prev_21:
                signal = "❌ 5/21 DUMP (Sell Signal)"
                status_color = "red"
                ema_slow = curr_21
                stop_loss = curr_21 * 1.01

            if signal != "WAIT":
                company_name = TICKER_NAMES.get(ticker, ETF_NAMES.get(ticker, ticker))
                results.append({
                    "ticker": ticker,
                    "company_name": company_name,
                    "price": curr_close,
                    "signal": signal,
                    "color": status_color,
                    "ema_5": curr_5,
                    "ema_13": curr_13,
                    "ema_21": curr_21,
                    # Stop Loss usually strictly below the slow EMA line
                    "stop_loss": stop_loss,
                    "diff_pct": ((curr_5 - ema_slow)/ema_slow)*100
                })

        except Exception:
            continue

    # Sort by "Freshness" (Breakouts first)
    results.sort(key=lambda x: 0 if "FRESH" in x['signal'] else 1)
    return results
