from fastapi import FastAPI
from cachetools import TTLCache
import asyncio
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

# Import your heavy math/screener logic
from option_auditor.screener import screen_trend_followers_isa

app = FastAPI(title="Trade Auditor Guru")

# HEAVYWEIGHT CACHE: Stores results in RAM for 10 minutes
# This allows 10 users to share the exact same 'Heavy Math' results
global_scan_cache = TTLCache(maxsize=10, ttl=600)

def perform_heavy_market_scan(region: str):
    """
    Wrapper to run the synchronous screener logic.
    """
    return screen_trend_followers_isa(region=region)

@app.get("/api/screen/isa")
async def screen_isa(region: str = "US"):
    if region in global_scan_cache:
        return {"status": "success", "source": "cache", "data": global_scan_cache[region]}

    # Run the heavy math in a threadpool so it doesn't block other users
    results = await asyncio.to_thread(perform_heavy_market_scan, region)

    global_scan_cache[region] = results
    return {"status": "success", "source": "live", "data": results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
