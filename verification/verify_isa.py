
from playwright.sync_api import Page, expect, sync_playwright
import time

def verify_isa_screener(page: Page):
    # 1. Navigate to the app
    page.goto("http://127.0.0.1:5000")

    # 2. Click on "Screener" tab (It might be in navigation)
    # The default page might be Home.
    # Check navigation links
    # Assuming Screener is a link or we are already there?
    # Based on memory, "Screener" is the first action button or in nav.

    # Let's try to click "Screener" in the Nav or "Launch Screener" in Home.
    # Looking at Home.tsx (not read, but standard), usually there is a link.

    # Try to find "Screener" link
    page.get_by_role("link", name="Screener").first.click()

    # 3. Wait for Screener page
    page.get_by_text("Stock & Option Screener").wait_for()

    # 4. Click on "ISA Trend Follower" tab
    # Tabs are buttons in Screener.tsx
    page.get_by_text("ISA Trend Follower").click()

    # 5. Check if Region Selector is visible
    # Label "Region"
    region_select = page.get_by_label("Region")
    expect(region_select).to_be_visible()

    # 6. Run Screener
    # Mock API
    page.route("**/screen/isa*", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body='[{"ticker": "TEST", "price": 105.0, "signal": "ENTER LONG", "breakout_level": 100.0, "stop_loss_3atr": 95.0, "trailing_exit_20d": 98.0, "volatility_pct": 2.0, "risk_per_share": 5.0, "breakout_date": "2023-10-01"}]'
    ))

    page.get_by_role("button", name="Run Screener").click()

    # 7. Check Results
    # Wait for table
    page.get_by_text("Breakout Date").wait_for()

    # Check for date presence
    expect(page.get_by_text("2023-10-01")).to_be_visible()

    # Take screenshot
    page.screenshot(path="verification/isa_verification.png", full_page=True)

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            verify_isa_screener(page)
            print("Verification script ran successfully.")
        except Exception as e:
            print(f"Verification failed: {e}")
            page.screenshot(path="verification/isa_failure.png")
        finally:
            browser.close()
