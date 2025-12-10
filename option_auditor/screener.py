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
    "RELIANCE": "Reliance Industries Limited",
    "TCS": "Tata Consultancy Services Limited",
    "HDFCBANK": "HDFC Bank Limited",
    "BHARTIARTL": "Bharti Airtel Limited",
    "ICICIBANK": "ICICI Bank Limited",
    "INFY": "Infosys Limited",
    "HINDUNILVR": "Hindustan Unilever Limited",
    "SBIN": "State Bank of India",
    "ITC": "ITC Limited",
    "LTIM": "LTIMindtree Limited",
    "LT": "Larsen & Toubro Limited",
    "HCLTECH": "HCL Technologies Limited",
    "BAJFINANCE": "Bajaj Finance Limited",
    "AXISBANK": "Axis Bank Limited",
    "MARUTI": "Maruti Suzuki India Limited",
    "ULTRACEMCO": "UltraTech Cement Limited",
    "SUNPHARMA": "Sun Pharmaceutical Industries Limited",
    "M&M": "Mahindra & Mahindra Limited",
    "TITAN": "Titan Company Limited",
    "KOTAKBANK": "Kotak Mahindra Bank Limited",
    "ADANIENT": "Adani Enterprises Limited",
    "TATAMOTORS": "Tata Motors Limited",
    "NTPC": "NTPC Limited",
    "TATASTEEL": "Tata Steel Limited",
    "POWERGRID": "Power Grid Corporation of India Limited",
    "ASIANPAINT": "Asian Paints Limited",
    "JSWSTEEL": "JSW Steel Limited",
    "BAJAJFINSV": "Bajaj Finserv Limited",
    "NESTLEIND": "Nestlé India Limited",
    "GRASIM": "Grasim Industries Limited",
    "ONGC": "Oil and Natural Gas Corporation Limited",
    "TECHM": "Tech Mahindra Limited",
    "HINDALCO": "Hindalco Industries Limited",
    "ADANIPORTS": "Adani Ports and Special Economic Zone Limited",
    "CIPLA": "Cipla Limited",
    "WIPRO": "Wipro Limited",
    "SBILIFE": "SBI Life Insurance Company Limited",
    "DRREDDY": "Dr. Reddy's Laboratories Limited",
    "BRITANNIA": "Britannia Industries Limited",
    "TATACONSUM": "Tata Consumer Products Limited",
    "COALINDIA": "Coal India Limited",
    "APOLLOHOSP": "Apollo Hospitals Enterprise Limited",
    "EICHERMOT": "Eicher Motors Limited",
    "INDUSINDBK": "IndusInd Bank Limited",
    "DIVISLAB": "Divi's Laboratories Limited",
    "BAJAJ-AUTO": "Bajaj Auto Limited",
    "HDFCLIFE": "HDFC Life Insurance Company Limited",
    "HEROMOTOCO": "Hero MotoCorp Limited",
    "BEL": "Bharat Electronics Limited",
    "SHRIRAMFIN": "Shriram Finance Limited",
    "LICI": "Life Insurance Corporation of India",
    "HAL": "Hindustan Aeronautics Limited",
    "ADANIPOWER": "Adani Power Limited",
    "DMART": "Avenue Supermarts Limited",
    "VBL": "Varun Beverages Limited",
    "JIOFIN": "Jio Financial Services Limited",
    "SIEMENS": "Siemens Limited",
    "TRENT": "Trent Limited",
    "ZOMATO": "Zomato Limited",
    "ADANIGREEN": "Adani Green Energy Limited",
    "IOC": "Indian Oil Corporation Limited",
    "DLF": "DLF Limited",
    "VEDL": "Vedanta Limited",
    "BANKBARODA": "Bank of Baroda",
    "GAIL": "GAIL (India) Limited",
    "AMBUJACEM": "Ambuja Cements Limited",
    "CHOLAFIN": "Cholamandalam Investment and Finance Company Limited",
    "HAVELLS": "Havells India Limited",
    "ABB": "ABB India Limited",
    "PIDILITIND": "Pidilite Industries Limited",
    "GODREJCP": "Godrej Consumer Products Limited",
    "DABUR": "Dabur India Limited",
    "SHREECEM": "Shree Cement Limited",
    "PNB": "Punjab National Bank",
    "BPCL": "Bharat Petroleum Corporation Limited",
    "SBICARD": "SBI Cards and Payment Services Limited",
    "SRF": "SRF Limited",
    "MOTHERSON": "Samvardhana Motherson International Limited",
    "ICICIPRULI": "ICICI Prudential Life Insurance Company Limited",
    "MARICO": "Marico Limited",
    "BERGEPAINT": "Berger Paints India Limited",
    "ICICIGI": "ICICI Lombard General Insurance Company Limited",
    "TVSMOTOR": "TVS Motor Company Limited",
    "NAUKRI": "Info Edge (India) Limited",
    "LODHA": "Macrotech Developers Limited",
    "BOSCHLTD": "Bosch Limited",
    "INDIGO": "InterGlobe Aviation Limited",
    "CANBK": "Canara Bank",
    "UNITDSPR": "United Spirits Limited",
    "TORNTPHARM": "Torrent Pharmaceuticals Limited",
    "PIIND": "PI Industries Limited",
    "UPL": "UPL Limited",
    "JINDALSTEL": "Jindal Steel & Power Limited",
    "ALKEM": "Alkem Laboratories Limited",
    "ZYDUSLIFE": "Zydus Lifesciences Limited",
    "COLPAL": "Colgate-Palmolive (India) Limited",
    "BAJAJHLDNG": "Bajaj Holdings & Investment Limited",
    "TATAPOWER": "The Tata Power Company Limited",
    "IRCTC": "Indian Railway Catering and Tourism Corporation Limited",
    "MUTHOOTFIN": "Muthoot Finance Limited",
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

