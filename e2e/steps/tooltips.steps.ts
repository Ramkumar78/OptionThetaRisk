import { Then } from '@cucumber/cucumber';
import { actorCalled, Wait } from '@serenity-js/core';
import { PageElement, By, Hover, isVisible } from '@serenity-js/web';

Then('they should see the Mindset Meter tooltip when hovering', async () => {
    const mindsetMeterLabel = PageElement.located(By.xpath("//h2[contains(text(), 'Mindset Meter')]"))
        .describedAs('Mindset Meter label');

    await actorCalled('Alice').attemptsTo(
        Hover.over(mindsetMeterLabel),
        Wait.until(
            PageElement.located(By.xpath("//*[contains(text(), 'A score evaluating your trading behavior')]")),
            isVisible()
        )
    );
});

Then('they should see the Regime tooltip when hovering', async () => {
    // Note: The text might be "SPY Regime" or similar depending on selected asset.
    // Dashboard.tsx: {selectedAsset.symbol} Regime
    // Default is SPY, so "SPY Regime" or just "Regime" if using contains.
    // Dashboard.tsx: <h2 ...>{selectedAsset.symbol} Regime</h2>
    // So text is "SPY Regime".
    // Using contains(text(), 'Regime') is safe.

    const regimeLabel = PageElement.located(By.xpath("//h2[contains(text(), 'Regime')]"))
        .describedAs('Regime label');

    await actorCalled('Alice').attemptsTo(
        Hover.over(regimeLabel),
        Wait.until(
             PageElement.located(By.xpath("//*[contains(text(), 'The current broad market trend')]")),
             isVisible()
        )
    );
});
