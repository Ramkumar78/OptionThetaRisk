Feature: Sanity Check
  As a user
  I want to ensure the main user flow works
  So that I can trust the application

  Scenario: User loads home page, navigates to Backtester, enters symbol SPY, and sees a Result
    Given the user is on the TradeGuardian home page
    When they navigate to the Backtester page
    And they enter symbol "SPY"
    And they complete the mindset check
    Then they should see the Result graph
