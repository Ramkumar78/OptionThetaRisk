
from playwright.sync_api import sync_playwright, expect

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()

    # Mock the API response
    def handle_screen_isa(route):
        print("Intercepted /screen/isa")
        route.fulfill(
            status=200,
            content_type="application/json",
            body='''[
              {
                "ticker": "AAPL",
                "company_name": "Apple Inc.",
                "price": 150.00,
                "pct_change_1d": 1.2,
                "signal": "🚀 ENTER LONG (50d Breakout)",
                "breakout_level": 148.00,
                "stop_loss_3atr": 140.00,
                "trailing_exit_20d": 135.00,
                "volatility_pct": 2.5,
                "atr_20": 3.75,
                "risk_per_share": 10.00,
                "dist_to_stop_pct": 6.66,
                "tharp_verdict": "✅ SAFE",
                "max_position_size": "4.0%",
                "breakout_date": "2023-10-01"
              }
            ]'''
        )

    # Intercept API calls
    page.route("**/screen/isa*", handle_screen_isa)

    # Navigate to app screener page directly
    page.goto("http://127.0.0.1:5000/screener")

    # Click ISA Trend Follower tab
    # The tab id is 'tab-isa'
    # Wait for it to be visible first
    page.wait_for_selector("#tab-isa", state="visible")
    page.click("#tab-isa")

    # Click Run Screener
    page.click("#run-screener-btn")

    # Wait for results table
    # Expect a cell with "Apple Inc."
    page.get_by_text("Apple Inc.").wait_for()

    # Verify new columns
    expect(page.get_by_text("Tharp Verdict")).to_be_visible()
    expect(page.get_by_text("Max Size")).to_be_visible()
    expect(page.get_by_text("✅ SAFE")).to_be_visible()
    expect(page.get_by_text("4.0%")).to_be_visible()

    # Screenshot
    page.screenshot(path="verification/isa_tharp.png")
    print("Screenshot saved to verification/isa_tharp.png")

    browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
