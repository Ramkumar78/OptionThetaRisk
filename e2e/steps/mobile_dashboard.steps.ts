import { Given, When, Then } from '@cucumber/cucumber';
import { actorCalled, Wait, Duration } from '@serenity-js/core';
import { PageElement, By, isVisible, Click, Navigate } from '@serenity-js/web';
import { BrowseTheWebWithPlaywright } from '@serenity-js/playwright';
import { Ensure } from '@serenity-js/assertions';

Given('I am using a mobile device', async () => {
    const actor = actorCalled('Alice');
    const ability = BrowseTheWebWithPlaywright.as(actor);
    const page = await ability.currentPage();
    const nativePage = await (page as any).nativePage();
    await nativePage.setViewportSize({ width: 375, height: 667 });
});

When('I visit the dashboard page', async () => {
     await actorCalled('Alice').attemptsTo(
        Navigate.to('/dashboard')
    );
});

Then('I should see the dashboard content', async () => {
    const header = PageElement.located(By.css('h1'))
        .describedAs('Dashboard Header');

    await actorCalled('Alice').attemptsTo(
        Wait.upTo(Duration.ofSeconds(30)).until(header, isVisible()),
        Ensure.that(header, isVisible())
    );
});

Then('I should see the Quick Trade button in the mobile menu', async () => {
    const menuButton = PageElement.located(By.id('mobile-menu-toggle'))
        .describedAs('Mobile Menu Toggle');

    await actorCalled('Alice').attemptsTo(
        Wait.upTo(Duration.ofSeconds(5)).until(menuButton, isVisible()),
        Click.on(menuButton)
    );

    const quickTradeBtnText = PageElement.located(By.xpath("//div[@id='navbar-sticky']//button[contains(text(), 'Quick Trade')]"))
        .describedAs('Quick Trade Button Mobile');

    await actorCalled('Alice').attemptsTo(
        Wait.upTo(Duration.ofSeconds(5)).until(quickTradeBtnText, isVisible())
    );
});
