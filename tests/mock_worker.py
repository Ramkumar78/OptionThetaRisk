from typing import Any, Callable, Tuple

class SynchronousPool:
    """Mock for multiprocessing.Pool that runs tasks synchronously."""
    def __init__(self, processes=None):
        pass

    def apply_async(self, func: Callable, args: Tuple = (), kwds: dict = None, callback: Callable = None, error_callback: Callable = None):
        if kwds is None:
            kwds = {}
        try:
            func(*args, **kwds)
        except Exception as e:
            if error_callback:
                error_callback(e)
            else:
                # Log or re-raise if needed, but worker functions usually catch their own errors
                print(f"SyncPool Error: {e}")

        # Return a dummy AsyncResult if needed, but AnalysisWorker doesn't use it
        return None

    def close(self):
        pass

    def join(self):
        pass
