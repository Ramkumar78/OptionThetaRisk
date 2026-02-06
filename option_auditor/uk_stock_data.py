import os
import logging
import pandas as pd
from option_auditor.common.file_utils import load_tickers_from_csv
from option_auditor.common.data_utils import fetch_exchange_rate

logger = logging.getLogger("UK_Stock_Data")

# Removed hardcoded UK_TICKERS list in favor of CSV loading

UK_EURO_TICKERS = [
    # Top 50 FTSE (UK) - Note: Most should now be in the CSV, but kept for Euro mix
    "AZN.L", "SHEL.L", "HSBA.L", "ULVR.L", "BP.L", "RIO.L", "REL.L", "GSK.L", "DGE.L", "LSEG.L", "BATS.L", "GLEN.L", "BA.L", "CNA.L", "NG.L", "LLOY.L", "RR.L", "BARC.L", "CPG.L", "NWG.L", "RKT.L", "VOD.L", "AAL.L", "SGE.L", "HLN.L", "EXR.L", "TSCO.L", "SSE.L", "MNG.L", "ADM.L", "III.L", "ANTO.L", "SPX.L", "STAN.L", "IMB.L", "WTB.L", "SVT.L", "AUTO.L", "SN.L", "CRDA.L", "WPP.L", "SMIN.L", "DCC.L", "AV.L", "LGEN.L", "KGF.L", "SBRY.L", "MKS.L", "LAND.L", "PSON.L",
    # Liquid UK Mid-Caps
    "JD.L", "IAG.L", "EZJ.L", "AML.L", "IDS.L", "DLG.L", "ITM.L", "QQ.L", "GRG.L", "VTY.L", "BTRW.L", "BOO.L", "ASOS.L", "HBR.L", "ENOG.L", "TLW.L", "CWR.L", "GNC.L", "THG.L", "CURY.L", "DOM.L", "SFOR.L", "PETS.L", "MRO.L", "INVP.L", "OCDO.L", "IGG.L", "CMC.L", "PLUS.L", "EMG.L", "HWDN.L", "COST.L", "BEZ.L", "SGRO.L", "PSN.L", "TW.L", "BYG.L", "SAFE.L", "UTG.L", "BBOX.L", "MANG.L", "TPK.L", "HIK.L", "SRO.L", "FRES.L", "KAP.L", "WKP.L", "JMAT.L", "RS1.L", "PNN.L",
    # Top 50 Euro
    "ASML.AS", "MC.PA", "SAP.DE", "RMS.PA", "TTE.PA", "SIE.DE", "CDI.PA", "AIR.PA", "SAN.MC", "IBE.MC", "OR.PA", "ALV.DE", "SU.PA", "EL.PA", "AI.PA", "BNP.PA", "DTE.DE", "ENEL.MI", "DG.PA", "BBVA.MC", "CS.PA", "BAS.DE", "ADS.DE", "MUV2.DE", "IFX.DE", "SAF.PA", "ENI.MI", "INGA.AS", "ISP.MI", "KER.PA", "STLAP.PA", "AD.AS", "VOW3.DE", "BMW.DE", "MBG.DE", "BAYN.DE", "DB1.DE", "BN.PA", "RI.PA", "CRH.L", "G.MI", "PHIA.AS", "HEIA.AS", "NOKIA.HE", "VIV.PA", "ORA.PA", "KNEBV.HE", "UMG.AS", "HO.PA", "ABI.BR"
]

def get_uk_tickers():
    """
    Returns the UK FTSE 350 list from a CSV file.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(current_dir, 'data', 'ftse_350.csv')

    tickers = load_tickers_from_csv(csv_path)
    if tickers:
        logger.info(f"Loaded {len(tickers)} tickers from CSV: {csv_path}")
        return tickers
    else:
        logger.warning(f"FTSE 350 CSV not found at {csv_path}.")
        return []

def get_uk_euro_tickers():
    """Returns normalized UK/Euro tickers list."""
    # We could potentially merge get_uk_tickers() here, but keeping legacy list for now
    # to preserve the Euro component which is not in the CSV.
    return list(set(UK_EURO_TICKERS))

def apply_currency_conversion(df: pd.DataFrame, target_currency: str = 'GBP', source_currency: str = 'GBp') -> pd.DataFrame:
    """
    Converts DataFrame OHLCV data to target currency.

    :param df: The DataFrame containing market data.
    :param target_currency: The desired currency (GBP, USD, EUR, etc).
    :param source_currency: The source currency.
                            Defaults to 'GBp' (Pence) which is standard for LSE (.L) tickers.
                            For Euro tickers, caller should pass 'EUR'.
    """
    if df.empty:
        return df

    # Normalize GBp (pence) to GBP (pounds) first if needed
    is_pence = (source_currency == 'GBp')
    normalization_factor = 0.01 if is_pence else 1.0
    actual_source_iso = 'GBP' if is_pence else source_currency

    # Optimization: If target is GBP and source is GBp, just scale by 0.01
    # If target is GBp and source is GBp, do nothing.
    if source_currency == target_currency:
        return df

    # Fetch rate from Actual Source (e.g. GBP) to Target (e.g. USD)
    try:
        exchange_rate = fetch_exchange_rate(actual_source_iso, target_currency)
    except Exception as e:
        logger.error(f"Failed to fetch exchange rate: {e}")
        return df

    # Total multiplier = Normalization * Exchange Rate
    # e.g. GBp -> USD: 0.01 * (GBP->USD Rate)
    # e.g. GBp -> GBP: 0.01 * 1.0 = 0.01
    final_multiplier = normalization_factor * exchange_rate

    if final_multiplier == 1.0:
        return df

    df_conv = df.copy()
    cols_to_convert = ['Open', 'High', 'Low', 'Close', 'Adj Close']

    logger.info(f"Converting UK Data from {source_currency} to {target_currency} (Multiplier: {final_multiplier})")

    for col in cols_to_convert:
        if col in df_conv.columns:
            df_conv[col] = df_conv[col] * final_multiplier

    return df_conv
