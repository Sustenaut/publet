@conformance @must-14.1.1
Feature: A replica takes in a domain only when its publisher signed the records
  A client synchronizing by delta checks each record's signature before it
  stores anything. The signatures, and the keys that made them, travel with
  the records.

  Scenario: Records signed by the publisher are taken in
    Given a node serving a domain of five objects whose records are signed
    When a client synchronizes from generation 0
    Then it succeeds
    And stderr does not say "warning"
    And the replica holds 16 objects

  Scenario: Records signed by another key from the third on are refused
    Given a node serving a domain of five objects whose records are forged from the third
    When a client synchronizes from generation 0
    Then it is refused, and nothing is stored
    And stderr says "generation 3"