UK_EURO_TICKERS = [
    # Top 50 FTSE (UK)
    "AZN.L", "SHEL.L", "HSBA.L", "ULVR.L", "BP.L", "RIO.L", "REL.L", "GSK.L", "DGE.L", "LSEG.L", "BATS.L", "GLEN.L", "BA.L", "CNA.L", "NG.L", "LLOY.L", "RR.L", "BARC.L", "CPG.L", "NWG.L", "RKT.L", "VOD.L", "AAL.L", "SGE.L", "HLN.L", "EXR.L", "TSCO.L", "SSE.L", "MNG.L", "ADM.L", "III.L", "ANTO.L", "SPX.L", "STAN.L", "IMB.L", "WTB.L", "SVT.L", "AUTO.L", "SN.L", "CRDA.L", "WPP.L", "SMIN.L", "DCC.L", "AV.L", "LGEN.L", "KGF.L", "SBRY.L", "MKS.L", "LAND.L", "PSON.L",
    # Liquid UK Mid-Caps
    "JD.L", "IAG.L", "EZJ.L", "AML.L", "IDS.L", "DLG.L", "ITM.L", "QQ.L", "GRG.L", "VTY.L", "BTRW.L", "BOO.L", "ASOS.L", "HBR.L", "ENOG.L", "TLW.L", "CWR.L", "GNC.L", "THG.L", "CURY.L", "DOM.L", "SFOR.L", "PETS.L", "MRO.L", "INVP.L", "OCDO.L", "IGG.L", "CMC.L", "PLUS.L", "EMG.L", "HWDN.L", "COST.L", "BEZ.L", "SGRO.L", "PSN.L", "TW.L", "BYG.L", "SAFE.L", "UTG.L", "BBOX.L", "MANG.L", "TPK.L", "HIK.L", "SRO.L", "FRES.L", "KAP.L", "WKP.L", "JMAT.L", "RS1.L", "PNN.L",
    # Top 50 Euro
    "ASML.AS", "MC.PA", "SAP.DE", "RMS.PA", "TTE.PA", "SIE.DE", "CDI.PA", "AIR.PA", "SAN.MC", "IBE.MC", "OR.PA", "ALV.DE", "SU.PA", "EL.PA", "AI.PA", "BNP.PA", "DTE.DE", "ENEL.MI", "DG.PA", "BBVA.MC", "CS.PA", "BAS.DE", "ADS.DE", "MUV2.DE", "IFX.DE", "SAF.PA", "ENI.MI", "INGA.AS", "ISP.MI", "KER.PA", "STLAP.PA", "AD.AS", "VOW3.DE", "BMW.DE", "MBG.DE", "BAYN.DE", "DB1.DE", "BN.PA", "RI.PA", "CRH.L", "G.MI", "PHIA.AS", "HEIA.AS", "NOKIA.HE", "VIV.PA", "ORA.PA", "KNEBV.HE", "UMG.AS", "HO.PA", "ABI.BR"
]

def get_uk_euro_tickers():
    """Returns normalized UK/Euro tickers list."""
    return list(set(UK_EURO_TICKERS))

INDIAN_TICKERS = [
    # Nifty 50
    "RELIANCE", "TCS", "HDFCBANK", "BHARTIARTL", "ICICIBANK", "INFY", "HINDUNILVR", "SBIN", "ITC", "LTIM", "LT", "HCLTECH", "BAJFINANCE", "AXISBANK", "MARUTI", "ULTRACEMCO", "SUNPHARMA", "M&M", "TITAN", "KOTAKBANK", "ADANIENT", "TATAMOTORS", "NTPC", "TATASTEEL", "POWERGRID", "ASIANPAINT", "JSWSTEEL", "BAJAJFINSV", "NESTLEIND", "GRASIM", "ONGC", "TECHM", "HINDALCO", "ADANIPORTS", "CIPLA", "WIPRO", "SBILIFE", "DRREDDY", "BRITANNIA", "TATACONSUM", "COALINDIA", "APOLLOHOSP", "EICHERMOT", "INDUSINDBK", "DIVISLAB", "BAJAJ-AUTO", "HDFCLIFE", "HEROMOTOCO", "BEL", "SHRIRAMFIN",
    # Nifty Next 50
    "LICI", "HAL", "ADANIPOWER", "DMART", "VBL", "JIOFIN", "SIEMENS", "TRENT", "ZOMATO", "ADANIGREEN", "IOC", "DLF", "VEDL", "BANKBARODA", "GAIL", "AMBUJACEM", "CHOLAFIN", "HAVELLS", "ABB", "PIDILITIND", "GODREJCP", "DABUR", "SHREECEM", "PNB", "BPCL", "SBICARD", "SRF", "MOTHERSON", "ICICIPRULI", "MARICO", "BERGEPAINT", "ICICIGI", "TVSMOTOR", "NAUKRI", "LODHA", "BOSCHLTD", "INDIGO", "CANBK", "UNITDSPR", "TORNTPHARM", "PIIND", "UPL", "JINDALSTEL", "ALKEM", "ZYDUSLIFE", "COLPAL", "BAJAJHLDNG", "TATAPOWER", "IRCTC", "MUTHOOTFIN"
]

