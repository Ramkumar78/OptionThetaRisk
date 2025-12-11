try:
    from tastytrade.metrics import get_market_metrics, MarketMetricInfo
    print("Import Successful")
    print(MarketMetricInfo.model_fields.keys())
except ImportError as e:
    print(f"Import Failed: {e}")
