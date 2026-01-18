Feature: Bull Put Spread Strategy
  As a trader
  I want to screen for high probability Bull Put Spreads
  So that I can generate income with defined risk

  Scenario: Basic Bull Put Spread screening
    Given I have a list of tickers "SPY,IWM"
    When I run the Bull Put screener
    Then I should receive a list of results
    And each result should contain a "credit" field
    And each result should contain a "pop" field
