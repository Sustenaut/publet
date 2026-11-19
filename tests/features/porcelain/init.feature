@porcelain
Feature: A workspace is local-first from the start

  Scenario: init creates a workspace with a policy
    Given an empty directory
    And the program under test is "pub"
    When I run "pub init"
    Then a workspace exists
    And it prints "policy"
    And it prints "trusts only this workspace"

  Scenario: commands refuse to guess where the workspace is
    Given an empty directory
    And the program under test is "pub"
    When I run "pub read" on any identifier
    Then it says to run "pub init"

  Scenario: pub with no command lists the commands and exits as a usage error
    Given an empty directory
    And the program under test is "pub"
    When I run "pub"
    Then it exits 2 and lists the commands, with pub --version
