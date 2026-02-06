import os
import sys
import uuid
import random
import argparse
from datetime import datetime, timedelta

# Add root directory to path to allow imports from webapp
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from webapp.storage import get_storage_provider
from webapp.app import create_app

def generate_sample_data(username, count=50):
    print(f"Generating {count} sample journal entries for user: {username}")

    app = create_app(testing=True)
    with app.app_context():
        storage = get_storage_provider(app)

        strategies = ["VCP", "Pullback", "Breakout", "Mean Reversion", "Income"]
        sentiments = ["Bullish", "Bearish", "Neutral"]
        symbols = ["AAPL", "TSLA", "NVDA", "AMD", "SPY", "QQQ", "IWM"]
        emotions_pool = ["Disciplined", "FOMO", "Fear", "Greed", "Confident", "Hesitant"]

        entries = []
        end_date = datetime.now()

        for i in range(count):
            # Random date within last 6 months
            days_ago = random.randint(1, 180)
            entry_dt = end_date - timedelta(days=days_ago)
            entry_date_str = entry_dt.strftime("%Y-%m-%d")
            entry_time_str = entry_dt.strftime("%H:%M:%S")

            symbol = random.choice(symbols)
            strategy = random.choice(strategies)
            sentiment = random.choice(sentiments)

            # Win rate ~60%
            is_win = random.random() < 0.60

            if is_win:
                pnl = random.uniform(100, 1000)
                emotion = "Disciplined" if random.random() > 0.2 else "Greed"
            else:
                pnl = random.uniform(-500, -100)
                emotion = "Disciplined" if random.random() > 0.5 else "FOMO"

            # Sometimes add a second emotion
            emotions = [emotion]
            if random.random() > 0.8:
                 emotions.append(random.choice(emotions_pool))

            qty = random.randint(1, 10)
            entry_price = random.uniform(50, 200)
            exit_price = entry_price + (pnl / qty)

            entry = {
                "id": str(uuid.uuid4()),
                "username": username,
                "entry_date": entry_date_str,
                "entry_time": entry_time_str,
                "symbol": symbol,
                "strategy": strategy,
                "direction": "Long" if pnl > 0 or random.random() > 0.5 else "Short",
                "entry_price": round(entry_price, 2),
                "exit_price": round(exit_price, 2),
                "qty": qty,
                "pnl": round(pnl, 2),
                "sentiment": sentiment,
                "notes": f"Sample trade generated via script. Strategy: {strategy}",
                "emotions": emotions
            }
            entries.append(entry)

        saved_count = storage.save_journal_entries(entries)
        print(f"Successfully saved {saved_count} entries for {username}.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate sample journal data")
    parser.add_argument("--username", type=str, required=True, help="Username to assign trades to")
    parser.add_argument("--count", type=int, default=50, help="Number of entries to generate")

    args = parser.parse_args()
    generate_sample_data(args.username, args.count)
