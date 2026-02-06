from playwright.sync_api import sync_playwright, expect
import time

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    try:
        page.goto("http://localhost:5173/")

        # Wait for page to load
        page.wait_for_selector("text=TradeGuardian")

        # Ensure we start in a known state (force light mode if needed, or just toggle)
        # Check current state
        html = page.locator("html")
        classes = html.get_attribute("class") or ""
        print(f"Initial classes: {classes}")

        # Take screenshot of initial state
        page.screenshot(path="verification/initial.png")

        # Find theme toggle button
        toggle_btn = page.locator("#theme-toggle")
        toggle_btn.click()

        # Wait for a moment for transition
        time.sleep(1)

        classes_after = html.get_attribute("class") or ""
        print(f"Classes after toggle: {classes_after}")

        # Take screenshot of toggled state
        page.screenshot(path="verification/toggled.png")

        # Toggle back
        toggle_btn.click()
        time.sleep(1)
        page.screenshot(path="verification/back_original.png")

    except Exception as e:
        print(f"Error: {e}")
        page.screenshot(path="verification/error.png")
    finally:
        browser.close()

with sync_playwright() as playwright:
    run(playwright)
