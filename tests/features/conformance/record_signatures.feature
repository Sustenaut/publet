@conformance @must-14.1.1
Feature: A generation record is trusted only when its publisher signed it
  A record names its author, which proves nothing. A reader checks each
  record's detached signature by that key before it trusts the membership the
  records state. Records from before a domain signed stay readable, with a
  warning; once a domain has signed, a missing signature is refused.

  Background:
    Given a domain at generation 0 with one member, and its publisher's key

  Scenario: Records signed by the publisher apply
    Given two records, both signed by the publisher
    When I apply the records
    Then it succeeds
    And stderr does not mention "warning"

  Scenario: Records from before the domain signed apply, with a warning
    Given two records, neither signed
    When I apply the records
    Then it succeeds
    And stderr mentions "warning: generation 1"

  Scenario: A record unsigned after a signed one is refused
    Given two records, the first signed by the publisher and the second unsigned
    When I apply the records
    Then it fails
    And stderr mentions "is unsigned, after an earlier generation of this domain was signed"

  Scenario: A record signed by another key is refused
    Given two records, the second signed by another key
    When I apply the records
    Then it fails
    And stderr mentions "carries a signature that does not verify by its author"

  Scenario: A record whose signature was altered is refused
    Given two records, the second with its signature altered
    When I apply the records
    Then it fails
    And stderr mentions "carries a signature that does not verify by its author"

  Scenario: A record whose bytes were altered after signing loses its signature
    Given two records, both signed, and the second altered after signing
    When I apply the records
    Then it fails

  Scenario: A record signed by a key that does not continue the publisher's is refused
    Given two records, the second written and signed by another key
    When I apply the records
    Then it fails
    And stderr mentions "does not continue"
