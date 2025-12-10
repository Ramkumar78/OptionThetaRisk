from playwright.sync_api import Page, expect, sync_playwright
import time

def verify_title_and_icon(page: Page):
    # 1. Arrange: Go to the frontend
    page.goto("http://localhost:5173")

    # Wait for the page to load
    page.wait_for_load_state("networkidle")

    # 2. Assert Title
    print("Checking title...")
    expect(page).to_have_title("Trade Auditor")
    print("Title verified.")

    # 3. Assert Navigation Logo
    print("Checking navbar logo...")
    logo = page.locator("#nav-logo-img")
    expect(logo).to_be_visible()

    # Check if the image loaded (naturalWidth > 0)
    is_loaded = page.evaluate("document.getElementById('nav-logo-img').naturalWidth > 0")
    if is_loaded:
        print("Logo image loaded successfully.")
    else:
        print("Logo image FAILED to load (naturalWidth == 0).")
        raise AssertionError("Logo image failed to load")

    # 4. Assert Favicon (Browser side check, tricky with Playwright directly, but we can check the DOM)
    print("Checking favicon link in DOM...")
    favicon = page.locator("link[rel='icon']")
    expect(favicon).to_have_attribute("href", "/static/img/logo.png")
    print("Favicon link verified.")

    # 5. Screenshot
    page.screenshot(path="/home/jules/verification/verification.png")
    print("Screenshot saved.")

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            verify_title_and_icon(page)
        except Exception as e:
            print(f"Verification Failed: {e}")
            page.screenshot(path="/home/jules/verification/failure.png")
            exit(1)
        finally:
            browser.close()
