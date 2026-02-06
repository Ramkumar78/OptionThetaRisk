from playwright.sync_api import Page, expect, sync_playwright
import time

def test_mindset_checklist(page: Page):
    print("Navigating to Home...")
    # 1. Go to Home page
    page.goto("http://localhost:5173/")

    # Wait for page to load
    page.wait_for_timeout(2000)

    print("Clicking Pre-Flight...")
    # Click Pre-Flight button
    page.get_by_role("button", name="Pre-Flight").click()

    print("Verifying Modal...")
    # 3. Verify Modal appears
    expect(page.get_by_text("Mindset Check")).to_be_visible()

    # 4. Screenshot
    print("Taking screenshot...")
    page.screenshot(path="verification/mindset_check.png")

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            test_mindset_checklist(page)
            print("Success!")
        except Exception as e:
            print(f"Error: {e}")
            page.screenshot(path="verification/error.png")
        finally:
            browser.close()
