@conformance
Feature: A family defines the classes under one class, and an edition pins a release
  A family is a definitional claim with `defines.sort` "family": a parent
  code, a grouping, and its classes, each a concept without `sort`. Families
  name each other by code. An edition is a definitional claim listing every
  family by its exact CID, with the auxiliary groups and groupings they use
  and counts a reader can check. A class is named by its code where a field
  takes a code, and by its family's CID and `aspect` where a field takes a CID.

  Background:
    Given a workspace

  @must-5.9.1
  Scenario: A family is one claim defining its classes
    When I compose the family under "6"
    Then it succeeds
    And reading it shows "class     definitional"

  @must-5.9.1
  Scenario Outline: A family of the wrong shape is refused
    When I compose a family defining
      """
      <defines>
      """
    Then it fails
    And stderr mentions "<reason>"

    Examples:
      | defines | reason |
      | {"sort": "family", "parent": "63", "members": [{"pdc": "631", "name": "x"}]} | defines.grouping |
      | {"sort": "family", "parent": "63", "grouping": "1", "members": [{"pdc": "631", "name": "x"}]} | defines.grouping |
      | {"sort": "family", "parent": "", "grouping": 1, "members": [{"pdc": "631", "name": "x"}]} | defines.parent |
      | {"sort": "family", "parent": "63", "grouping": 1} | defines.members |
      | {"sort": "family", "parent": "63", "grouping": 1, "members": []} | at least one class |
      | {"sort": "family", "parent": "63", "grouping": 1, "members": [{"name": "x"}]} | defines.pdc |
      | {"sort": "family", "parent": "63", "grouping": 1, "members": [{"pdc": "631"}]} | defines.name |
      | {"sort": "family", "parent": "63", "grouping": 1, "members": [{"pdc": "631", "name": "x"}, {"pdc": "631", "name": "y"}]} | each code once |
      | {"sort": "family", "parent": "63", "grouping": 1, "members": [{"pdc": "631", "name": "x"}], "auxiliaries": [{"pdc": "631", "name": "y"}]} | each code once |
      | {"sort": "family", "parent": "631", "grouping": 1, "members": [{"pdc": "631", "name": "x"}]} | defines.parent |
      | {"sort": "family", "parent": "631", "grouping": 1, "members": [{"pdc": "632", "name": "x"}], "auxiliaries": [{"pdc": "631", "name": "y"}]} | defines.parent |
      | {"sort": "family", "parent": "63", "grouping": 1, "members": [{"sort": "concept", "pdc": "631", "name": "x"}]} | without `sort` |
      | {"sort": "family", "parent": "63", "grouping": 1, "members": [{"pdc": "631", "name": "x", "children": false}]} | defines.members.children |
      | {"sort": "family", "parent": "63", "grouping": 1, "members": [{"pdc": "631", "name": "x"}], "auxiliaries": []} | defines.auxiliaries |

  @must-5.9.1
  Scenario: A family may only be defined by a definitional claim
    When I compose a normative claim carrying a family
    Then it fails
    And stderr mentions "`defines` belongs on a `definitional` claim only"

  @must-5.9.1
  Scenario: A member is a concept in any form, and presupposes what that form cites
    Given a kind
    When I compose a family whose member narrows the kind
    Then it succeeds
    And the family presupposes the kind

  @must-5.9.1
  Scenario: A quantity member has a boundary, as a quantity concept does
    Given a kind
    When I compose a family whose member narrows the kind with no boundary
    Then it fails
    And stderr mentions "defines.boundary"

  @must-5.9.1
  Scenario: A relation member may bind another member of its family
    Given a kind
    When I compose a family of two quantities and a relation between them
    Then it succeeds

  @must-5.9.1
  Scenario: A relation member binding a code nothing defines is refused
    Given a kind
    When I compose a family whose relation binds the code "99"
    Then it fails
    And stderr mentions "PDC code 99 is named"

  @must-5.9.1
  Scenario: A field taking a code finds its concept in a family in depends
    When I compose the family under "6"
    And I compose a singular of class "63" depending on the family
    Then it succeeds

  @must-5.9.1
  Scenario: A field taking a code still needs the claim defining it
    When I compose a singular of class "63" depending on nothing
    Then it fails
    And stderr mentions "PDC code 63 is named"

  @must-5.9.1
  Scenario: A single concept claim stays valid beside a family at its code
    When I compose the family under "6"
    And I compose a concept at "63"
    Then it succeeds

  @must-9.2
  Scenario: Two families are compared per code
    Given a store where two rival families share one code
    When I compare the claims resting on each
    Then it succeeds
    And the divergence names the code "63" and no other

  @must-9.2
  Scenario: A concept and a family's member at one code diverge
    Given a store where a concept and a family share one code
    When I compare the claims resting on each
    Then it succeeds
    And the divergence names the code "63" and no other

  @must-9.2
  Scenario: Two versions of a family are stale on their shared codes
    Given a store where a family is revised and a claim rests on each version
    When I compare the claims resting on each
    Then it succeeds
    And the code "63" is stale rather than divergent

  @must-9.2
  Scenario: An edition has no term to diverge on
    Given the family vector "accept-edition"
    When I list the vector's terms
    Then the terms name each class and nothing for the edition

  @must-5.9.1
  Scenario: Something is placed under a class by the family's CID and the code
    When I compose the family under "6"
    And I classify a claim under the family with aspect "63"
    Then it succeeds

  @must-5.9.1
  Scenario Outline: A classifies under a family must name one of its codes
    When I compose the family under "6"
    And I classify a claim under the family with aspect "<aspect>"
    Then it fails
    And stderr mentions "must name one of its codes"

    Examples:
      | aspect |
      | 64     |
      | 6      |

  @must-5.9.1
  Scenario: A classifies under a family with no aspect is refused
    When I compose the family under "6"
    And I classify a claim under the family with no aspect
    Then it fails
    And stderr mentions "must name one of its codes"

  @must-5.9.1
  Scenario Outline: A family is changed and not debated
    When I compose the family under "6"
    And I file a "<kind>" on the family <how>
    Then it fails
    And stderr mentions "a `<kind>` cannot target"

    Examples:
      | kind       | how               |
      | disputes   | with aspect "63"  |
      | disputes   | with no aspect    |
      | supports   | with aspect "63"  |
      | supports   | with no aspect    |
      | assessment | with aspect "63"  |
      | assessment | with no aspect    |

  @must-5.9.1
  Scenario Outline: An edition is changed and not debated
    When I compose a release
    And I file a "<kind>" on the edition
    Then it fails
    And stderr mentions "a `<kind>` cannot target"

    Examples:
      | kind       |
      | disputes   |
      | supports   |
      | assessment |

  @must-2
  Scenario Outline: A concept is changed and not debated
    When I compose a concept at "63"
    And I file a "<kind>" on the concept
    Then it fails
    And stderr mentions "a `<kind>` cannot target"

    Examples:
      | kind       |
      | disputes   |
      | supports   |
      | assessment |

  @must-5.2
  Scenario: Authoring refuses what a load would report and leave out
    When I compose the family under "6"
    And I file a "disputes" on the family with no aspect
    Then it fails
    And stderr mentions "so it was not stored"

  @must-5.2
  Scenario: A dispute on a family does not stop the rest loading
    Given the family vector "drop-family-disputes"
    When I load the vector
    Then the vector's outcome is what its table says
    And stderr mentions "warning: dropped"

  @must-5.2
  Scenario: What a load leaves out is still a member of the domain it is in
    Given a workspace holding a family vector "drop-family-disputes" as a directory
    When I make a domain of the directory
    Then it succeeds
    And every object in the directory is a member of its generation

  @must-5.9.1
  Scenario: A proposal is argued on its supersedes relation, by two keys
    Given a steward's family
    When a second key proposes a new family superseding it
    Then the proposal is in the family's full lineage and not its authoritative one
    When the second key files an argument supporting the proposal's relation
    Then it succeeds
    When a third claim disputes the proposal's relation
    Then it succeeds
    When the second key files a "supports" on the current family
    Then it fails
    And stderr mentions "a `supports` cannot target"
    When the second key files a "disputes" on the current family
    Then it fails
    And stderr mentions "a `disputes` cannot target"
    When the second key files a "supports" on the proposed family
    Then it fails
    And stderr mentions "a `supports` cannot target"
    When the second key files a "disputes" on the proposed family
    Then it fails
    And stderr mentions "a `disputes` cannot target"
    Then everything held loads with nothing left out
    When the steward publishes the proposal
    Then the proposal is in the family's authoritative lineage

  @must-5.2
  Scenario: A verdict remains barred from an edition
    When I compose a release
    And I file a "verdict" on the edition
    Then it fails
    And stderr mentions "definitional"

  @must-5.9.1
  Scenario Outline: What a family still admits passes
    When I compose the family under "6"
    And I file a "<kind>" on the family with no aspect
    Then it succeeds

    Examples:
      | kind        |
      | tagged      |
      | timestamped |
      | retracts    |

  @must-5.9.1
  Scenario: A claim may rest on a family and be disputed itself
    When I compose the family under "6"
    And I dispute a claim resting on the family
    Then it succeeds

  @must-5.9.1
  Scenario: The steward's next version of a family is authoritative
    Given the family vector "accept-family-revised-by-its-steward"
    Then the next version is in the family's authoritative lineage

  @must-5.9.1
  Scenario: A lineage delegate's next version of a family is authoritative
    Given the family vector "accept-family-revised-by-a-delegate"
    Then the next version is in the family's authoritative lineage

  @must-5.9.1
  Scenario: Another key's next version of a family is only a proposal
    Given the family vector "accept-family-change-proposed-by-another-key"
    Then the next version is in the family's full lineage and not its authoritative one

  @must-5.9.1
  Scenario: Usage of one class targets the family with the code as aspect
    When I compose the family under "6"
    And I file usage on the family with aspect "63"
    Then it succeeds

  @must-5.2
  Scenario: A verdict remains barred from a family, as from every definition
    When I compose the family under "6"
    And I file a verdict on the family with aspect "63"
    Then it fails
    And stderr mentions "definitional"

  @must-5.9.1
  Scenario: An edition pins its families
    When I compose a release
    Then it succeeds
    And reading it shows "class     definitional"

  @must-5.9.1
  Scenario: A family not held leaves an edition unchecked, and says so
    When I compose an edition of families this workspace does not hold
    Then it succeeds
    And stderr mentions "is not held, so what cites it is unchecked"

  @must-5.9.1
  Scenario Outline: An edition that disagrees with its families is refused
    When I compose a release with <change>
    Then it fails
    And stderr mentions "<reason>"

    Examples:
      | change                          | reason                                          |
      | classes miscounted in a section | its counts give `main`                          |
      | auxiliaries miscounted in total | its counts give `total`                         |
      | a child not flagged             | 6 heads a family and has no `children` flag     |
      | a flag with no family under it  | 63 has a `children` flag and no family under it |
      | an undefined grouping           | names the grouping 7                            |
      | a parent not its key            | the family listed under 6 states the parent     |
      | a top family with a parent      | the top family states the parent                |
      | a code in two families          | define (1/9) twice                              |
      | a parent nothing defines        | which no listed family defines                  |
      | a concept listed as a family    | is listed as a family and does not define one   |

  @must-5.9.1
  Scenario Outline: An edition of the wrong shape is refused
    When I compose a release with its edition changed by <change>
    Then it fails
    And stderr mentions "<reason>"

    Examples:
      | change                       | reason             |
      | no top family                | defines.top        |
      | no main section              | defines.sections   |
      | one family listed twice      | each family once   |
      | one parent in two sections   | each parent code once |
      | a group number used twice    | each number once   |
      | a group with no heads        | at least one head  |
      | a head named twice           | naming each thing once |
      | a grouping of no such group  | group numbers the edition defines |
      | no counts                    | defines.counts     |
      | groups miscounted            | defines.counts     |
      | groupings miscounted         | defines.counts     |
      | a section's families miscounted | defines.counts  |
      | total families miscounted    | defines.counts     |

  @must-5.9.1
  Scenario: An edition may grow against the one it supersedes
    Given a composed release
    When I revise the edition so that a group and a grouping gain members and new numbers appear
    Then it succeeds

  @must-5.9.1
  Scenario Outline: An edition that shrinks against the one it supersedes is refused
    Given a composed release
    When I revise the edition so that <change>
    Then it fails
    And stderr mentions "<reason>"

    Examples:
      | change                         | reason                                         |
      | a group loses a head           | group 1 lost                                   |
      | a grouping loses a group       | grouping 2 lost 1                              |
      | a group number is dropped      | group 2 of the edition it supersedes is gone   |
      | a grouping number is dropped   | grouping 3 of the edition it supersedes is gone |
      | a group number means another   | group 2 is reused with a different meaning     |
      | a grouping number means another | grouping 1 is reused with a different meaning |

  @must-5.9.1
  Scenario: Another key's supersedes relation does not bind an edition
    Given a store where another key files a supersedes from an edition to one it shrinks against
    Then loading the store succeeds

  @must-5.9.1
  Scenario Outline: Each family vector is decided as its table says
    Given the family vector "<case>"
    When I load the vector
    Then the vector's outcome is what its table says

    Examples:
      | case |
      | accept-edition |
      | drop-concept-disputes |
      | drop-concept-supports |
      | drop-concept-assessment |
      | drop-concept-verdict |
      | drop-concept-critique |
      | drop-classifies-under-no-class |
      | accept-proposal-argued-on-its-relation |
      | accept-edition-that-grew |
      | reject-family-code-twice |
      | reject-family-code-in-both-lists |
      | reject-family-parent-is-a-member |
      | reject-family-no-classes |
      | reject-family-no-grouping |
      | reject-family-member-with-sort |
      | reject-family-children-false |
      | reject-family-kind-not-in-depends |
      | reject-edition-no-section |
      | reject-edition-grouping-of-undefined-group |
      | reject-edition-number-twice |
      | reject-edition-empty-group |
      | reject-edition-count-of-groups |
      | reject-edition-count-of-listed-families |
      | drop-edition-count-of-classes |
      | drop-edition-count-of-auxiliaries-in-total |
      | drop-edition-child-not-flagged |
      | drop-edition-flag-with-no-family |
      | drop-edition-undefined-grouping |
      | drop-edition-parent-disagrees |
      | drop-edition-top-with-parent |
      | drop-edition-code-in-two-families |
      | drop-edition-group-lost-a-head |
      | drop-edition-number-reused |
      | drop-edition-grouping-lost-a-group |
      | drop-edition-number-dropped |
      | drop-family-disputes |
      | drop-family-disputes-on-a-code |
      | drop-edition-disputes |
      | drop-family-supports |
      | drop-family-supports-on-a-code |
      | drop-edition-supports |
      | drop-family-assessment |
      | drop-family-assessment-on-a-code |
      | drop-edition-assessment |
      | drop-family-verdict |
      | drop-family-verdict-on-a-code |
      | drop-edition-verdict |
      | drop-family-critique |
      | drop-family-critique-on-a-code |
      | drop-edition-critique |
      | accept-family-allowed-uses |
      | accept-family-revised-by-its-steward |
      | accept-family-revised-by-a-delegate |
      | accept-family-change-proposed-by-another-key |

  Scenario: The family vectors are what their generator makes
    Then every family vector is what the generator makes
