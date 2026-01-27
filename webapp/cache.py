import time
from collections import OrderedDict

# --- MEMORY SAFE CACHE (LRU) ---
class LRUCache:
    def __init__(self, capacity: int, ttl_seconds: int):
        self.cache = OrderedDict()
        self.capacity = capacity
        self.ttl = ttl_seconds

    def get(self, key):
        if key not in self.cache:
            return None

        value, timestamp = self.cache[key]

        # Check Expiry
        if time.time() - timestamp > self.ttl:
            self.cache.pop(key)
            return None

        # Move to end (Recently Used)
        self.cache.move_to_end(key)
        return value

    def set(self, key, value):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = (value, time.time())
        self.cache.move_to_end(key)

        # Evict if full
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)

# Init Cache (Max 50 results, 10 min expiry)
screener_cache = LRUCache(capacity=50, ttl_seconds=600)

def get_cached_screener_result(key):
    return screener_cache.get(key)

def cache_screener_result(key, data):
    screener_cache.set(key, data)
