
import logging
import pandas as pd
import numpy as np
from option_auditor.screener import screen_hybrid_strategy, screen_turtle_setups

# Configure logging
logging.basicConfig(level=logging.ERROR)

def debug_hims():
    ticker = "hims"
    print(f"--- Debugging {ticker} ---")
    
    # Check Hybrid
    print("\n[Hybrid Strategy]")
    try:
        results = screen_hybrid_strategy(ticker_list=[ticker], check_mode=True)
        if not results:
            print("❌ Hybrid Strategy returned EMPTY list.")
        else:
            print(f"✅ Hybrid Strategy Success. Count: {len(results)}")
            for r in results:
                print(f"   Signal: {r.get('signal')}")
                print(f"   Price: {r.get('price')}")
                print(f"   Trend: {r.get('trend_verdict')}") # hybrid specific
    except Exception as e:
        print(f"❌ Hybrid Exception: {e}")
        import traceback
        traceback.print_exc()

    # Check Turtle
    print("\n[Turtle Strategy]")
    try:
        results = screen_turtle_setups(ticker_list=[ticker], check_mode=True)
        if not results:
            print("❌ Turtle Strategy returned EMPTY list.")
        else:
            print(f"✅ Turtle Strategy Success. Count: {len(results)}")
            for r in results:
                print(f"   Signal: {r.get('signal')}")
                print(f"   Price: {r.get('price')}")
    except Exception as e:
        print(f"❌ Turtle Exception: {e}")

if __name__ == "__main__":
    debug_hims()
