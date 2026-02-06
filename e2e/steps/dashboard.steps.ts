import { Given, Then } from '@cucumber/cucumber';
import { actorCalled, Wait } from '@serenity-js/core';
import { Navigate, PageElement, By, Text, isVisible } from '@serenity-js/web';
import { Ensure, includes } from '@serenity-js/assertions';

Given('the user is on the TradeGuardian home page', async () => {
    await actorCalled('Alice').attemptsTo(
        Navigate.to('/')
    );
});

Then('they should see the brand {string}', async (brand: string) => {
    const brandElement = PageElement.located(By.id('nav-logo-link'))
        .describedAs('the brand logo');

    await actorCalled('Alice').attemptsTo(
        Wait.until(brandElement, isVisible()),
        Ensure.that(Text.of(brandElement), includes(brand))
    );
});

Then('they should see the {string} display', async (text: string) => {
    // using XPath to find element containing text
    const elementWithText = PageElement.located(By.xpath(`//*[contains(text(), '${text}')]`))
        .describedAs(`an element containing text "${text}"`);

    await actorCalled('Alice').attemptsTo(
        Wait.until(elementWithText, isVisible()),
        Ensure.that(Text.of(elementWithText), includes(text))
    );
});
