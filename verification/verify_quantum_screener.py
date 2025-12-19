from playwright.sync_api import sync_playwright, Page, expect

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    # Increase viewport to ensure desktop view
    page = browser.new_page(viewport={"width": 1280, "height": 720})

    # Mock the Quantum Screener API response
    def handle_quantum_request(route):
        print("Intercepted quantum request")
        route.fulfill(
            status=200,
            content_type="application/json",
            body='''[
                {
                    "ticker": "AAPL",
                    "price": 150.00,
                    "hurst": 0.75,
                    "entropy": 1.2,
                    "verdict": "Persistent Trend",
                    "score": 95
                },
                {
                    "ticker": "TSLA",
                    "price": 200.00,
                    "hurst": 0.35,
                    "entropy": 1.8,
                    "verdict": "Mean Reversion",
                    "score": 40
                },
                {
                    "ticker": "MSFT",
                    "price": 300.00,
                    "hurst": 0.50,
                    "entropy": 1.6,
                    "verdict": "Random Walk",
                    "score": 50
                }
            ]'''
        )

    # Note: Vite proxies /screen calls to localhost:5000, but playwright intercepts browser requests.
    # The browser makes a request to /screen/quantum.
    page.route("**/screen/quantum*", handle_quantum_request)

    try:
        print("Navigating to http://localhost:5173/screener")
        page.goto("http://localhost:5173/")

        print("Waiting for nav links")
        page.wait_for_selector("text=Screener", timeout=5000)
        page.click("text=Screener")

        print("On Screener page, waiting for Strategies")
        page.wait_for_selector("text=Strategies", timeout=5000)

        print("Clicking Quantum Physics tab")
        page.click("text=Quantum Physics")

        # Check if the title updated
        expect(page.locator("h1")).to_contain_text("Quantum Entanglement")

        print("Clicking Run Screener")
        page.click("button:has-text('Run Screener')")

        print("Waiting for AAPL result")
        page.wait_for_selector("text=AAPL", timeout=5000)

        # Take screenshot
        page.screenshot(path="verification/quantum_screener.png", full_page=True)
        print("Screenshot taken")

    except Exception as e:
        print(f"Error: {e}")
        page.screenshot(path="verification/error.png")
    finally:
        browser.close()

with sync_playwright() as playwright:
    run(playwright)
