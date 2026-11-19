@porcelain @must-11.3
Feature: A standing is never reduced to a badge
  A reader told only "accepted" cannot tell whether that rests on
  replication or on agreement, and those are not the same claim.

  Background:
    Given a workspace containing the cohort claim

  Scenario: Every component of the standing is exposed
    When I ask why
    Then the affirm, deny, abstain and active weights are shown
    And it prints "delta"
    And it prints "threshold"
    And the reproduction counts and the replication floor are shown

  Scenario: An unevaluated claim says so about the viewpoint, not the claim
    When I ask why
    Then it prints "result           undetermined"
    And it prints "fact about your viewpoint"

  Scenario: Overwhelming endorsement without replication is not acceptance
    Given fifty trusted keys affirming the claim
    When I ask why
    Then it prints "result           unreplicated"
    And it prints "substitutes for one replication"
