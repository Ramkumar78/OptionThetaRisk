from playwright.sync_api import sync_playwright
import time

def verify_ui():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1280, 'height': 800})

        # Home
        print("Navigating to Home...")
        page.goto("http://localhost:5173/")
        time.sleep(2) # Wait for fade-in
        page.screenshot(path="verification/home.png")
        print("Home screenshot taken.")

        # Dashboard
        print("Navigating to Dashboard...")
        page.goto("http://localhost:5173/dashboard")
        time.sleep(2)
        page.screenshot(path="verification/dashboard.png")
        print("Dashboard screenshot taken.")

        # Screener
        print("Navigating to Screener...")
        page.goto("http://localhost:5173/screener")
        time.sleep(2)
        page.screenshot(path="verification/screener.png")
        print("Screener screenshot taken.")

        browser.close()

if __name__ == "__main__":
    verify_ui()
