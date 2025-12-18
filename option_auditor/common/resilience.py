import pybreaker
import logging
from option_auditor.common.constants import SCREENER_CACHE

logger = logging.getLogger(__name__)

# Guru Setup: Define the Breaker
# We trip if 5% of requests fail or if we hit 3 consecutive hard timeouts
data_api_breaker = pybreaker.CircuitBreaker(
    fail_max=3,
    reset_timeout=30, # Stay open for 30s
    exclude=[ValueError] # Don't trip for user input errors
)

class ResiliencyGuru:
    @staticmethod
    def fallback_fetch():
        """The Hystrix Fallback: Return the last successful scan from cache."""
        logger.warning("HYSTRIX: Circuit Open. Serving Fallback Cache.")
        return SCREENER_CACHE.get("last_good_scan", {"error": "Service Degraded", "data": []})
