import os
import csv
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def load_tickers_from_csv(file_path: str, column_name: str = None) -> list:
    """
    Loads tickers from a CSV file.
    Supports simple single-column CSVs or loading by column name.
    """
    tickers = []
    if not os.path.exists(file_path):
        logger.warning(f"Ticker CSV not found: {file_path}")
        return []

    try:
        # If column_name is provided, assume header exists.
        if column_name:
            df = pd.read_csv(file_path)
            if column_name in df.columns:
                raw_list = df[column_name].astype(str).str.strip().tolist()
            else:
                # Try fallback or log error?
                # Maybe file has no header but user asked for column? Unlikely.
                logger.warning(f"Column '{column_name}' not found in {file_path}")
                return []
        else:
            # If no column name, assume no header (or handle header manually)
            # This covers ftse_350.csv (no header)
            df = pd.read_csv(file_path, header=None)
            if not df.empty:
                raw_list = df.iloc[:, 0].astype(str).str.strip().tolist()
            else:
                return []

        # Common cleaning
        ignore_list = ['nan', 'symbol', 'ticker', 'company']
        tickers = [
            t.upper() for t in raw_list
            if t and t.lower() not in ignore_list and not t.startswith('/')
        ]

        # Deduplicate while preserving order
        tickers = list(dict.fromkeys(tickers))
        return tickers

    except Exception as e:
        logger.error(f"Error loading tickers from {file_path}: {e}")
        return []
