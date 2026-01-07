import os
import time
from playwright.sync_api import sync_playwright

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("http://localhost:5000/screener")
    time.sleep(5) # Wait for load

    # Wait for table
    try:
        page.wait_for_selector("table", timeout=5000)
    except:
        print("Table not found (maybe loading or empty)")

    page.screenshot(path="frontend_verification.png")
    browser.close()

with sync_playwright() as playwright:
    run(playwright)
