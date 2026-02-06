import { chromium, devices } from 'playwright';

(async () => {
  console.log('📱 Starting Mobile Responsiveness Check...');
  const browser = await chromium.launch();
  const context = await browser.newContext({
    ...devices['iPhone 13'],
  });
  const page = await context.newPage();

  page.on('console', msg => console.log('PAGE LOG:', msg.text()));
  page.on('pageerror', exception => console.log(`PAGE ERROR: "${exception}"`));

  try {
    const url = 'http://localhost:5000/';
    console.log(`Navigating to ${url}...`);
    await page.goto(url);

    // Verify Home
    await page.waitForSelector('text=Institutional-Grade', { timeout: 10000 });
    console.log('✅ Home Page Loaded');

    // Navigate to Dashboard via client-side routing to avoid hitting API endpoint
    console.log('Clicking "Launch Dashboard"...');
    await page.click('text=Launch Dashboard');

    // 1. Check Header
    await page.waitForSelector('text=Command Center', { timeout: 20000 });
    console.log('✅ "Command Center" header visible');

    // 2. Check Mindset Meter (existing)
    await page.waitForSelector('text=Mindset Meter');
    console.log('✅ "Mindset Meter" visible');

    // 3. Check Trading Mood (New Widget)
    await page.waitForSelector('text=Trading Mood');
    console.log('✅ "Trading Mood" widget visible');

    // 4. Check Quick Actions Sidebar Toggle
    const toggle = await page.waitForSelector('[aria-label="Quick Trade"]');
    if (await toggle.isVisible()) {
        console.log('✅ "Quick Add" toggle visible');
    } else {
        throw new Error('"Quick Add" toggle not visible');
    }

    // 5. Open Sidebar
    await toggle.click();
    await page.waitForSelector('text=Quick Trade Entry');
    console.log('✅ Sidebar opened successfully');

    console.log('🎉 Mobile Check Passed!');
  } catch (error) {
    console.error('❌ Mobile Check Failed:', error);
    await page.screenshot({ path: 'e2e_failure_2.png' });
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
