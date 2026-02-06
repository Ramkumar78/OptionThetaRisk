import { BeforeAll, AfterAll, setDefaultTimeout } from '@cucumber/cucumber';
import { configure, engage, Cast } from '@serenity-js/core';
import { BrowseTheWebWithPlaywright } from '@serenity-js/playwright';
import * as playwright from 'playwright';

// Set default timeout to 30 seconds
setDefaultTimeout(30 * 1000);

let browser: playwright.Browser;

BeforeAll(async () => {
    configure({
        crew: [
            '@serenity-js/console-reporter',
        ],
    });
});

BeforeAll(async () => {
    // Launch the browser
    browser = await playwright.chromium.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox'] // Useful for CI environments
    });

    const baseUrl = process.env.BASE_URL || 'http://localhost:5000';

    // Engage the actors
    engage(
        Cast.where(actor => actor.whoCan(
            BrowseTheWebWithPlaywright.using(browser, {
                baseURL: baseUrl,
            })
        ))
    );
});

AfterAll(async () => {
    if (browser) {
        await browser.close();
    }
});
