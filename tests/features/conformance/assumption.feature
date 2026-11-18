@conformance @must-10.7 @must-7.4
Feature: Vouching and triage bear on the graph without authority in it
  An assumer stakes standing on another key's output while disclosing
  nothing about who holds it. A triage annotation orders attention and
  decides nothing.

  Scenario: An assumption is not authorship
    Given a key assuming accountability for another
    When I list the claims authored by the assumed key
    Then it succeeds
    And it lists only the assumed key's own publet

  Scenario: An assumer takes no byline
    Given a key assuming accountability for another
    When I list the claims authored by the assumer
    Then it succeeds
    And stdout is empty

  Scenario: Assumptions are counted, because fronting is visible only in aggregate
    Given a key assuming accountability for three others
    When I list the assumptions the assumer holds
    Then it succeeds
    And it lists 3 assumptions, each of a different key

  Scenario: No linkage between assumer and assumed holder is recorded
    Given a key assuming accountability for another
    When I list the assumptions the assumer holds
    Then it succeeds
    And it lists 1 assumption, each of a different key
    And each assumption it lists records only the two keys and the grounds

  Scenario: A triage annotation changes no standing
    Given a claim with a standing
    And a triage annotation calling it redundant
    When I ask why again
    Then it succeeds
    And the standing is unchanged

  Scenario: A triage annotation without its disclosure block is not read
    Given a triage annotation with no engine declared
    When I list the triage findings on the claim
    Then it succeeds
    And stdout is empty
