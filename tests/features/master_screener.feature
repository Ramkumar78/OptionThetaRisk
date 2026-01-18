Feature: Master Convergence Screener
  As a trader
  I want to find stocks with strategy confluence
  So that I can find high probability setups

  Scenario: Confluence detection
    Given I have a list of tickers "AAPL,MSFT"
    When I run the Master Convergence screener
    Then I should receive a list of results
    And each result should contain a "confluence_score" field
    And the result should indicate "BULLISH" trend if price is above SMA200
