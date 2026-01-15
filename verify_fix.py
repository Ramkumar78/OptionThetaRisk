import sys
import os
import logging

# Configure logging to see output
logging.basicConfig(level=logging.INFO)

# Add repo root to path
sys.path.append(os.getcwd())

try:
    from option_auditor.screener import screen_options_only_strategy
    print("Successfully imported screen_options_only_strategy")
except ImportError as e:
    print(f"Failed to import screen_options_only_strategy: {e}")
    sys.exit(1)

# Run with small limit
print("Running screener with limit=5...")
try:
    # Use 'us' region by default
    results = screen_options_only_strategy(limit=5)
    print(f"Screener returned {len(results)} results.")
    if results:
        print("Sample result keys:", results[0].keys())
    else:
        print("No results found (this is possible if tickers are skipped or don't match criteria, but function ran successfully)")
except Exception as e:
    print(f"Screener failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
