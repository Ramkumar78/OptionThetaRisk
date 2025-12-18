from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
import logging
from option_auditor.models import StockCheckRequest
from option_auditor import screener
from option_auditor.common.resilience import data_api_breaker
from option_auditor.common.constants import TICKER_NAMES
import pybreaker

# Logger
logger = logging.getLogger(__name__)

app = FastAPI(title="OptionThetaRisk Guru API")

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "fastapi-core"}

@app.get("/api/screener/status")
async def get_breaker_status():
    """
    Returns the real-time status of the Circuit Breaker.
    """
    return {
        "api_health": data_api_breaker.current_state,
        "is_fallback": data_api_breaker.current_state == 'open'
    }

@app.post("/api/screen/isa/check")
async def check_isa_stock(payload: StockCheckRequest):
    """
    Async implementation of the ISA Stock Check.
    Uses run_in_threadpool to handle synchronous yfinance/pandas calls.
    """

    # 1. Resolve Ticker (Synchronous helper)
    ticker_query = payload.ticker.strip()
    if not ticker_query:
        raise HTTPException(status_code=400, detail="No ticker provided")

    try:
        # We wrap resolve_ticker logic here or call it
        # Since resolve_ticker is pure logic/memory lookup (TICKER_NAMES), it's fast enough to run in main thread,
        # but screen_trend_followers_isa is heavy (I/O).

        # We can use the screener.resolve_ticker helper
        resolved_ticker = screener.resolve_ticker(ticker_query)
        if not resolved_ticker:
            resolved_ticker = ticker_query.upper()

        # 2. Execute with Circuit Breaker and Threadpool
        # Uses refactored helper from screener.py to keep controller clean.
        result = await run_in_threadpool(
            data_api_breaker.call,
            screener.screen_single_ticker_with_pnl,
            resolved_ticker,
            payload.entry_price
        )

        if not result:
             raise HTTPException(status_code=404, detail=f"No data found for {resolved_ticker}")

        return {"status": "success", "data": result}

    except HTTPException:
        raise
    except pybreaker.CircuitBreakerError:
        # Fallback logic
        logger.warning(f"Circuit Breaker Open for {ticker_query}")
        return {"status": "degraded", "message": "API Throttled - Using Cache"}

    except Exception as e:
        logger.error(f"Error checking stock {ticker_query}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
