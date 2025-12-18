from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from cachetools import TTLCache
import asyncio
import pandas as pd
from typing import Optional, List, Dict, Any

from webapp.app import app as flask_app
from option_auditor.models import StockCheckRequest, ScanResult
from option_auditor import screener
from option_auditor.strategies.isa import IsaStrategy
from option_auditor.common.data_utils import async_fetch_data_with_retry
from option_auditor.common.resilience import data_api_breaker

# Initialize FastAPI
fastapi_app = FastAPI()

# Enable CORS (Required for Frontend)
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Advanced Local Caching (The "Poor Man's Redis")
# Thread-Safe LRU Cache with TTL of 600 seconds
SCREENER_CACHE = TTLCache(maxsize=100, ttl=600)

@fastapi_app.get("/health")
async def health():
    return "OK"

@fastapi_app.get("/api/screener/status")
async def get_breaker_status():
    """
    Returns the real-time status of the Circuit Breaker.
    Used by the frontend to display 'Stale Data' warnings.
    """
    return {
        "api_health": data_api_breaker.current_state, # 'closed', 'open', 'half-open'
        "is_fallback": data_api_breaker.current_state == 'open'
    }

@fastapi_app.get("/api/screen/isa/check", response_model=ScanResult)
async def check_isa_stock_async(ticker: str, entry_price: Optional[float] = None):
    """
    Async implementation of the ISA Check endpoint.
    Uses asyncio to handle concurrent requests without blocking.
    """

    # Check Cache
    cache_key = f"isa_check_{ticker}"
    if cache_key in SCREENER_CACHE:
        return SCREENER_CACHE[cache_key]

    try:
        ticker = screener.resolve_ticker(ticker) or ticker.upper()

        # 1. Transition to Async I/O (The "No-Cost" Performance Play)
        # Fetch data asynchronously
        df = await async_fetch_data_with_retry(ticker, period="1y")

        if df.empty or len(df) < 200:
            raise HTTPException(status_code=404, detail=f"Insufficient data for {ticker}")

        # Run Strategy (CPU bound, but fast for single ticker)
        # 4. The "HFT" Signal Refinement (Hurst Exponent) is included in IsaStrategy.analyze
        strategy = IsaStrategy()
        result_dict = strategy.analyze(df)

        # Construct Result
        curr_price = float(df['Close'].iloc[-1])
        signal = result_dict.get('signal', 'WAIT')

        # PnL Logic
        details = result_dict
        if entry_price:
             pnl_value = curr_price - entry_price
             pnl_pct = ((curr_price - entry_price) / entry_price) * 100
             details['pnl_value'] = pnl_value
             details['pnl_pct'] = pnl_pct

             # Override signal if holding
             if "ENTER" in signal or "WATCH" in signal:
                 signal = "✅ HOLD (Trend Active)"

             stop_exit = result_dict.get('trailing_exit_20d', 0)
             if curr_price <= stop_exit:
                 signal = "🛑 EXIT (Stop Hit)"

             if "AVOID" in signal:
                 signal = "🛑 EXIT (Downtrend)"

        result = ScanResult(
            ticker=ticker,
            price=curr_price,
            signal=signal,
            verdict=signal, # Mapping signal to verdict
            details=details
        )

        # Update Cache
        SCREENER_CACHE[cache_key] = result
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mount Flask App (for backward compatibility)
fastapi_app.mount("/", WSGIMiddleware(flask_app))

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    uvicorn.run(fastapi_app, host="0.0.0.0", port=port, log_level="debug" if debug else "info")
