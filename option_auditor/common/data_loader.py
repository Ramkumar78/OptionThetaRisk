import os
import csv
import logging
import pandas as pd
from typing import List

logger = logging.getLogger(__name__)

def load_tickers_from_csv(filename: str, column_name: str = None) -> List[str]:
    """
    Loads a list of unique tickers from a CSV file located in the 'option_auditor/data' directory.

    Args:
        filename (str): Name of the CSV file (e.g., 'us_sectors.csv').
        column_name (str, optional): The column name containing tickers. If None, assumes first column.

    Returns:
        List[str]: A list of unique, stripped, uppercase tickers.
    """
    tickers = []
    try:
        # Construct path relative to this file
        # This file is in option_auditor/common/
        # Data is in option_auditor/data/
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        csv_path = os.path.join(base_dir, 'data', filename)

        if not os.path.exists(csv_path):
            logger.warning(f"CSV file not found: {csv_path}")
            return []

        # Attempt to use pandas for robustness if header is known or expected
        try:
            df = pd.read_csv(csv_path)

            # If column name provided, use it
            target_col = None
            if column_name and column_name in df.columns:
                target_col = column_name
            # Else if 'Symbol' or 'Ticker' exists, prioritize them
            elif 'Symbol' in df.columns:
                target_col = 'Symbol'
            elif 'Ticker' in df.columns:
                target_col = 'Ticker'

            if target_col:
                tickers = df[target_col].astype(str).str.strip().unique().tolist()
            else:
                # Fallback to first column
                tickers = df.iloc[:, 0].astype(str).str.strip().unique().tolist()

        except pd.errors.EmptyDataError:
             logger.warning(f"CSV file is empty: {csv_path}")
             return []

        # Clean tickers
        cleaned_tickers = [
            t.upper() for t in tickers
            if t and t.lower() != 'nan' and not t.startswith('/')
        ]

        # logger.info(f"Loaded {len(cleaned_tickers)} tickers from {filename}")
        return cleaned_tickers

    except Exception as e:
        logger.error(f"Error loading tickers from {filename}: {e}")
        return []
