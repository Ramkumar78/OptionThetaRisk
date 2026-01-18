Feature: Fortress Strategy
  As a conservative investor
  I want to screen for Dynamic Volatility Fortress setups
  So that I can sell options with high safety margin

  Scenario: Fortress setup identification
    Given I have a list of tickers "SPY"
    When I run the Fortress screener
    Then I should receive a list of results
    And each result should contain a "safety_mult" field
    And each result should contain a "sell_strike" field
