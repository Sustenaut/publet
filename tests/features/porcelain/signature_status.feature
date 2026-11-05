@porcelain @must-4.4
Feature: Readers show whether an object's author signed it
  Only what its author signed counts towards a standing, so `pub read` and
  `pub bundle` say for each object whether a signature by its author verifies.

  Background:
    Given a workspace with a key and a claim it composed

  Scenario: An unsigned claim is shown as not counting yet
    When I read the claim
    Then it shows "signed    no: it counts towards no standing until its author signs it"
    And reading it as JSON gives the signature "missing"

  Scenario: A claim its author signed is shown as signed
    When the author signs the claim
    And I read the claim
    Then it shows "signed    yes, by its author"
    And reading it as JSON gives the signature "verified"

  Scenario: A signature by its author that does not verify is shown as such
    When a signature by the author over other bytes is filed for the claim
    And I read the claim
    Then it shows "signed    no: a signature by its author does not verify"
    And reading it as JSON gives the signature "invalid"

  Scenario: A signature is not itself signed
    When the author signs the claim
    And I read the claim's signature
    Then it shows "signed    not applicable"

  Scenario: An object file read alone is not checked
    When I read the claim from its own file
    Then it shows "signed    not checked"

  Scenario: Bundles say which objects their authors signed
    When the author signs the claim
    And I compose a second claim and leave it unsigned
    And I write the bundles
    Then the claim's bundle gives the signature "verified"
    And the second claim's bundle gives the signature "missing"
