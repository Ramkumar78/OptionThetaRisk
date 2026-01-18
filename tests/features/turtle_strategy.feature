Feature: Turtle Trading Strategy
  As a trader
  I want to screen for Turtle Trading setups
  So that I can identify breakout opportunities

  Scenario: Basic Turtle setup screening
    Given I have a list of tickers "GOOGL,AMZN"
    When I run the Turtle screener for timeframe "1d"
    Then I should receive a list of results
    And each result should contain a "signal" field
    And each result should contain a "stop_loss" field