def get_indian_tickers():
    """Returns normalized Indian tickers list."""
    # Append .NS for NSE
    return [t + ".NS" for t in INDIAN_TICKERS]

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

            # --- TURTLE & DARVAS CALCULATIONS ---
            # 1. Donchian Channels (20-day High/Low)
            df['20_High'] = df['High'].rolling(window=20).max().shift(1)
            df['20_Low'] = df['Low'].rolling(window=20).min().shift(1)

            # Darvas / 10-day Box for faster breakouts
            df['10_High'] = df['High'].rolling(window=10).max().shift(1)
            df['10_Low'] = df['Low'].rolling(window=10).min().shift(1)

            # 2. ATR (Volatility 'N')
            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=20)

            curr_close = float(df['Close'].iloc[-1])

            # Calculate % Change
            pct_change_1d = None
            if len(df) >= 2:
                try:
                    prev_close_px = float(df['Close'].iloc[-2])
                    pct_change_1d = ((curr_close - prev_close_px) / prev_close_px) * 100
                except Exception as e:
                    print(f"Error calc % change for {ticker}: {e}")

            if pd.isna(df['20_High'].iloc[-1]) or pd.isna(df['ATR'].iloc[-1]):
                continue

            prev_high = float(df['20_High'].iloc[-1])
            prev_low = float(df['20_Low'].iloc[-1])
            atr = float(df['ATR'].iloc[-1])

            # 10-day values
            prev_high_10 = float(df['10_High'].iloc[-1]) if not pd.isna(df['10_High'].iloc[-1]) else prev_high
            prev_low_10 = float(df['10_Low'].iloc[-1]) if not pd.isna(df['10_Low'].iloc[-1]) else prev_low

            signal = "WAIT"
            buy_price = 0.0
            stop_loss = 0.0
            target = 0.0

            dist_to_breakout_high = (curr_close - prev_high) / prev_high

            # Buy Breakout (Turtle 20-Day)
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

            # Near High (Turtle 20-Day only for now)
            elif -0.02 <= dist_to_breakout_high <= 0:
                signal = "👀 WATCH (Near High)"
                buy_price = prev_high
                stop_loss = prev_high - (2 * atr)
                target = prev_high + (4 * atr)

            if signal != "WAIT":
                # Handle cases where ticker has suffix (e.g. .L or .NS) but key in TICKER_NAMES does not
                base_ticker = ticker.split('.')[0]
                company_name = TICKER_NAMES.get(ticker, TICKER_NAMES.get(base_ticker, ETF_NAMES.get(ticker, ticker)))
                results.append({
                    "ticker": ticker,
                    "company_name": company_name,
                    "price": curr_close,
                    "pct_change_1d": pct_change_1d,
                    "signal": signal,
                    "breakout_level": prev_high,
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

            # Calculate % Change
            pct_change_1d = None
            if len(df) >= 2:
                try:
                    prev_close_px = float(df['Close'].iloc[-2])
                    pct_change_1d = ((curr_close - prev_close_px) / prev_close_px) * 100
                except Exception:
                    pass

            # Logic Priority:
            # 1. Fresh 5/21 Breakout (Stronger/Rarer)
            # 2. Fresh 5/13 Breakout
            # 3. Trending 5/21 (Trend strength)
            # 4. Trending 5/13

            # 1. Fresh Breakouts
            if curr_5 > curr_21 and prev_5 <= prev_21:
                signal = "🚀 FRESH 5/21 BREAKOUT"
                status_color = "green"
                ema_slow = curr_21
                stop_loss = curr_21 * 0.99

            elif curr_5 > curr_13 and prev_5 <= prev_13:
                signal = "🚀 FRESH 5/13 BREAKOUT"
                status_color = "green"
                ema_slow = curr_13
                stop_loss = curr_13 * 0.99

            # 2. Trending (Held for >1 day)
            elif curr_5 > curr_21:
                 signal = "📈 5/21 TRENDING"
                 status_color = "blue"
                 ema_slow = curr_21
                 stop_loss = curr_21 * 0.99

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
                # Handle cases where ticker has suffix (e.g. .L or .NS) but key in TICKER_NAMES does not
                base_ticker = ticker.split('.')[0]
                company_name = TICKER_NAMES.get(ticker, TICKER_NAMES.get(base_ticker, ETF_NAMES.get(ticker, ticker)))
                results.append({
                    "ticker": ticker,
                    "company_name": company_name,
                    "price": curr_close,
                    "pct_change_1d": pct_change_1d,
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

def screen_darvas_box(ticker_list: list = None, time_frame: str = "1d") -> list:
    """
    Screens for Darvas Box Breakouts.
    Strategy:
    1. Trend: Stock near 52-week High.
    2. Box: Price breaks above a "Ceiling" established by a recent high (3-day non-penetration).
    3. Volume: Spike on breakout.
    """
    import yfinance as yf
    import pandas_ta as ta
    import pandas as pd
    import numpy as np

    if ticker_list is None:
        ticker_list = [
            "SPY", "QQQ", "IWM", "GLD", "SLV", "USO", "TLT", # ETFs
            "AAPL", "MSFT", "NVDA", "AMD", "TSLA", "META", "GOOGL", "AMZN", # Tech
            "JPM", "BAC", "XOM", "CVX", "PFE", "KO", "DIS" # Blue Chips
        ]
        if "WATCH" in SECTOR_COMPONENTS:
             ticker_list = list(set(ticker_list + SECTOR_COMPONENTS["WATCH"]))

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
    period = "1y" # Need longer history for 52-week high

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
            data = yf.download(ticker_list, period=period, interval=yf_interval, progress=False, group_by='ticker', auto_adjust=True)
        except Exception:
            pass

    def _process_darvas(ticker):
        try:
            df = _prepare_data_for_ticker(ticker, data, time_frame, period, yf_interval, resample_rule, is_intraday)

            if df is None or len(df) < 50:
                return None

            curr_close = float(df['Close'].iloc[-1])
            curr_volume = float(df['Volume'].iloc[-1]) if 'Volume' in df.columns else 0

            # 1. 52-Week High Check (Momentum Filter)
            # If intraday, we might not have full 52-week data in `df` (only 1mo).
            # So we rely on the data we have. For proper Darvas, 1y daily is best.
            # If intraday, we assume the user accepts the "local" high as the filter or we skip.
            # Let's use the max of the available data.
            period_high = df['High'].max()
            # If we are within 5% of the high
            if curr_close < period_high * 0.90:
                # Darvas requires new highs. If we are deep in drawdown, ignore.
                # Exception: Early stage breakout from a base might be slightly lower.
                # Strictest rule: Must be making a new high.
                # Let's relax to: Near High (> 90%).
                pass # Just a filter, but we proceed to check boxes

            # 2. Identify Box (Ceiling & Floor)
            # We iterate back to find the most recent valid Box.
            # A valid box has a Ceiling (Top) and a Floor (Bottom).

            # Logic:
            # Find the most recent "Pivot High" (Ceiling).
            # A Top at index T is valid if High[T] >= High[T-3...T-1] AND High[T] >= High[T+1...T+3].

            # Optimization: We only need the last established box.
            # We scan backwards from T-3.

            ceiling = None
            floor = None

            # Convert to numpy for speed
            highs = df['High'].values
            lows = df['Low'].values
            closes = df['Close'].values
            volumes = df['Volume'].values if 'Volume' in df.columns else np.zeros(len(df))

            # Look back window: last 60 bars (approx 3 months)
            lookback = min(len(df), 60)

            # Find potential Tops
            # We iterate backwards
            found_top_idx = -1

            for i in range(len(df) - 4, len(df) - lookback, -1):
                # Check for Pivot High at i
                # Left neighbors (i-3 to i-1)
                if i < 3: break

                # Check if High[i] is >= High[i-3...i-1] AND High[i] >= High[i+1...i+3]
                # Note: i+3 must exist.
                if i + 3 >= len(df): continue

                curr_h = highs[i]
                if (curr_h >= highs[i-1] and curr_h >= highs[i-2] and curr_h >= highs[i-3] and
                    curr_h >= highs[i+1] and curr_h >= highs[i+2] and curr_h >= highs[i+3]):

                    found_top_idx = i
                    ceiling = curr_h
                    break

            if found_top_idx == -1:
                return None # No defined top recently

            # Find Floor (Bottom) AFTER the Top
            # Darvas: "The point where it stops dropping... becomes the bottom"
            # So we look for a Pivot Low in the range (found_top_idx + 1 ... Today)
            # But the pivot low also needs 3 days confirmation.

            found_bot_idx = -1

            for j in range(found_top_idx + 1, len(df) - 3):
                # Check for Pivot Low at j
                # Left neighbors?
                # Actually, Darvas establishes the floor *after* the ceiling.
                # Condition: Low[j] <= Low[j-3...j-1] AND Low[j] <= Low[j+1...j+3]
                # And Low[j] < Ceiling

                if j < 3: continue
                if j + 3 >= len(df): continue

                curr_l = lows[j]
                if curr_l >= ceiling: continue # Bottom must be below top

                if (curr_l <= lows[j-1] and curr_l <= lows[j-2] and curr_l <= lows[j-3] and
                    curr_l <= lows[j+1] and curr_l <= lows[j+2] and curr_l <= lows[j+3]):

                    found_bot_idx = j
                    floor = curr_l
                    # We take the *first* valid bottom after top? Or the lowest?
                    # Darvas boxes are usually defined by the first consolidation range.
                    # Let's assume the first valid pivot low establishes the floor.
                    break

            if floor is None:
                # We have a Top but no confirmed Floor yet.
                # We are likely "In Formation".
                pass

            signal = "WAIT"

            # 3. Check for Breakout
            # If we have a valid Box [Floor, Ceiling]
            if ceiling and floor:
                # Check if we are breaking out NOW (last bar)
                # Breakout: Close > Ceiling
                if closes[-1] > ceiling and closes[-2] <= ceiling:
                     signal = "📦 DARVAS BREAKOUT"

                # Check for Breakdown (Stop Loss)
                elif closes[-1] < floor and closes[-2] >= floor:
                     signal = "📉 BOX BREAKDOWN"

                elif closes[-1] > ceiling:
                     # Already broken out, sustaining high?
                     if (closes[-1] - ceiling) / ceiling < 0.05:
                         signal = "🚀 MOMENTUM (Post-Breakout)"

            elif ceiling and not floor:
                # Setup phase?
                # Price is between Top and (undefined) Bottom.
                pass

            if signal == "WAIT":
                return None

            # 4. Volume Filter (for Breakouts)
            is_valid_volume = True
            if "BREAKOUT" in signal:
                # Volume > 150% of 20-day MA
                vol_ma = np.mean(volumes[-21:-1]) if len(volumes) > 21 else np.mean(volumes)
                if vol_ma > 0 and curr_volume < vol_ma * 1.2: # Relaxed to 1.2x
                    # signal += " (Low Vol)"
                    # Maybe filter it out strictly?
                    # Darvas insisted on volume.
                    is_valid_volume = False

            if not is_valid_volume:
                return None

            # 52-Week High check (Strict for Entry)
            if "BREAKOUT" in signal:
                if curr_close < period_high * 0.95:
                     # Breakout of a box, but far from 52w high?
                     # Might be a recovery box. Darvas preferred ATH.
                     # We label it differently?
                     pass

            # Calculate metrics
            pct_change_1d = None
            if len(df) >= 2:
                 pct_change_1d = ((closes[-1] - closes[-2]) / closes[-2]) * 100

            atr = ta.atr(df['High'], df['Low'], df['Close'], length=14).iloc[-1]

            stop_loss = floor if floor else (ceiling - 2*atr if ceiling else curr_close * 0.95)
            # Target = Breakout + Box Height
            box_height = (ceiling - floor) if (ceiling and floor) else (4 * atr)
            target = ceiling + box_height if ceiling else curr_close * 1.2

            base_ticker = ticker.split('.')[0]
            company_name = TICKER_NAMES.get(ticker, TICKER_NAMES.get(base_ticker, ETF_NAMES.get(ticker, ticker)))

            return {
                "ticker": ticker,
                "company_name": company_name,
                "price": curr_close,
                "pct_change_1d": pct_change_1d,
                "signal": signal,
                "breakout_level": ceiling,
                "floor_level": floor,
                "stop_loss": stop_loss,
                "target_price": target,
                "high_52w": period_high,
                "volume_ratio": (curr_volume / np.mean(volumes[-21:-1])) if len(volumes) > 21 else 1.0
            }

        except Exception as e:
            # print(f"Error processing {ticker}: {e}")
            return None

    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_symbol = {executor.submit(_process_darvas, sym): sym for sym in ticker_list}
        for future in as_completed(future_to_symbol):
            try:
                data = future.result()
                if data:
                    results.append(data)
            except Exception:
                pass

    return results

# -------------------------------------------------------------------------
#  SMC / ICT HELPER FUNCTIONS
# -------------------------------------------------------------------------

def _identify_swings(df: pd.DataFrame, lookback: int = 2) -> pd.DataFrame:
    """
    Identifies fractal Swing Highs and Swing Lows.
    A swing high is a high surrounded by lower highs on both sides.
    """
    df = df.copy()
    # Swing High
    df['Swing_High'] = df['High'][
        (df['High'] > df['High'].shift(1)) &
        (df['High'] > df['High'].shift(-1))
    ]
    # Swing Low
    df['Swing_Low'] = df['Low'][
        (df['Low'] < df['Low'].shift(1)) &
        (df['Low'] < df['Low'].shift(-1))
    ]
    return df

def _detect_fvgs(df: pd.DataFrame) -> list:
    """
    Detects unmitigated Fair Value Gaps (FVGs) in the last 20 candles.
    Returns a list of dicts: {'type': 'bull/bear', 'top': float, 'bottom': float, 'index': datetime}
    """
    fvgs = []
    # Iterate through recent candles (last 50 is enough for active setups)
    # We need index access, so we convert to records or iterate by index
    # Logic:
    # Bearish FVG: Low of candle[i-2] > High of candle[i]. Gap is between them.
    # Bullish FVG: High of candle[i-2] < Low of candle[i]. Gap is between them.

    if len(df) < 3:
        return []

    highs = df['High'].values
    lows = df['Low'].values
    times = df.index

    # Check last 30 candles
    start_idx = max(2, len(df) - 30)

    for i in range(start_idx, len(df)):
        # Bearish FVG (Down move)
        # Candle i (current), i-1 (displacement), i-2 (high anchor)
        # Gap exists if Low[i-2] > High[i]
        if lows[i-2] > highs[i]:
            gap_size = lows[i-2] - highs[i]
            # Filter tiny gaps (noise) - e.g., < 0.02% price
            if gap_size > (highs[i] * 0.0002):
                fvgs.append({
                    "type": "BEARISH",
                    "top": lows[i-2],
                    "bottom": highs[i],
                    "ts": times[i-1] # Timestamp of the big candle
                })

        # Bullish FVG (Up move)
        # Gap exists if High[i-2] < Low[i]
        if highs[i-2] < lows[i]:
            gap_size = lows[i] - highs[i-2]
            if gap_size > (lows[i] * 0.0002):
                fvgs.append({
                    "type": "BULLISH",
                    "top": lows[i],
                    "bottom": highs[i-2],
                    "ts": times[i-1]
                })
    return fvgs

def screen_mms_ote_setups(ticker_list: list = None, time_frame: str = "1h") -> list:
    """
    Screens for ICT Market Maker Models + OTE (Optimal Trade Entry).

    Strategy:
    1.  Bias: Daily Trend.
    2.  Setup:
        -   Price Sweeps a Swing High/Low (Liquidity Raid).
        -   Reverses with DISPLACEMENT (leaving an FVG).
        -   Breaks Structure (MSS).
    3.  Trigger: Price is currently retracing into the OTE Zone (62-79% Fib).
    """
    import pandas as pd
    import numpy as np
    from concurrent.futures import ThreadPoolExecutor, as_completed

    if ticker_list is None:
        # Default to liquid lists + Forex proxies
        ticker_list = ["SPY", "QQQ", "IWM", "GLD", "FXE", "FXY", "MSFT", "AAPL", "NVDA", "TSLA", "AMD", "AMZN", "META", "GOOGL"]

    # For OTE, we usually want Intraday data to see the displacement clearly.
    # 1h (60m) is a good balance for Swing Trading this model.
    yf_interval = "1h"
    period = "60d" # Max 60d for 1h data in yfinance
    is_intraday = True

    # Override for different timeframes
    if time_frame == "15m":
        yf_interval = "15m"
        period = "1mo" # Max 1mo for 15m
    elif time_frame == "1d":
        yf_interval = "1d"
        period = "1y"
        is_intraday = False

    results = []

    def _process_ote(ticker):
        try:
            # 1. Fetch Data
            # We need standard data preparation
            import yfinance as yf
            df = yf.download(ticker, period=period, interval=yf_interval, progress=False, auto_adjust=True)

            if df.empty or len(df) < 50:
                return None

            # Flatten columns if MultiIndex (yfinance fix)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            curr_close = float(df['Close'].iloc[-1])

            # 2. Identify Structure (Swings)
            df = _identify_swings(df, lookback=3)

            # Get last valid Swing High and Low
            last_swings_high = df[df['Swing_High'].notna()]
            last_swings_low = df[df['Swing_Low'].notna()]

            if last_swings_high.empty or last_swings_low.empty:
                return None

            # ---------------------------------------------------------
            # BEARISH SETUP (Market Maker Sell Model)
            # ---------------------------------------------------------
            # Logic:
            # A. Find the Highest High in recent window (Liquidity Pool)
            # B. Check if price swept it and rejected.
            # C. Check for displacement down.

            signal = "WAIT"
            setup_details = {}

            # Look at the last major swing high (e.g., from 10-50 bars ago)
            # We want a sweep of a SIGNIFICANT level, not just the last candle.

            recent_highs = last_swings_high.tail(5) # Get last 5 swing highs

            # Iterate backwards to find a setup
            # We look for a "Leg" that created a High, then broke a Low.

            # Simplified Logic for Screener:
            # 1. Find the highest point in the last 40 bars (extended from 20 to catch session highs).
            peak_idx = df['High'].iloc[-40:].idxmax()
            peak_high = df.loc[peak_idx, 'High']

            # 2. Verify displacement AFTER peak
            # Find lowest low AFTER the peak
            after_peak = df.loc[peak_idx:]
            if len(after_peak) < 3: return None # Too fresh

            valley_idx = after_peak['Low'].idxmin()
            valley_low = df.loc[valley_idx, 'Low']

            # 3. Calculate Fibonacci of this range (High -> Low)
            # Range for Bearish OTE: We draw Fib from High to Low.
            # OTE is retracement back UP to 62-79%.
            range_size = peak_high - valley_low
            fib_62 = peak_high - (range_size * 0.618)
            fib_79 = peak_high - (range_size * 0.79)

            # 4. Check if current price is IN the OTE zone
            # Bearish OTE: Price is between 62% and 79% retracement
            # (Which means it is HIGHER than the low)

            # Also check for FVG in the down leg
            fvgs = _detect_fvgs(after_peak)
            bearish_fvgs = [f for f in fvgs if f['type'] == "BEARISH"]
            has_fvg = len(bearish_fvgs) > 0

            if has_fvg and (fib_79 <= curr_close <= fib_62):
                 # One more check: Did we break structure?
                 # Ideally, the 'valley_low' should be lower than a PREVIOUS swing low (MSS)
                 # Find swing low BEFORE peak
                 before_peak = df.loc[:peak_idx].iloc[:-1] # exclude peak itself
                 if not before_peak.empty:
                     prev_swing_lows = before_peak[before_peak['Swing_Low'].notna()]
                     if not prev_swing_lows.empty:
                         last_structural_low = prev_swing_lows['Low'].iloc[-1]

                         if valley_low < last_structural_low:
                             signal = "🐻 BEARISH OTE (Sell)"
                             setup_details = {
                                 "stop": peak_high,
                                 "entry_zone": f"{fib_62:.2f} - {fib_79:.2f}",
                                 "target": valley_low - range_size # -1.0 extension
                             }

            # ---------------------------------------------------------
            # BULLISH SETUP (Market Maker Buy Model)
            # ---------------------------------------------------------
            if signal == "WAIT":
                # 1. Find lowest point in last 40 bars
                trough_idx = df['Low'].iloc[-40:].idxmin()
                trough_low = df.loc[trough_idx, 'Low']

                # 2. Find highest high AFTER trough (Displacement Up)
                after_trough = df.loc[trough_idx:]
                if len(after_trough) >= 3:
                    peak_up_idx = after_trough['High'].idxmax()
                    peak_up_high = df.loc[peak_up_idx, 'High']

                    # 3. Fibs (Low to High)
                    # OTE is retracement DOWN to 62-79%
                    range_up = peak_up_high - trough_low
                    fib_62_up = trough_low + (range_up * 0.618)
                    fib_79_up = trough_low + (range_up * 0.79)

                    # 4. Check FVG
                    bullish_fvgs = [f for f in _detect_fvgs(after_trough) if f['type'] == "BULLISH"]

                    # 5. Check Zone
                    if len(bullish_fvgs) > 0 and (fib_79_up <= curr_close <= fib_62_up):
                        # 6. Check MSS (Did we break a prior High?)
                        before_trough = df.loc[:trough_idx].iloc[:-1]
                        if not before_trough.empty:
                             prev_swing_highs = before_trough[before_trough['Swing_High'].notna()]
                             if not prev_swing_highs.empty:
                                 last_struct_high = prev_swing_highs['High'].iloc[-1]

                                 if peak_up_high > last_struct_high:
                                     signal = "🐂 BULLISH OTE (Buy)"
                                     setup_details = {
                                         "stop": trough_low,
                                         "entry_zone": f"{fib_79_up:.2f} - {fib_62_up:.2f}",
                                         "target": peak_up_high + range_up
                                     }

            if signal != "WAIT":
                return {
                    "ticker": ticker,
                    "price": curr_close,
                    "signal": signal,
                    "stop_loss": setup_details['stop'],
                    "ote_zone": setup_details['entry_zone'],
                    "target": setup_details['target'],
                    "fvg_detected": "Yes"
                }

        except Exception as e:
            return None
        return None

    # Threaded execution
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_symbol = {executor.submit(_process_ote, sym): sym for sym in ticker_list}
        for future in as_completed(future_to_symbol):
            try:
                data = future.result()
                if data:
                    results.append(data)
            except Exception:
                pass

    return results

# -------------------------------------------------------------------------
#  OPTIONS STRATEGY HELPERS (Add to option_auditor/screener.py)
# -------------------------------------------------------------------------
import math
from datetime import date

def _norm_cdf(x):
    """Cumulative distribution function for the standard normal distribution."""
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

def _calculate_put_delta(S, K, T, r, sigma):
    """
    Estimates Put Delta using Black-Scholes.
    S: Spot Price, K: Strike, T: Time to Expiry (years), r: Risk-free rate, sigma: IV
    """
    if T <= 0 or sigma <= 0: return -0.5 # Fallback
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    return _norm_cdf(d1) - 1.0

def screen_bull_put_spreads(ticker_list: list = None, min_roi: float = 0.15) -> list:
    """
    Screens for 45 DTE, 30-Delta Bull Put Spreads ($5 Wide).

    Logic:
    1. Filter for Bullish Trend (Price > SMA 50).
    2. Find Expiry closest to 45 DTE.
    3. Calculate Deltas to find Short Strike (~0.30 Delta).
    4. Find Long Strike ($5 lower).
    5. Calculate ROI (Credit / Collateral).
    """
    import yfinance as yf
    import pandas_ta as ta
    import pandas as pd

    if ticker_list is None:
        # Liquid stocks are essential for good spreads
        ticker_list = ["SPY", "QQQ", "IWM", "NVDA", "AMD", "TSLA", "AMZN", "MSFT", "AAPL", "GOOGL", "META", "NFLX", "JPM", "DIS", "BA", "COIN", "MARA"]

    results = []

    # Risk-free rate approx
    RISK_FREE_RATE = 0.045
    TARGET_DTE = 45
    SPREAD_WIDTH = 5.0
    TARGET_DELTA = -0.30 # Puts have negative delta

    def _process_spread(ticker):
        try:
            # 1. Trend Filter (Fast Fail)
            # We need ~6 months of data for SMA 50 and stability check
            df = yf.download(ticker, period="6mo", interval="1d", progress=False, auto_adjust=True)
            if df.empty or len(df) < 50: return None

            # Flatten columns
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            curr_price = float(df['Close'].iloc[-1])
            sma_50 = df['Close'].rolling(50).mean().iloc[-1]

            # Trend Check: Only sell puts if stock is above SMA 50 (Bullish/Neutral)
            if curr_price < sma_50:
                return None

            # 2. Get Option Dates
            tk = yf.Ticker(ticker)
            expirations = tk.options
            if not expirations: return None

            # Find date closest to 45 DTE
            today = date.today()
            best_date = None
            min_diff = 999

            for exp_str in expirations:
                exp_date = pd.to_datetime(exp_str).date()
                dte = (exp_date - today).days
                diff = abs(dte - TARGET_DTE)
                if diff < min_diff:
                    min_diff = diff
                    best_date = exp_str

            # Filter: Ensure DTE is reasonably close (e.g. 30 to 60 days)
            actual_dte = (pd.to_datetime(best_date).date() - today).days
            if not (25 <= actual_dte <= 75): return None

            # 3. Get Option Chain for that Date
            chain = tk.option_chain(best_date)
            puts = chain.puts

            if puts.empty: return None

            # 4. Find 30 Delta Strike
            # yfinance gives us 'impliedVolatility'. We calculate delta ourselves.
            # T in years
            T_years = actual_dte / 365.0

            # Calculate Delta for each row
            puts['calc_delta'] = puts.apply(
                lambda row: _calculate_put_delta(
                    curr_price, row['strike'], T_years, RISK_FREE_RATE, row['impliedVolatility']
                ), axis=1
            )

            # Find the row closest to -0.30
            # Sort by distance to target delta
            puts['delta_dist'] = (puts['calc_delta'] - TARGET_DELTA).abs()
            short_leg_row = puts.loc[puts['delta_dist'].idxmin()]

            short_strike = short_leg_row['strike']
            short_bid = short_leg_row['bid'] # We sell at bid (conservatively) or mid
            short_delta = short_leg_row['calc_delta']

            # 5. Find Long Strike ($5 Lower)
            long_strike_target = short_strike - SPREAD_WIDTH

            # Find strike closest to target (exact match preferred)
            puts['strike_dist'] = (puts['strike'] - long_strike_target).abs()
            long_leg_row = puts.loc[puts['strike_dist'].idxmin()]

            long_strike = long_leg_row['strike']
            long_ask = long_leg_row['ask'] # We buy at ask

            # Check if we actually found a $5 wide spread (allow small variance for weird strikes)
            actual_width = short_strike - long_strike
            if abs(actual_width - SPREAD_WIDTH) > 1.0:
                return None # Could not find the defined spread width

            # 6. Calc Metrics
            # Credit = Price Sold - Price Bought
            # Note: yfinance data can be delayed/wide. We use midpoint if bid/ask is messy,
            # but strictly: Credit = Short_Bid - Long_Ask

            # Fallback to lastPrice if bid/ask is zero (market closed/illiquid)
            s_price = short_bid if short_bid > 0 else short_leg_row['lastPrice']
            l_price = long_ask if long_ask > 0 else long_leg_row['lastPrice']

            credit = s_price - l_price

            # Max Risk = Width - Credit
            risk = actual_width - credit

            if risk <= 0 or credit <= 0: return None # Bad data

            roi = credit / risk

            if roi < min_roi: return None # Yield too low

            return {
                "ticker": ticker,
                "price": curr_price,
                "strategy": "Bull Put Spread",
                "expiry": best_date,
                "dte": actual_dte,
                "short_strike": short_strike,
                "short_delta": round(short_delta, 2),
                "long_strike": long_strike,
                "credit": round(credit, 2),
                "max_risk": round(risk, 2),
                "roi_pct": round(roi * 100, 1),
                "trend": "Bullish (>SMA50)"
            }

        except Exception as e:
            return None

    # Multi-threaded Execution
    import concurrent.futures
    final_list = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(_process_spread, t): t for t in ticker_list}
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res: final_list.append(res)

    # Sort by ROI
    final_list.sort(key=lambda x: x['roi_pct'], reverse=True)
    return final_list
