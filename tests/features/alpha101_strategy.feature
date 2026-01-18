Feature: Alpha 101 Strategy
  As a trader
  I want to screen for Alpha 101 momentum setups
  So that I can find high momentum stocks

  Scenario: Alpha 101 setup screening
    Given I have a list of tickers "NVDA,TSLA"
    When I run the Alpha 101 screener for timeframe "1d"
    Then I should receive a list of results
    And each result should contain a "alpha_101" field
