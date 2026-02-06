Feature: Manual Trade Entry

  Scenario: User adds a new trade in the Journal
    Given the user is on the Journal page
    When they enter the following trade details:
      | Symbol   | AAPL     |
      | Strategy | Long     |
      | PnL      | 150      |
      | Notes    | E2E Test |
    And they click "Add Entry"
    Then the "Mindset Check" modal should open
    When they confirm the mindset checklist
    Then the trade should appear in the journal list with symbol "AAPL" and PnL "150"
