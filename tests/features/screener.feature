Feature: Screener 5/13 Strategy
  As a trader
  I want to screen for 5/13 EMA setups
  So that I can find potential trading opportunities

  Scenario: Basic 5/13 setup screening
    Given I have a list of tickers "AAPL,MSFT"
    When I run the 5/13 screener for timeframe "1d"
    Then I should receive a list of results
    And each result should contain a "signal" field
