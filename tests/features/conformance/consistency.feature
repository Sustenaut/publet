@conformance @must-14.1.1 @must-14.3.1
Feature: A delta cannot add, omit, or substitute anything
  Deltas are self-verifying: the client recomputes the membership root and
  compares it, so the peer that served the delta need not be trusted.

  Scenario: An honest delta applies and matches the declared root
    Given a domain at generation 0 with one member
    And a generation adding one member
    When the delta is applied
    Then it succeeds

  Scenario: A delta smuggling an extra member is refused
    Given a domain at generation 0 with one member
    And a generation whose added list contains a member the snapshot excludes
    When the delta is applied
    Then it fails
    And stderr mentions "membership root"

  Scenario: A client far behind syncs in logarithmic fetches
    Given a client 300 generations behind the head
    When I count the fetches it needs to sync
    Then the result is "4"
