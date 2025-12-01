import sys
import os
import time
from playwright.sync_api import sync_playwright

def verify_dashboard():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # Wait for server
            time.sleep(2)

            # Go to upload page
            page.goto("http://localhost:5000/")
            print("Loaded homepage")

            # Create a dummy CSV with a ROLL - using proper newline characters
            with open("verification/dummy_roll.csv", "w") as f:
                f.write("Time,Action,Underlying Symbol,Description,Quantity,Price,Commissions and Fees,Expiration Date,Strike Price,Option Type\n")
                f.write("2023-01-01 10:00,SELL_TO_OPEN,SPY,Call,1,5.0,1.0,2023-01-20,400,CALL\n")
                f.write("2023-01-10 10:00,BUY_TO_CLOSE,SPY,Call,1,4.0,1.0,2023-01-20,400,CALL\n")
                f.write("2023-01-10 10:02,SELL_TO_OPEN,SPY,Call,1,6.0,1.0,2023-02-17,400,CALL\n")
                f.write("2023-01-20 10:00,BUY_TO_CLOSE,SPY,Call,1,1.0,1.0,2023-02-17,400,CALL\n")

            # Upload
            page.set_input_files("input[type='file']", "verification/dummy_roll.csv")
            page.click("button[type='submit']")
            print("Uploaded file")

            # Wait for results
            page.wait_for_selector("h3:has-text('Audit Summary')")
            print("Results page loaded")

            # Check for Leakage Report
            if page.locator("h3:has-text('The Leakage Report')").count() > 0:
                print("Leakage Report found")
            else:
                print("Leakage Report NOT found")
                sys.exit(1)

            # Check for Theta Curve Chart
            if page.locator("#thetaCurveChart").count() > 0:
                print("Theta Curve Chart found")
            else:
                print("Theta Curve Chart NOT found")
                sys.exit(1)

            # Take screenshot
            page.screenshot(path="verification/results_leakage.png", full_page=True)
            print("Screenshot saved")

        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
        finally:
            browser.close()

if __name__ == "__main__":
    verify_dashboard()
