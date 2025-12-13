from playwright.sync_api import Page, expect, sync_playwright
import time

def verify_hybrid_screener(page: Page):
    # 1. Arrange: Go to the app homepage (served by Flask)
    page.goto("http://localhost:5000")

    # 2. Act: Navigate to Screener
    try:
        page.locator("#nav-link-screener").first.click()
    except:
        page.get_by_role("link", name="Market Screener").first.click()

    # Wait for the heading
    page.get_by_role("heading", name="Stock & Option Screener").wait_for(timeout=5000)

    # 3. Find the "Hybrid (Trend+Cycle)" tab and click it
    hybrid_tab = page.locator("#tab-hybrid")
    hybrid_tab.wait_for()
    hybrid_tab.click()

    # 4. Assert: Check if the description changed to Hybrid
    expect(page.get_by_text("High Probability Setup")).to_be_visible()

    # 5. Run the screener
    run_btn = page.locator("#run-screener-btn")
    run_btn.click()

    # 6. Wait for results
    # Wait for any result row to appear
    # We saw "GILD" in the output
    try:
        page.get_by_text("GILD").first.wait_for(timeout=20000)
    except:
         # Try another ticker if GILD isn't there (it was in the curl output)
         page.locator("table").wait_for(timeout=20000)

    # Check for "Cycle" in the page content to confirm header
    if "Cycle" not in page.content():
        raise Exception("Cycle header missing from page content")

    # 7. Screenshot
    page.screenshot(path="/home/jules/verification/hybrid_screener.png")

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            verify_hybrid_screener(page)
            print("Verification successful!")
        except Exception as e:
            print(f"Verification failed: {e}")
            page.screenshot(path="/home/jules/verification/hybrid_screener_failed.png")
        finally:
            browser.close()
