import { Given, When, Then, DataTable } from '@cucumber/cucumber';
import { actorCalled, Wait, Duration } from '@serenity-js/core';
import { Navigate, PageElement, By, Enter, Click, Text, isVisible } from '@serenity-js/web';
import { Ensure, includes } from '@serenity-js/assertions';

Given('the user is on the Journal page', async () => {
    await actorCalled('Alice').attemptsTo(
        Navigate.to('/'),
        Wait.upTo(Duration.ofSeconds(15)).until(PageElement.located(By.id('nav-link-journal')), isVisible()),
        Click.on(PageElement.located(By.id('nav-link-journal'))),
        Wait.upTo(Duration.ofSeconds(15)).until(PageElement.located(By.id('journal-symbol')), isVisible())
    );
});

When('they enter the following trade details:', async (dataTable: DataTable) => {
    const data = dataTable.rowsHash();
    const symbol = data['Symbol'];
    const strategy = data['Strategy'];
    const pnl = data['PnL'];
    const notes = data['Notes'];

    await actorCalled('Alice').attemptsTo(
        Enter.theValue(symbol).into(PageElement.located(By.id('journal-symbol'))),
        Enter.theValue(strategy).into(PageElement.located(By.id('journal-strategy'))),
        Enter.theValue(pnl).into(PageElement.located(By.id('journal-pnl'))),
        Enter.theValue(notes).into(PageElement.located(By.id('journal-notes')))
    );
});

When('they click {string}', async (buttonText: string) => {
    // Handling "Add Entry" specifically if needed, or generic button click by text
    // But since we have specific IDs, let's map text to ID or find by text.
    // The button has id "journal-submit-btn" and text "Add Entry".

    let target;
    if (buttonText === 'Add Entry') {
        target = PageElement.located(By.id('journal-submit-btn'));
    } else {
        target = PageElement.located(By.xpath(`//button[contains(text(), '${buttonText}')]`));
    }

    await actorCalled('Alice').attemptsTo(
        Click.on(target)
    );
});

Then('the {string} modal should open', async (modalTitle: string) => {
    const modalHeader = PageElement.located(By.xpath(`//*[contains(text(), '${modalTitle}')]`));

    await actorCalled('Alice').attemptsTo(
        Wait.until(modalHeader, isVisible())
    );
});

When('they confirm the mindset checklist', async () => {
    // Questions:
    // 1. Am I chasing a loss? -> No
    // 2. Is this within my risk plan? -> Yes
    // 3. Am I calm? -> Yes

    // Q1 No
    const q1No = PageElement.located(By.xpath(`//div[p[contains(text(), '1. Am I chasing')]]//label[span[text()='No']]`));
    // Q2 Yes
    const q2Yes = PageElement.located(By.xpath(`//div[p[contains(text(), '2. Is this within')]]//label[span[text()='Yes']]`));
    // Q3 Yes
    const q3Yes = PageElement.located(By.xpath(`//div[p[contains(text(), '3. Am I calm')]]//label[span[text()='Yes']]`));

    const confirmButton = PageElement.located(By.xpath(`//button[contains(text(), 'Log Trade')]`));

    await actorCalled('Alice').attemptsTo(
        Click.on(q1No),
        Click.on(q2Yes),
        Click.on(q3Yes),
        Wait.for(Duration.ofMilliseconds(500)), // Small wait for state update/button enablement
        Click.on(confirmButton)
    );
});

Then('the trade should appear in the journal list with symbol {string} and PnL {string}', async (symbol: string, pnl: string) => {
    // We look for an entry that contains both symbol and PnL
    // The list container is implicit, we can look for the specific entry structure

    // Simplest verification: Ensure text exists on page in the list area.
    // Or we can find a specific entry container.
    // List container: div with class space-y-4 inside lg:col-span-2
    // But specific entries have IDs starting with journal-entry-

    // Let's verify that an element containing both exists.
    // XPath: //div[starts-with(@id, 'journal-entry-')][.//span[text()='SYMBOL']][.//div[contains(text(), 'PNL')]]

    // Note: PnL formatting might be "+150.00". The step says "150".
    // Journal.tsx: {entry.pnl && entry.pnl > 0 ? '+' : ''}{entry.pnl?.toFixed(2)}
    // If PnL is 150, text will be "+150.00".
    // So we should expect "+150.00" or check loose containment.

    const formattedPnl = parseFloat(pnl) > 0 ? `+${parseFloat(pnl).toFixed(2)}` : parseFloat(pnl).toFixed(2);

    // Search for the symbol
    const tradeEntry = PageElement.located(By.xpath(`//div[starts-with(@id, 'journal-entry-') and .//span[contains(text(), '${symbol}')]]`));

    await actorCalled('Alice').attemptsTo(
        Wait.upTo(Duration.ofSeconds(15)).until(tradeEntry, isVisible()),
        Ensure.that(Text.of(tradeEntry), includes(symbol)),
        Ensure.that(Text.of(tradeEntry), includes(formattedPnl))
    );
});
