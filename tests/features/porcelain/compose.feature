@porcelain @must-5.1
Feature: Composing requires stating what you are asserting under

  Background:
    Given a workspace

  Scenario: A publet cannot be composed without a scope
    When I compose a claim with no scope
    Then it fails
    And stderr mentions "--scope is required"

  Scenario: A publet cannot be composed without a class
    When I compose a claim with no class
    Then it fails
    And stderr mentions "--class is required"

  Scenario: An empirical claim is told what acceptance will require
    When I compose an empirical claim
    Then stderr mentions "endorsement alone"

  Scenario: Structural findings are warnings, not refusals
    When I compose a claim joining two assertions
    Then it succeeds
    And stderr mentions "two assertions"
