
import os
import shutil
import pytest
from webapp.app import create_app

@pytest.fixture()
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
    })

    # Clean up the reports folder before each test
    report_folder = app.config["REPORT_FOLDER"]
    if os.path.exists(report_folder):
        shutil.rmtree(report_folder, ignore_errors=True)
    os.makedirs(report_folder, exist_ok=True)

    yield app

    # Final cleanup after test
    if os.path.exists(report_folder):
        shutil.rmtree(report_folder, ignore_errors=True)

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
