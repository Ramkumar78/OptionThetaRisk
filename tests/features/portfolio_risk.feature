Feature: Portfolio Risk Analysis
  As an investor
  I want to analyze my portfolio risk
  So that I can identify concentration and correlation issues

  Scenario: High concentration detection
    Given I have a portfolio with "NVDA:80000,GOOGL:20000"
    When I analyze the portfolio risk
    Then I should receive a risk report
    And the report should contain concentration warnings
    And the concentration warning should mention "NVDA"

  Scenario: Sector diversification check
    Given I have a portfolio with "AAPL:50000,MSFT:50000"
    When I analyze the portfolio risk
    Then the report should contain sector breakdown
    And "Technology" sector should be dominant if known
