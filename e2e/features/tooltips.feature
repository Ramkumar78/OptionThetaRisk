Feature: Dashboard Tooltips

  Background:
    Given the user is on the TradeGuardian home page
    When they navigate to the Dashboard page

  Scenario: User sees tooltips on hover
    Then they should see the Mindset Meter tooltip when hovering
    And they should see the Regime tooltip when hovering
