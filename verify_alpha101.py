from playwright.sync_api import sync_playwright, expect

def run_verification():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Navigate to the Screener page
        page.goto("http://127.0.0.1:5000/screener")

        # Wait for the page to load
        page.wait_for_load_state("networkidle")

        # Locate the strategy dropdown
        strategy_select = page.locator("#strategy-select")

        # Click to open dropdown (if it was custom, but it's a select element)
        # Select 'Alpha 101'
        strategy_select.select_option("alpha101")

        # Verify that the description updated
        # "Kakushadze Alpha #101"
        expect(page.get_by_text("Kakushadze Alpha #101")).to_be_visible()

        # Verify the legend updated
        expect(page.get_by_text("Alpha Value")).to_be_visible()
        expect(page.get_by_text("Range from -1.0 to 1.0")).to_be_visible()

        # Take screenshot
        page.screenshot(path="alpha101_verification_v2.png")

        browser.close()

if __name__ == "__main__":
    run_verification()
