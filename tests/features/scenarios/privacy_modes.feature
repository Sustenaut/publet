@scenario @must-14.3.2
Feature: The mode in use is visible, not assumed
  The privacy properties of reading a replica are real, and a reader who
  does not know which mode they are in cannot know whether they have them.

  Scenario: Local reads are labelled and are the default
    Given a workspace containing the cohort claim
    When I read the claim
    Then the mode is reported as "local"

  Scenario: Evaluation happens locally and says so
    Given a workspace containing the cohort claim
    When I ask why
    Then it prints "locally"
    And it prints "policy pub:sha2-256:"

  Scenario: Syncing says what it disclosed
    Given a workspace containing the cohort claim
    When I read the claim
    Then it prints "[local]"
    And it does not print "[query]"
    And stderr does not mention "[query]"
