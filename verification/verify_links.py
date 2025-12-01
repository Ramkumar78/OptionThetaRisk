from playwright.sync_api import sync_playwright

def verify_homepage_links():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Navigate to the homepage
        # Assuming app is running on localhost:5000 as per README
        page.goto("http://127.0.0.1:5000")

        # Verify Contact link
        contact_link = page.get_by_role("link", name="Contact")
        if contact_link.is_visible() and contact_link.get_attribute("href") == "mailto:shriram2222@gmail.com":
            print("Contact link verification passed.")
        else:
            print("Contact link verification failed.")

        # Verify GitHub link
        # The link text is still "GitHub" as per requirement
        github_link = page.get_by_role("link", name="GitHub", exact=True)
        expected_url = "https://github.com/Ramkumar78/OptionThetaRisk/blob/main/README.md"

        if github_link.is_visible() and github_link.get_attribute("href") == expected_url:
             print("GitHub link verification passed.")
        else:
             print(f"GitHub link verification failed. Found: {github_link.get_attribute('href')}")

        # Take a screenshot of the navbar area
        page.screenshot(path="verification/homepage_navbar.png")

        browser.close()

if __name__ == "__main__":
    verify_homepage_links()
