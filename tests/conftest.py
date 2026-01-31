
import pytest
from unittest.mock import patch

@pytest.fixture(autouse=True)
def prevent_background_scheduler():
    """Prevent the background scheduler from starting during tests."""
    with patch('webapp.services.scheduler_service.start_scheduler') as mock:
        yield mock
