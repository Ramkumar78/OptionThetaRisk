import { Then, When } from '@cucumber/cucumber';
import { actorCalled, Wait, Duration } from '@serenity-js/core';
import { PageElement, By, Click, Enter, isVisible } from '@serenity-js/web';
import { Ensure } from '@serenity-js/assertions';

When('they navigate to the Backtester page', async () => {
    await actorCalled('Alice').attemptsTo(
        Click.on(PageElement.located(By.id('nav-link-backtest')).describedAs('Backtest link'))
    );
});

When('they enter symbol {string}', async (symbol: string) => {
    await actorCalled('Alice').attemptsTo(
        Enter.theValue(symbol).into(PageElement.located(By.id('ticker-input')).describedAs('Ticker input')),
        Click.on(PageElement.located(By.css('button[type="submit"]')).describedAs('Run Backtest button'))
    );
});

Then('they should see the Result graph', async () => {
    // Wait for result to appear. It might take some time as backtest runs.
    // The "Equity Curve" header appears when result is present.
    const resultHeader = PageElement.located(By.xpath("//h3[contains(text(), 'Equity Curve')]"))
        .describedAs('Equity Curve header');

    await actorCalled('Alice').attemptsTo(
        Wait.upTo(Duration.ofSeconds(30)).until(resultHeader, isVisible()),
        Ensure.that(resultHeader, isVisible())
    );
});
