@conformance @must-4.4
Feature: Only what its author signed counts towards a standing
  An object's `author` names a key and proves nothing. Before evidence counts
  towards a standing, its signature by that key is checked against the key's
  own object. What fails stays readable, and is named as not counted.

  Background:
    Given a workspace whose trusted key affirms an empirical claim

  Scenario: An affirmation its author signed counts
    When the affirmation is signed by its author
    And I ask why the claim stands as it does
    Then the affirmation weighs on the claim
    And no evidence is reported as not counted

  Scenario Outline: An affirmation not signed by its author does not count
    When the affirmation is <how>
    And I ask why the claim stands as it does
    Then the affirmation does not weigh on the claim
    And the affirmation is reported as not counted

    Examples:
      | how                               |
      | left unsigned                     |
      | signed by another key             |
      | signed with an altered signature  |
