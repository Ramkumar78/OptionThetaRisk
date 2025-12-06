import pytest

def test_theme_toggle_presence(authed_client):
    """
    Verifies that the theme toggle button exists in the base template.
    Fails if the theme feature is removed.
    """
    resp = authed_client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'id="theme-toggle"' in html, "Theme toggle button (id='theme-toggle') is missing!"
