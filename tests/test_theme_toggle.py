
import os
import shutil
import pytest
import time
import gc
from webapp.app import create_app

@pytest.fixture()
def app():
    app = create_app(testing=True)
    app.config.update({
        "WTF_CSRF_ENABLED": False,
    })

    # Clean up the reports DB before each test
    db_path = os.path.join(app.instance_path, "reports.db")
    for _ in range(3):
        try:
            if os.path.exists(db_path):
                os.remove(db_path)
            break
        except PermissionError:
            gc.collect()
            time.sleep(0.1)

    # Initialize DB for testing
    from webapp.storage import LocalStorage
    storage = LocalStorage(db_path)

    yield app

    # Final cleanup after test
    storage.close()
    del storage
    gc.collect()

    for _ in range(5):
        try:
            if os.path.exists(db_path):
                os.remove(db_path)
            break
        except PermissionError:
            time.sleep(0.1)

def test_theme_toggle_presence(app):
    """
    Verifies that the theme toggle button exists in the base template.
    Fails if the theme feature is removed.
    """
    client = app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    # We look for the specific ID of the toggle button
    assert 'id="theme-toggle"' in html, "Theme toggle button (id='theme-toggle') is missing!"
