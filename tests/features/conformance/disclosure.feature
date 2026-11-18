@conformance @must-17
Feature: What a user is told before they publish anything
  Every object signed is replicated and designed not to be removable, so
  the consequences are stated in plain language at the point of first use
  rather than in documentation someone may never read.

  Scenario: Creating a workspace states the permanence
    Given an empty directory
    And the program under test is "pub"
    When I run "pub init"
    Then it prints "permanent and attributed"

  Scenario: Creating a workspace states that there is no erasure
    Given an empty directory
    And the program under test is "pub"
    When I run "pub init"
    Then it prints "cannot be reliably"

  Scenario: Creating a workspace advises separate keys per context
    Given an empty directory
    And the program under test is "pub"
    When I run "pub init"
    Then it prints "separate keys for separate contexts"

  Scenario: Reading states which mode was used
    Given a workspace containing the cohort claim
    When I read the claim
    Then the mode is reported as "local"
