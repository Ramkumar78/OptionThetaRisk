Feature: Mobile Dashboard
  As a retail trader on the go
  I want to see the dashboard correctly on my mobile device
  So that I can monitor my risks anywhere

  Scenario: Dashboard loads on mobile viewport
    Given I am using a mobile device
    When I visit the dashboard page
    Then I should see the dashboard content
    And I should see the Quick Trade button in the mobile menu
