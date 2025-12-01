from playwright.sync_api import sync_playwright
import time
import os

def generate_sample_csv():
    content = (
        "Time,Underlying Symbol,Quantity,Action,Price,Commissions and Fees,Expiration Date,Strike Price,Option Type\n"
        "2025-01-01 10:00,MSFT,1,Buy to Open,1.00,0.10,2025-02-21,500,Put\n"
        "2025-01-03 10:00,MSFT,1,Sell to Close,1.50,0.10,2025-02-21,500,Put\n"
        "2025-01-02 10:00,AAPL,1,Sell to Open,2.00,0.10,2025-02-21,200,Call\n"
        "2025-01-04 10:00,AAPL,1,Buy to Close,1.00,0.10,2025-02-21,200,Call\n"
    )
    with open("sample_trades.csv", "w") as f:
        f.write(content)
    return os.path.abspath("sample_trades.csv")

def verify_ui():
    csv_path = generate_sample_csv()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # Go to upload page
            page.goto("http://127.0.0.1:5000")

            # Click expand metrics
            page.click('button:has-text("Optional: Account Metrics")')
            page.wait_for_timeout(500)

            # Fill form
            page.fill('input[name="account_size_start"]', "10000")

            # Directly set input file without waiting for filechooser event
            # (Use set_input_files on the input element locator)
            page.locator('input[name="csv"]').set_input_files(csv_path)

            # Submit
            page.click('button[type="submit"]')

            # Wait for results page elements
            # We look for "Net PnL" which is in the new cards
            page.wait_for_selector("text=Net PnL", timeout=30000)

            # Also check for "Range:" if present
            # page.wait_for_selector("text=Range:", timeout=5000) # Optional check

            # Screenshot the results
            page.screenshot(path="/home/jules/verification/results_page.png", full_page=True)
            print("Verification screenshot saved to /home/jules/verification/results_page.png")

        except Exception as e:
            print(f"Verification failed: {e}")
            page.screenshot(path="/home/jules/verification/error.png", full_page=True)
            raise
        finally:
            browser.close()

if __name__ == "__main__":
    verify_ui()
