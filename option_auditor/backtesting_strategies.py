from abc import ABC, abstractmethod
import pandas as pd
import pandas_ta as ta
import logging
from option_auditor.common.constants import VIX_GREEN_THRESHOLD, VIX_YELLOW_THRESHOLD
from option_auditor.strategies.rsi_reversal import RsiReversalStrategy

logger = logging.getLogger("BacktestStrategies")

class AbstractBacktestStrategy(ABC):
    def __init__(self, strategy_type: str):
        self.strategy_type = strategy_type

    @abstractmethod
    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add strategy-specific indicators to the DataFrame."""
        pass

    @abstractmethod
    def should_buy(self, i: int, df: pd.DataFrame, context: dict) -> bool:
        """Check for buy signal at index i."""
        pass

    @abstractmethod
    def should_sell(self, i: int, df: pd.DataFrame, context: dict) -> tuple[bool, str]:
        """Check for sell signal at index i. Returns (should_sell, reason)."""
        pass

    @abstractmethod
    def get_initial_stop_target(self, row: pd.Series, atr: float) -> tuple[float, float]:
        """Calculate initial stop loss and target price."""
        pass

    def get_retail_explanation(self) -> str:
        """Returns a retail-friendly explanation of the strategy."""
        return "No explanation available."

    def _get_regime(self, row):
        spy_price = row.get('Spy', 0)
        spy_sma = row.get('spy_sma200', 0)
        vix_price = row.get('Vix', 99)

        if spy_price > spy_sma and vix_price < VIX_GREEN_THRESHOLD:
            return "GREEN"
        elif spy_price > spy_sma and vix_price < VIX_YELLOW_THRESHOLD:
            return "YELLOW"
        return "RED"


class GrandmasterBacktestStrategy(AbstractBacktestStrategy):
    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df['sma50'] = df['Close'].rolling(50).mean()
        df['sma200'] = df['Close'].rolling(200).mean()
        df['high_20'] = df['High'].rolling(20).max().shift(1)
        df['low_20'] = df['Low'].rolling(20).min().shift(1)
        return df

    def should_buy(self, i: int, df: pd.DataFrame, context: dict) -> bool:
        row = df.iloc[i]
        regime = self._get_regime(row)

        if regime == "RED":
            return False

        price = row['Close']
        sma50 = row['sma50']
        sma200 = row['sma200']
        high_20d = row['high_20']

        is_trend = (price > sma200) and (price > sma50) and (sma50 > sma200)
        breakout = (price > high_20d)

        return is_trend and breakout

    def should_sell(self, i: int, df: pd.DataFrame, context: dict) -> tuple[bool, str]:
        row = df.iloc[i]
        regime = self._get_regime(row)

        if regime == "RED":
            return True, "REGIME CHANGE (RED)"

        price = row['Close']
        trail_stop = row['low_20']
        if price < trail_stop:
            return True, "TRAILING STOP (20d Low)"

        return False, ""

    def get_initial_stop_target(self, row: pd.Series, atr: float) -> tuple[float, float]:
        price = row['Close']
        stop_loss = price - (2.5 * atr)
        target_price = price + (6 * atr)
        return stop_loss, target_price


class TurtleBacktestStrategy(AbstractBacktestStrategy):
    def get_retail_explanation(self) -> str:
        return "Trend Following Strategy: Buying breakouts of 20-day highs. Profiting from strong trends."

    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df['high_20'] = df['High'].rolling(20).max().shift(1)
        df['low_10'] = df['Low'].rolling(10).min().shift(1)
        return df

    def should_buy(self, i: int, df: pd.DataFrame, context: dict) -> bool:
        row = df.iloc[i]
        price = row['Close']
        return price > row['high_20']

    def should_sell(self, i: int, df: pd.DataFrame, context: dict) -> tuple[bool, str]:
        row = df.iloc[i]
        price = row['Close']
        if price < row['low_10']:
            return True, "10d LOW EXIT"
        return False, ""

    def get_initial_stop_target(self, row: pd.Series, atr: float) -> tuple[float, float]:
        price = row['Close']
        stop_loss = price - (2 * atr)
        target_price = price + (4 * atr)
        return stop_loss, target_price


class IsaBacktestStrategy(AbstractBacktestStrategy):
    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df['sma50'] = df['Close'].rolling(50).mean()
        df['sma200'] = df['Close'].rolling(200).mean()
        df['high_50'] = df['High'].rolling(50).max().shift(1)
        df['low_20'] = df['Low'].rolling(20).min().shift(1)
        return df

    def should_buy(self, i: int, df: pd.DataFrame, context: dict) -> bool:
        row = df.iloc[i]
        price = row['Close']
        is_breakout_50 = price > row['high_50']
        is_isa_reentry = (price > row['sma50']) and (price > row['sma200'])
        return (price > row['sma200']) and (is_breakout_50 or is_isa_reentry)

    def should_sell(self, i: int, df: pd.DataFrame, context: dict) -> tuple[bool, str]:
        row = df.iloc[i]
        price = row['Close']
        if price < row['low_20']:
            return True, "20d LOW EXIT"
        return False, ""

    def get_initial_stop_target(self, row: pd.Series, atr: float) -> tuple[float, float]:
        price = row['Close']
        stop_loss = price - (2.5 * atr)
        target_price = price + (6 * atr)
        return stop_loss, target_price


class MarketBacktestStrategy(AbstractBacktestStrategy):
    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df['sma50'] = df['Close'].rolling(50).mean()
        df['rsi'] = ta.rsi(df['Close'], length=14)
        return df

    def should_buy(self, i: int, df: pd.DataFrame, context: dict) -> bool:
        row = df.iloc[i]
        price = row['Close']
        is_uptrend = price > row['sma50']
        rsi = row['rsi']
        return is_uptrend and (30 <= rsi <= 50)

    def should_sell(self, i: int, df: pd.DataFrame, context: dict) -> tuple[bool, str]:
        row = df.iloc[i]
        price = row['Close']
        is_uptrend = price > row['sma50']
        if not is_uptrend:
            return True, "TREND CHANGE (<SMA50)"
        return False, ""

    def get_initial_stop_target(self, row: pd.Series, atr: float) -> tuple[float, float]:
        price = row['Close']
        stop_loss = price - (2 * atr)
        target_price = price + (4 * atr)
        return stop_loss, target_price


class EmaBacktestStrategy(AbstractBacktestStrategy):
    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df['ema5'] = ta.ema(df['Close'], length=5)
        df['ema13'] = ta.ema(df['Close'], length=13)
        df['ema21'] = ta.ema(df['Close'], length=21)
        return df

    def should_buy(self, i: int, df: pd.DataFrame, context: dict) -> bool:
        if i < 1: return False
        row = df.iloc[i]
        prev_row = df.iloc[i-1]

        ema5 = row['ema5']
        ema13 = row['ema13']
        prev_ema5 = prev_row['ema5']
        prev_ema13 = prev_row['ema13']

        return ema5 > ema13 and prev_ema5 <= prev_ema13

    def should_sell(self, i: int, df: pd.DataFrame, context: dict) -> tuple[bool, str]:
        row = df.iloc[i]
        ema5 = row['ema5']
        ema13 = row['ema13']
        if ema5 < ema13:
            return True, "CROSS UNDER (5<13)"
        return False, ""

    def get_initial_stop_target(self, row: pd.Series, atr: float) -> tuple[float, float]:
        price = row['Close']
        stop_loss = row['ema21'] * 0.99
        target_price = price * 1.2
        return stop_loss, target_price


class DarvasBacktestStrategy(AbstractBacktestStrategy):
    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df['high_20'] = df['High'].rolling(20).max().shift(1)
        df['low_20'] = df['Low'].rolling(20).min().shift(1)
        return df

    def should_buy(self, i: int, df: pd.DataFrame, context: dict) -> bool:
        row = df.iloc[i]
        price = row['Close']
        high_20d = row['high_20']
        return price > high_20d

    def should_sell(self, i: int, df: pd.DataFrame, context: dict) -> tuple[bool, str]:
        row = df.iloc[i]
        price = row['Close']
        if price < row['low_20']:
            return True, "BOX LOW BREAK"
        return False, ""

    def get_initial_stop_target(self, row: pd.Series, atr: float) -> tuple[float, float]:
        price = row['Close']
        stop_loss = row['low_20']
        target_price = price * 1.25
        return stop_loss, target_price


class MmsOteBacktestStrategy(AbstractBacktestStrategy):
    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df['sma50'] = df['Close'].rolling(50).mean()
        df['rsi'] = ta.rsi(df['Close'], length=14)
        return df

    def should_buy(self, i: int, df: pd.DataFrame, context: dict) -> bool:
        row = df.iloc[i]
        price = row['Close']
        return (price > row['sma50']) and (row['rsi'] < 40)

    def should_sell(self, i: int, df: pd.DataFrame, context: dict) -> tuple[bool, str]:
        return False, ""

    def get_initial_stop_target(self, row: pd.Series, atr: float) -> tuple[float, float]:
        price = row['Close']
        stop_loss = price - (2 * atr)
        target_price = price + (4 * atr)
        return stop_loss, target_price


class BullPutBacktestStrategy(AbstractBacktestStrategy):
    def get_retail_explanation(self) -> str:
        return "Bullish Strategy: You want the stock to stay ABOVE your short strike. You profit from time decay (Theta)."

    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df['sma50'] = df['Close'].rolling(50).mean()
        df['rsi'] = ta.rsi(df['Close'], length=14)
        return df

    def should_buy(self, i: int, df: pd.DataFrame, context: dict) -> bool:
        row = df.iloc[i]
        price = row['Close']
        return (price > row['sma50']) and (40 < row['rsi'] < 55)

    def should_sell(self, i: int, df: pd.DataFrame, context: dict) -> tuple[bool, str]:
        return False, ""

    def get_initial_stop_target(self, row: pd.Series, atr: float) -> tuple[float, float]:
        price = row['Close']
        stop_loss = price - (2 * atr)
        target_price = price + (4 * atr)
        return stop_loss, target_price


class HybridBacktestStrategy(AbstractBacktestStrategy):
    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df['sma200'] = df['Close'].rolling(200).mean()
        df['rsi'] = ta.rsi(df['Close'], length=14)
        return df

    def should_buy(self, i: int, df: pd.DataFrame, context: dict) -> bool:
        row = df.iloc[i]
        price = row['Close']
        is_trend = price > row['sma200']
        is_cycle_low = row['rsi'] < 30

        if self.strategy_type == 'hybrid':
            return is_trend and is_cycle_low
        else: # fourier
            return is_cycle_low

    def should_sell(self, i: int, df: pd.DataFrame, context: dict) -> tuple[bool, str]:
        row = df.iloc[i]
        if row['rsi'] > 70:
            return True, "CYCLE HIGH"
        return False, ""

    def get_initial_stop_target(self, row: pd.Series, atr: float) -> tuple[float, float]:
        price = row['Close']
        stop_loss = price - (2 * atr)
        target_price = price + (2 * atr)
        return stop_loss, target_price


class FortressBacktestStrategy(AbstractBacktestStrategy):
    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df['sma200'] = df['Close'].rolling(200).mean()
        df['rsi'] = ta.rsi(df['Close'], length=14)
        return df

    def should_buy(self, i: int, df: pd.DataFrame, context: dict) -> bool:
        row = df.iloc[i]
        regime = self._get_regime(row)
        price = row['Close']
        return (price > row['sma200']) and (regime != "RED") and (row['rsi'] < 40)

    def should_sell(self, i: int, df: pd.DataFrame, context: dict) -> tuple[bool, str]:
        return False, ""

    def get_initial_stop_target(self, row: pd.Series, atr: float) -> tuple[float, float]:
        price = row['Close']
        stop_loss = price - (2 * atr)
        target_price = price + (4 * atr)
        return stop_loss, target_price


class QuantumBacktestStrategy(AbstractBacktestStrategy):
    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df['sma50'] = df['Close'].rolling(50).mean()
        df['rsi'] = ta.rsi(df['Close'], length=14)
        return df

    def should_buy(self, i: int, df: pd.DataFrame, context: dict) -> bool:
        row = df.iloc[i]
        price = row['Close']
        return (price > row['sma50']) and (row['rsi'] > 50)

    def should_sell(self, i: int, df: pd.DataFrame, context: dict) -> tuple[bool, str]:
        return False, ""

    def get_initial_stop_target(self, row: pd.Series, atr: float) -> tuple[float, float]:
        price = row['Close']
        stop_loss = price - (2 * atr)
        target_price = price + (4 * atr)
        return stop_loss, target_price


class Alpha101BacktestStrategy(AbstractBacktestStrategy):
    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        denom = (df['High'] - df['Low']) + 0.001
        df['alpha101'] = (df['Close'] - df['Open']) / denom
        return df

    def should_buy(self, i: int, df: pd.DataFrame, context: dict) -> bool:
        row = df.iloc[i]
        return row['alpha101'] > 0.5

    def should_sell(self, i: int, df: pd.DataFrame, context: dict) -> tuple[bool, str]:
        return False, ""

    def get_initial_stop_target(self, row: pd.Series, atr: float) -> tuple[float, float]:
        price = row['Close']
        stop_loss = row['Low'] - (0.5 * atr)
        target_price = price + (2 * atr)
        return stop_loss, target_price


class MyStrategyBacktestStrategy(AbstractBacktestStrategy):
    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df['sma50'] = df['Close'].rolling(50).mean()
        df['sma200'] = df['Close'].rolling(200).mean()
        denom = (df['High'] - df['Low']) + 0.001
        df['alpha101'] = (df['Close'] - df['Open']) / denom
        return df

    def should_buy(self, i: int, df: pd.DataFrame, context: dict) -> bool:
        row = df.iloc[i]
        price = row['Close']
        is_trend_up = (price > row['sma200']) and (price > row['sma50'])
        return is_trend_up and (row['alpha101'] > 0.5)

    def should_sell(self, i: int, df: pd.DataFrame, context: dict) -> tuple[bool, str]:
        return False, ""

    def get_initial_stop_target(self, row: pd.Series, atr: float) -> tuple[float, float]:
        price = row['Close']
        if row['alpha101'] > 0.5:
            stop_loss = row['Low'] - (0.5 * atr)
        else:
            stop_loss = price - (3 * atr)

        risk = price - stop_loss
        target_price = price + (risk * 2) if risk > 0 else price + (5 * atr)
        return stop_loss, target_price


class LiquidityGrabBacktestStrategy(AbstractBacktestStrategy):
    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        # Does not need specific indicators pre-calc beyond standard (handled by context/memory)
        # But we need access to swing points which are in context
        return df

    def should_buy(self, i: int, df: pd.DataFrame, context: dict) -> bool:
        row = df.iloc[i]
        curr_l = row['Low']
        curr_c = row['Close']
        recent_swing_lows = context.get('recent_swing_lows', [])

        for swing in recent_swing_lows:
            if curr_l < swing['price'] and curr_c > swing['price']:
                return True
        return False

    def should_sell(self, i: int, df: pd.DataFrame, context: dict) -> tuple[bool, str]:
        row = df.iloc[i]
        curr_h = row['High']
        curr_c = row['Close']
        recent_swing_highs = context.get('recent_swing_highs', [])

        for swing in recent_swing_highs:
            if curr_h > swing['price'] and curr_c < swing['price']:
                return True, "BEARISH SWEEP"
        return False, ""

    def get_initial_stop_target(self, row: pd.Series, atr: float) -> tuple[float, float]:
        price = row['Close']
        stop_loss = row['Low'] - (0.5 * atr)
        risk = price - stop_loss
        target_price = price + (3 * risk) if risk > 0 else price + (4 * atr)
        return stop_loss, target_price


class RsiBacktestStrategy(AbstractBacktestStrategy):
    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df['rsi'] = ta.rsi(df['Close'], length=14)
        return df

    def should_buy(self, i: int, df: pd.DataFrame, context: dict) -> bool:
        if i < 2: return False
        row = df.iloc[i]

        # Check if we just formed a swing low at i-1
        # This logic was in the main loop:
        # if r1['Low'] < r2['Low'] and r1['Low'] < row['Low']: is_new_swing_low = True

        # We need to rely on the context's memory of recent swings?
        # The main loop logic was: check if i-1 is a new swing low, THEN compare it to previous swings.

        recent_swing_lows = context.get('recent_swing_lows', [])

        # But wait, the context `recent_swing_lows` is updated in the main loop BEFORE calling should_buy?
        # If so, the latest one is the one at i-1.

        if len(recent_swing_lows) >= 2:
            latest = recent_swing_lows[-1]
            # Verify if this 'latest' swing was indeed formed at i-1.
            # The context update logic in UnifiedBacktester loop handles detection.
            # If the strategy detected a swing low at i-1, it appended it.

            # Check if latest idx is i-1
            if latest['idx'] == i-1:
                for prev in recent_swing_lows[:-1]:
                    # Bullish Div: Lower Price, Higher RSI
                    if latest['price'] < prev['price'] and latest['rsi'] > prev['rsi']:
                        return True
        return False

    def should_sell(self, i: int, df: pd.DataFrame, context: dict) -> tuple[bool, str]:
        recent_swing_highs = context.get('recent_swing_highs', [])
        if len(recent_swing_highs) >= 2:
            latest = recent_swing_highs[-1]
            if latest['idx'] == i-1:
                for prev in recent_swing_highs[:-1]:
                    # Bearish Div: Higher Price, Lower RSI
                    if latest['price'] > prev['price'] and latest['rsi'] < prev['rsi']:
                        return True, "BEARISH DIVERGENCE"
        return False, ""

    def get_initial_stop_target(self, row: pd.Series, atr: float) -> tuple[float, float]:
        price = row['Close']
        stop_loss = row['Low'] - (1.0 * atr)
        target_price = price + (3.0 * atr)
        return stop_loss, target_price

# Factory
def get_strategy(strategy_type: str) -> AbstractBacktestStrategy:
    s = strategy_type.lower()
    if s in ['grandmaster', 'council', 'master', 'master_convergence']:
        return GrandmasterBacktestStrategy(s)
    if s == 'turtle':
        return TurtleBacktestStrategy(s)
    if s == 'isa':
        return IsaBacktestStrategy(s)
    if s == 'market':
        return MarketBacktestStrategy(s)
    if s in ['ema', 'ema_5_13']:
        return EmaBacktestStrategy(s)
    if s == 'darvas':
        return DarvasBacktestStrategy(s)
    if s in ['mms', 'mms_ote']:
        return MmsOteBacktestStrategy(s)
    if s == 'bull_put':
        return BullPutBacktestStrategy(s)
    if s in ['fourier', 'hybrid']:
        return HybridBacktestStrategy(s)
    if s == 'fortress':
        return FortressBacktestStrategy(s)
    if s == 'quantum':
        return QuantumBacktestStrategy(s)
    if s == 'alpha101':
        return Alpha101BacktestStrategy(s)
    if s == 'mystrategy':
        return MyStrategyBacktestStrategy(s)
    if s == 'liquidity_grab':
        return LiquidityGrabBacktestStrategy(s)
    if s in ['rsi', 'rsi_divergence']:
        return RsiBacktestStrategy(s)
    if s == 'rsi_reversal':
        return RsiReversalStrategy(s)

    # Default to Market if unknown?
    return MarketBacktestStrategy(s)
