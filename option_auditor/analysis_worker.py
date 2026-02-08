import multiprocessing
import uuid
import logging
import os
import json
import tempfile
from typing import Dict, Any, List, Optional
from option_auditor.monte_carlo_simulator import run_simple_monte_carlo
from option_auditor.risk_analyzer import calculate_black_swan_impact

logger = logging.getLogger(__name__)

# Directory for task results
TASK_DIR = os.path.join(tempfile.gettempdir(), "option_auditor_tasks")
os.makedirs(TASK_DIR, exist_ok=True)

def _save_result(task_id: str, data: Dict):
    """Saves result to a JSON file atomically."""
    filepath = os.path.join(TASK_DIR, f"{task_id}.json")
    try:
        # Write to temp file first
        fd, temp_path = tempfile.mkstemp(dir=TASK_DIR, text=True)
        with os.fdopen(fd, 'w') as f:
            json.dump(data, f)
        # Atomic rename
        os.replace(temp_path, filepath)
    except Exception as e:
        logger.error(f"Failed to save task result {task_id}: {e}")

def _load_result(task_id: str) -> Dict:
    """Loads result from JSON file."""
    filepath = os.path.join(TASK_DIR, f"{task_id}.json")
    if not os.path.exists(filepath):
        return {"status": "not_found"}
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load task result {task_id}: {e}")
        return {"status": "error", "message": str(e)}

def _run_monte_carlo_task(task_id: str, strategies_data: List[Dict], start_equity: float):
    """
    Worker function to run Monte Carlo simulation.
    """
    try:
        logger.info(f"Worker: Starting Monte Carlo task {task_id}")
        result = run_simple_monte_carlo(strategies_data, start_equity=start_equity)
        _save_result(task_id, {"status": "completed", "result": result})
        logger.info(f"Worker: Completed Monte Carlo task {task_id}")
    except Exception as e:
        logger.error(f"Worker: Monte Carlo task {task_id} failed: {e}")
        _save_result(task_id, {"status": "failed", "error": str(e)})

def _run_black_swan_task(task_id: str, open_positions_data: List[Dict], prices: Dict[str, float]):
    """
    Worker function to run Black Swan simulation.
    """
    try:
        logger.info(f"Worker: Starting Black Swan task {task_id}")
        result = calculate_black_swan_impact(open_positions_data, prices)

        # Convert StressTestResult objects to dicts for JSON serialization
        serialized_result = []
        if isinstance(result, list):
            for item in result:
                if hasattr(item, '__dict__'):
                    serialized_result.append(item.__dict__)
                else:
                    serialized_result.append(item)
        else:
            serialized_result = result

        _save_result(task_id, {"status": "completed", "result": serialized_result})
        logger.info(f"Worker: Completed Black Swan task {task_id}")
    except Exception as e:
        logger.error(f"Worker: Black Swan task {task_id} failed: {e}")
        _save_result(task_id, {"status": "failed", "error": str(e)})

class AnalysisWorker:
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        # Use a small pool, e.g., 2 workers, to avoid hogging CPU
        # No Manager needed anymore
        self.pool = multiprocessing.Pool(processes=2)
        logger.info("AnalysisWorker initialized with 2 processes.")

    def submit_monte_carlo(self, strategies_data: List[Dict], start_equity: float) -> str:
        task_id = f"mc_{uuid.uuid4().hex}"
        _save_result(task_id, {"status": "processing"})
        try:
            self.pool.apply_async(
                _run_monte_carlo_task,
                args=(task_id, strategies_data, start_equity)
            )
        except Exception as e:
             logger.error(f"Failed to submit Monte Carlo task: {e}")
             _save_result(task_id, {"status": "failed", "error": str(e)})
        return task_id

    def submit_black_swan(self, open_positions_data: List[Dict], prices: Dict[str, float]) -> str:
        task_id = f"bs_{uuid.uuid4().hex}"
        _save_result(task_id, {"status": "processing"})
        try:
            self.pool.apply_async(
                _run_black_swan_task,
                args=(task_id, open_positions_data, prices)
            )
        except Exception as e:
             logger.error(f"Failed to submit Black Swan task: {e}")
             _save_result(task_id, {"status": "failed", "error": str(e)})
        return task_id

    def get_result(self, task_id: str) -> Dict:
        return _load_result(task_id)

    def shutdown(self):
        if self.pool:
            self.pool.close()
            self.pool.join()
