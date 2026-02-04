import pytest
import requests

# Gracefully handle missing playwright to avoid collection errors in CI
try:
    from playwright.sync_api import Page, expect, Route
except ImportError:
    Page = None
    expect = None
    Route = None

def is_server_running(url):
    try:
        # We assume the health endpoint or root is available
        response = requests.get(f"{url}/health", timeout=2)
        return response.status_code == 200
    except Exception:
        return False

@pytest.mark.skipif(Page is None, reason="Playwright not installed")
def test_monte_carlo_simulation(page: Page, base_url):
    """
    Test the Monte Carlo simulation flow with mocked backend response.
    This ensures the UI works correctly without relying on external data providers.
    """
    if not base_url:
        pytest.skip("No base_url configured")

    # Remove trailing slash for consistency
    base_url = base_url.rstrip("/")

    if not is_server_running(base_url):
        pytest.skip(f"Server at {base_url} is not running. Start the server to run E2E tests.")

    # Mock the API response
    def handle_analyze(route: Route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body="""
            {
                "prob_ruin_50pct": 2.5,
                "median_final_equity": 15000,
                "initial_capital": 10000,
                "avg_return_pct": 50.0,
                "worst_case_return": -10.0,
                "best_case_return": 120.0,
                "median_drawdown": 15.0,
                "worst_case_drawdown": 30.0,
                "message": "Simulation complete (MOCKED)",
                "equity_curves": {
                    "p05": [10000, 9900, 9800, 10100],
                    "p25": [10000, 10100, 10200, 10300],
                    "p50": [10000, 10200, 10400, 10600],
                    "p75": [10000, 10300, 10600, 11000],
                    "p95": [10000, 10500, 11000, 12000]
                }
            }
            """
        )

    # Intercept the API call
    page.route("**/analyze/monte-carlo", handle_analyze)

    # Navigate to the Monte Carlo page
    # Using explicit full URL to avoid 'invalid URL' errors if context base_url is missing
    page.goto(f"{base_url}/monte-carlo")

    # Fill in the form
    page.locator("#ticker-input").fill("SPY")
    page.locator("#strategy-select").select_option("turtle")
    page.locator("#simulations-input").fill("100")

    # Run Simulation button
    page.get_by_role("button", name="Run Simulation").click()

    # Wait for results to appear
    # We expect "Risk of Ruin (>50% DD)" to appear.
    expect(page.get_by_text("Risk of Ruin (>50% DD)")).to_be_visible(timeout=10000)

    # Check for specific mocked values
    expect(page.get_by_text("2.5%")).to_be_visible() # prob_ruin_50pct
    expect(page.get_by_text("$15,000")).to_be_visible() # median_final_equity

    # Verify that the chart heading is visible
    expect(page.get_by_role("heading", name="Projected Equity Curves (Cone)")).to_be_visible()

    # Verify that Detailed Statistics are visible
    expect(page.get_by_role("heading", name="Detailed Statistics")).to_be_visible()
