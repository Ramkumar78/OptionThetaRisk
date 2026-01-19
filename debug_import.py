import sys
import traceback

try:
    import tastytrade
    print(f"Tastytrade version: {tastytrade.__version__}")
    from tastytrade import Session, Account
    print("Import successful!")
except ImportError:
    print("ImportError caught!")
    traceback.print_exc()
except Exception:
    print("Other exception caught!")
    traceback.print_exc()
