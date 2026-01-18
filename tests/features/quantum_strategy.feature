Feature: Quantum Physics Screener
  As a quantitative trader
  I want to screen stocks using physics-based metrics (Hurst, Entropy, Kalman)
  So that I can identify regime changes and trends

  Scenario: Strong trend detection
    Given I have a list of tickers "NVDA"
    When I run the Quantum screener
    Then I should receive a list of results
    And each result should contain a "hurst" field
    And each result should contain a "entropy" field
