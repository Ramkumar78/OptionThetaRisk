import logging
from option_auditor.strategies.math_utils import generate_human_verdict

# Configure logger
logger = logging.getLogger(__name__)

# Import Unified Screener
from option_auditor.unified_screener import screen_universal_dashboard

# Imports from common constants
from option_auditor.common.constants import SECTOR_NAMES, SECTOR_COMPONENTS, TICKER_NAMES, DEFAULT_ACCOUNT_SIZE, RISK_FREE_RATE

# Import Refactored Utilities and Constants
from option_auditor.strategies.vertical_spreads import screen_vertical_put_spreads
from option_auditor.strategies.turtle import TurtleStrategy
from option_auditor.strategies.isa import IsaStrategy
from option_auditor.strategies.bull_put import screen_bull_put_spreads
from option_auditor.strategies.squeeze import screen_bollinger_squeeze
from option_auditor.strategies.liquidity import screen_liquidity_grabs
from option_auditor.strategies.fortress import screen_dynamic_volatility_fortress
from option_auditor.strategies.rsi_divergence import RsiDivergenceStrategy
from option_auditor.strategies.fourier import FourierStrategy
from option_auditor.strategies.quantum import screen_quantum_setups
from option_auditor.strategies.options_only import screen_options_only_strategy
from option_auditor.strategies.five_thirteen import FiveThirteenStrategy
from option_auditor.strategies.darvas import DarvasBoxStrategy
from option_auditor.common.screener_utils import ScreeningRunner, run_screening_strategy

# --- IMPORT NEWLY REFACTORED STRATEGIES ---
from option_auditor.strategies.market import (
    screen_market,
    screen_sectors,
    enrich_with_fundamentals
)
from option_auditor.strategies.mms_ote import screen_mms_ote_setups
from option_auditor.strategies.alpha import (
    screen_alpha_101,
    screen_my_strategy
)
from option_auditor.strategies.hybrid import (
    screen_hybrid_strategy,
    screen_confluence_scan
)
from option_auditor.strategies.master import screen_master_convergence
from option_auditor.strategies.monte_carlo import screen_monte_carlo_forecast

# -------------------------------------------------------------------------
#  WRAPPERS FOR EXISTING STRATEGIES
# -------------------------------------------------------------------------

def screen_turtle_setups(ticker_list: list = None, time_frame: str = "1d", region: str = "us", check_mode: bool = False) -> list:
    """
    Screens for Turtle Trading Setups (20-Day Breakouts).
    Supports multiple timeframes.
    DELEGATES TO: option_auditor/strategies/turtle.py
    """
    return run_screening_strategy(
        TurtleStrategy,
        ticker_list=ticker_list,
        time_frame=time_frame,
        region=region,
        check_mode=check_mode
    )

def screen_5_13_setups(ticker_list: list = None, time_frame: str = "1d", region: str = "us", check_mode: bool = False) -> list:
    """
    Screens for 5/13 and 5/21 EMA Crossovers (Momentum Breakouts).
    DELEGATES TO: option_auditor/strategies/five_thirteen.py
    """
    return run_screening_strategy(
        FiveThirteenStrategy,
        ticker_list=ticker_list,
        time_frame=time_frame,
        region=region,
        check_mode=check_mode,
        sorting_key=lambda x: 0 if "FRESH" in x['signal'] else 1
    )

def screen_darvas_box(ticker_list: list = None, time_frame: str = "1d", region: str = "us", check_mode: bool = False) -> list:
    """
    Screens for Darvas Box Breakouts.
    DELEGATES TO: option_auditor/strategies/darvas.py
    """
    return run_screening_strategy(
        DarvasBoxStrategy,
        ticker_list=ticker_list,
        time_frame=time_frame,
        region=region,
        check_mode=check_mode
    )

def screen_trend_followers_isa(ticker_list: list = None, risk_per_trade_pct: float = 0.01, region: str = "us", check_mode: bool = False, time_frame: str = "1d", account_size: float = DEFAULT_ACCOUNT_SIZE) -> list:
    """
    The 'Legendary Trend' Screener for ISA Accounts (Long Only).
    Supports Dynamic Position Sizing if account_size is provided.
    DELEGATES TO: option_auditor/strategies/isa.py
    """
    if not (0.001 <= risk_per_trade_pct <= 0.10):
        logger.warning(f"risk_per_trade_pct {risk_per_trade_pct} out of bounds (0.001-0.1). Resetting to 0.01.")
        risk_per_trade_pct = 0.01

    # Sort by signal priority
    def sort_key(x):
        s = x.get('signal', '')
        if "ENTER" in s: return 0
        if "WATCH" in s: return 1
        return 2

    return run_screening_strategy(
        IsaStrategy,
        ticker_list=ticker_list,
        time_frame=time_frame,
        region=region,
        check_mode=check_mode,
        sorting_key=sort_key,
        account_size=account_size,
        risk_per_trade_pct=risk_per_trade_pct
    )

def screen_fourier_cycles(ticker_list: list = None, time_frame: str = "1d", region: str = "us") -> list:
    """
    Screens for Cyclical Turns using Instantaneous Phase (Hilbert Transform).
    FIX: Removed fixed period limits (5-60d). Now detects geometric turns.
    DELEGATES TO: option_auditor/strategies/fourier.py
    """
    # Sort by strength (descending)
    def get_sort_key(x):
        if not x: return 0
        s = x.get('cycle_strength', '0%')
        if isinstance(s, str):
            try:
                return float(s.replace('%', ''))
            except:
                return 0
        return s

    return run_screening_strategy(
        FourierStrategy,
        ticker_list=ticker_list,
        time_frame=time_frame,
        region=region,
        sorting_key=get_sort_key,
        reverse_sort=True
    )

def screen_rsi_divergence(ticker_list: list = None, time_frame: str = "1d", region: str = "us") -> list:
    """
    Screens for RSI Divergences (Regular).
    Bullish: Price Lower Low, RSI Higher Low.
    Bearish: Price Higher High, RSI Lower High.
    DELEGATES TO: option_auditor/strategies/rsi_divergence.py
    """
    return run_screening_strategy(
        RsiDivergenceStrategy,
        ticker_list=ticker_list,
        time_frame=time_frame,
        region=region
    )
