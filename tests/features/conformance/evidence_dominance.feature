@conformance @must-11.4
Feature: Proof and replication dominate endorsement weight
  Proof settles a formal claim and independent reproduction settles an
  empirical one. Endorsement decides only what neither has settled.

  Scenario: Overwhelming endorsement cannot accept an unreplicated claim
    Given the "02-unreplicated" vector
    When I evaluate it
    Then it succeeds
    And the JSON it prints has "result" equal to "unreplicated"

  Scenario: One independent inconsistent reproduction outweighs endorsement
    Given the "03-refuted" vector
    When I evaluate it
    Then it succeeds
    And the JSON it prints has "result" equal to "rejected"

  Scenario: Meeting the replication floor permits acceptance
    Given the "01-chain" vector
    When I evaluate it
    Then it succeeds
    And the JSON it prints has "result" equal to "accepted"

  Scenario: A proof is not a poll
    Given the "05-proof" vector
    When I evaluate it
    Then it succeeds
    And the JSON it prints has "result" equal to "accepted"

  Scenario: Retraction removes positive standing whatever the evidence
    Given the "10-retracted" vector
    When I evaluate it
    Then it succeeds
    And the JSON it prints has "result" equal to "rejected"
