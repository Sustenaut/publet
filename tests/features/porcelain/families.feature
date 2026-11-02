@porcelain
Feature: Families are bundled for a theme, one bundle per family and per code
  `pub bundle` writes one bundle per family and a name bundle for each code it
  defines, pointing at the family and the code, so a page for a class needs
  nothing but its bundle. A generation record is signed as it is written.

  Background:
    Given a workspace

  Scenario: A code's name bundle points at its family and the code
    When I compose a release
    And I write the family bundles
    Then it succeeds
    And the name "63" has a bundle pointing at the family under "6" and the code "63"
    And the name "62-1/-9" has a bundle pointing at the family under "6" and the code "62-1/-9"
    And the family under "6" has no name of its own

  Scenario: A family's bundle lists its classes and the families around them
    When I compose a release
    And I write the family bundles
    Then the bundle of the family under "6" names its parent "6" and its grouping 2
    And the bundle of the family under "6" lists "63" as a member and "62-1/-9" as an auxiliary heading a family
    And the bundle of the family under "6" says the family under "----" is broader

  Scenario: An edition's bundle says what it lists, and each family says it is listed
    When I compose a release
    And I write the family bundles
    Then the edition's bundle is sorted "edition"
    And the family under "6" says it is listed in the edition

  Scenario: A rival for a code is shown on both sides
    When I compose a release
    And I compose a concept at "63"
    And I write the family bundles
    Then the name "63" lists the family and the concept
    And the bundle of the family under "6" shows the concept competing for "63"
    And the concept's bundle shows the family competing for its code

  Scenario: Something classified under a class is shown on the class
    When I compose the family under "6"
    And I classify a claim under the family with aspect "63"
    And I write the family bundles
    Then the bundle of the family under "6" lists the claim as a member of "63"
    And the claim's bundle says it is classified under the code "63"

  Scenario: An anchor over a family covers the families below it
    Given a directory holding a release and an anchor over the family under "----"
    When I write the family bundles from the directory
    Then the bundle of the family under "6" names the anchor
    And the bundle of the family under "-" names no anchor

  @must-14.1.1
  Scenario: Publishing signs the generation record, which stays out of the membership
    Given a corpus with a key and one publet
    When I publish it
    Then the corpus's generation record is signed by its key with purpose "authored"
    And the signature is not a member of the generation
    When I publish it again with nothing changed
    Then the generation stays as it was

  @must-14.1.1
  Scenario: Advancing a generation signs the next record too
    Given a corpus with a key and one publet
    When I publish it
    And I revise the publet and publish it
    Then the corpus's generation record is signed by its key with purpose "authored"
    And the signature is not a member of the generation

  @must-14.1.1
  Scenario: pub domain signs the genesis record where a key is held
    Given a directory of objects and a workspace with a key
    When I make a domain of the directory
    Then it succeeds
    And its generation record is signed by the key with purpose "authored"

  Scenario: pub domain says so where no key is held
    Given a directory of objects and a workspace with no key
    When I make a domain of the directory
    Then it succeeds
    And stdout mentions "unsigned: this workspace has no key"
