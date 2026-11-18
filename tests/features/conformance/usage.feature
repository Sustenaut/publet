@conformance @must-5.2
Feature: A definition is settled by usage, not by verdict
  Section 5.2 permits no verdict on a definitional publet and settles it by
  usage evidence instead. A citation names where a term is used; it need
  not carry the text, which is what keeps a corpus of definitions from
  becoming a corpus of restatements.

  Scenario: A verdict on a definition is refused
    Given a workspace with a composed definition
    When I record a verdict on it
    Then it fails
    And stderr mentions "not truth-apt"

  Scenario: Usage citations are recorded and shown
    Given a workspace with a composed definition
    When I cite two sources using it
    And I ask why about the definition
    Then it succeeds
    And it prints "en.wiktionary.org/wiki/Merkle_tree"
    And it prints "doc.rust-lang.org/reference"

  Scenario: Two citations of one source are one source
    Given a workspace with a composed definition
    When I cite the same source twice
    And I ask why about the definition
    Then it succeeds
    And it prints "1 distinct source"

  Scenario: A definition with nothing citing it says so
    Given a workspace with a composed definition
    When I ask why about the definition
    Then it succeeds
    And it prints "no corpus citations"

  Scenario: A citation need not reproduce the text
    Given a workspace with a composed definition
    When I cite two sources using it
    And I ask why about the definition
    Then it succeeds
    And no citation carries the defined text
