from playwright.sync_api import sync_playwright, expect

def run_verification():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Navigate to the Screener page
        page.goto("http://127.0.0.1:5000/screener")
        page.wait_for_load_state("networkidle")

        # Check Alpha 101 strategy selection
        strategy_select = page.locator("#strategy-select")
        strategy_select.select_option("alpha101")

        # Check Timeframe selection
        timeframe_select = page.locator("#timeframe-select")

        # Verify 1mo option exists
        # Option text is "Monthly (Macro)"
        # Option value is "1mo"

        # We can check if the option exists
        option_1mo = timeframe_select.locator("option[value='1mo']")
        expect(option_1mo).to_have_count(1)
        expect(option_1mo).to_have_text("Monthly (Macro)")

        # Select it
        timeframe_select.select_option("1mo")

        # Take screenshot
        page.screenshot(path="alpha101_timeframe_verification.png")

        browser.close()

if __name__ == "__main__":
    run_verification()
