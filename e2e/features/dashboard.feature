Feature: Dashboard
  As a user
  I want to see the dashboard
  So that I can monitor my portfolio

  Scenario: User views the Dashboard
    Given the user is on the TradeGuardian home page
    Then they should see the brand "TRADEGUARDIAN"
    And they should see the "Net Liq" display
