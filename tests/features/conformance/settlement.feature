@conformance @must-12.1 @must-12.2 @must-12.3 @must-12.5
Feature: Settlement holds money and no authority
  The ledger executes predicates over evaluations anyone can recompute.
  Every predicate is chosen in advance by the party putting up the money,
  and none of it reaches what anyone may read or what anyone believes.

  Background:
    Given this build carries settlement
    And the program under test is "pub-settle"

  Scenario: The layer is optional and says so when absent
    Given a bounty with a review share of 6000 basis points
    When I run "pub-settle --settle=bounty.cbor"
    Then it fails
    And stderr mentions "settlement is optional"

  Scenario: A bounty must name the viewpoint it settles against
    Given a bounty naming no policy
    When I run "pub-settle --bounty=bounty.cbor"
    Then it fails
    And stderr mentions "a bounty must name the policy it settles against"

  Scenario Outline: The review share has a floor
    Given a bounty with a review share of <share> basis points
    When I run "pub-settle --bounty=bounty.cbor"
    Then it <outcome>

    Examples:
      | share | outcome   |
      | 5999  | fails     |
      | 6000  | succeeds  |
      | 10000 | succeeds  |

  Scenario: The prohibitions are enumerated with their reasons
    When I run "pub-settle --prohibitions"
    Then it succeeds
    And each line it prints names what it forbids and why

  Scenario: The ledger interface cannot express a standing or a read
    When I read the methods of the ledger interface
    Then the result does not include "standing"
    And the result does not include "weight"
    And the result does not include "read"
    And the result does not include "fetch"
    And the result does not include "serve"
    And the result does not include "retriev"
    And the result does not include "access"
