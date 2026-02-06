Feature: Dashboard
  As a user
  I want to see the dashboard
  So that I can monitor my portfolio

  Scenario: User views the Dashboard
    Given the user is on the TradeGuardian home page
    When they navigate to the Dashboard page
    Then they should see the brand "TRADEGUARDIAN"
    And they should see the "Command Center" display
