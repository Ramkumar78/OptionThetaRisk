import pandas as pd
import numpy as np
from datetime import datetime

def analyze_journal(entries: list[dict]) -> dict:
    if not entries:
        return {
            "total_trades": 0,
            "win_rate": 0,
            "total_pnl": 0.0,
            "best_pattern": "None",
            "worst_pattern": "None",
            "best_time": "None",
            "suggestions": [],
            "equity_curve": []
        }

    df = pd.DataFrame(entries)

    # Ensure types
    df['pnl'] = pd.to_numeric(df['pnl'], errors='coerce').fillna(0.0)
    df['win'] = df['pnl'] > 0

    # Ensure required columns exist
    if 'entry_date' not in df.columns:
        df['entry_date'] = datetime.now().date().isoformat()
    if 'entry_time' not in df.columns:
        df['entry_time'] = "00:00"
    if 'strategy' not in df.columns:
        df['strategy'] = "Unknown"

    # Time Analysis
    # Convert entry_time (HH:MM) to datetime objects for comparison or buckets
    def get_time_bucket(t_str):
        if not t_str: return "Unknown"
        try:
            # Assuming HH:MM format
            parts = str(t_str).split(':')
            h = int(parts[0])
            m = int(parts[1])
            t = h * 60 + m

            # Buckets
            # 09:30 = 570
            # 10:30 = 630
            # 12:00 = 720
            # 14:00 = 840
            # 16:00 = 960

            if t < 630: return "Opening (9:30-10:30)"
            elif t < 720: return "Morning (10:30-12:00)"
            elif t < 840: return "Midday (12:00-2:00)"
            elif t < 960: return "Afternoon (2:00-4:00)"
            else: return "After Hours"
        except:
            return "Unknown"

    df['time_bucket'] = df['entry_time'].apply(get_time_bucket)

    # Metrics
    total_trades = len(df)
    total_pnl = df['pnl'].sum()
    win_rate = (df['win'].sum() / total_trades) * 100 if total_trades > 0 else 0

    # Group By Pattern
    pattern_stats = df.groupby('strategy').agg(
        count=('pnl', 'count'),
        win_rate=('win', 'mean'),
        total_pnl=('pnl', 'sum'),
        avg_pnl=('pnl', 'mean')
    ).reset_index()
    pattern_stats['win_rate'] = pattern_stats['win_rate'] * 100

    # Group By Time
    time_stats = df.groupby('time_bucket').agg(
        count=('pnl', 'count'),
        win_rate=('win', 'mean'),
        total_pnl=('pnl', 'sum')
    ).reset_index()
    time_stats['win_rate'] = time_stats['win_rate'] * 100

    # Identify Best/Worst
    best_pattern = "None"
    worst_pattern = "None"

    if not pattern_stats.empty:
        # Filter for meaningful stats (at least 2 trades?)
        valid_patterns = pattern_stats[pattern_stats['count'] >= 1]
        if not valid_patterns.empty:
            best_pattern_row = valid_patterns.sort_values(by=['total_pnl', 'win_rate'], ascending=False).iloc[0]
            best_pattern = f"{best_pattern_row['strategy']} ({best_pattern_row['win_rate']:.1f}% WR, ${best_pattern_row['total_pnl']:.0f})"

            worst_pattern_row = valid_patterns.sort_values(by=['total_pnl'], ascending=True).iloc[0]
            worst_pattern = f"{worst_pattern_row['strategy']} ({worst_pattern_row['win_rate']:.1f}% WR, ${worst_pattern_row['total_pnl']:.0f})"

    best_time = "None"
    if not time_stats.empty:
        valid_times = time_stats[time_stats['count'] >= 1]
        if not valid_times.empty:
            best_time_row = valid_times.sort_values(by=['win_rate', 'total_pnl'], ascending=False).iloc[0]
            best_time = f"{best_time_row['time_bucket']} ({best_time_row['win_rate']:.1f}% WR)"

    # Generate Suggestions
    suggestions = []

    # Pattern Suggestions
    for _, row in pattern_stats.iterrows():
        if row['count'] >= 3:
            if row['win_rate'] >= 60 and row['avg_pnl'] > 0:
                suggestions.append(f"Keep trading <b>{row['strategy']}</b>. It has a high win rate ({row['win_rate']:.1f}%) and is profitable.")
            elif row['win_rate'] < 40:
                suggestions.append(f"Review <b>{row['strategy']}</b>. Win rate is low ({row['win_rate']:.1f}%). Consider refining rules or dropping.")
            elif row['avg_pnl'] < 0:
                 suggestions.append(f"<b>{row['strategy']}</b> is losing money despite reasonable win rate. Check your risk/reward ratio.")

    # Time Suggestions
    for _, row in time_stats.iterrows():
        if row['count'] >= 3:
             if row['win_rate'] < 40:
                 suggestions.append(f"Avoid trading during <b>{row['time_bucket']}</b>. Win rate is only {row['win_rate']:.1f}%.")
             if row['win_rate'] > 70:
                 suggestions.append(f"Increase size during <b>{row['time_bucket']}</b>. You are seeing the market well here.")

    if total_trades < 10:
        suggestions.append("Keep logging! Need more trades (aim for 50) for reliable patterns.")

    # Equity Curve Calculation
    equity_curve = []
    try:
        # Fill NaN dates/times
        df['temp_date'] = df['entry_date'].fillna(datetime.now().date().isoformat())
        df['temp_time'] = df['entry_time'].fillna("00:00")

        def combine_dt(row):
            try:
                # Handle cases where temp_date/time might not be strings
                d = str(row['temp_date'])
                t = str(row['temp_time'])
                return pd.to_datetime(f"{d} {t}")
            except:
                return pd.Timestamp.now()

        df['dt_sort'] = df.apply(combine_dt, axis=1)

        # Sort chronologically
        df_sorted = df.sort_values(by='dt_sort')

        # Calculate Cumulative Sum
        df_sorted['cumulative_pnl'] = df_sorted['pnl'].cumsum()

        # Format
        equity_curve = df_sorted[['dt_sort', 'cumulative_pnl']].apply(
            lambda x: {
                'date': x['dt_sort'].isoformat(),
                'cumulative_pnl': round(x['cumulative_pnl'], 2)
            }, axis=1
        ).tolist()
    except Exception as e:
        # If something fails in date parsing, fallback to empty curve or unsorted cumsum
        # For now, just log/ignore to prevent crash
        print(f"Equity Curve Error: {e}")
        pass

    # Return structure
    return {
        "total_trades": total_trades,
        "win_rate": round(win_rate, 1),
        "total_pnl": round(total_pnl, 2),
        "best_pattern": best_pattern,
        "worst_pattern": worst_pattern,
        "best_time": best_time,
        "suggestions": suggestions,
        "patterns": pattern_stats.to_dict(orient='records'),
        "time_analysis": time_stats.to_dict(orient='records'),
        "equity_curve": equity_curve
    }
