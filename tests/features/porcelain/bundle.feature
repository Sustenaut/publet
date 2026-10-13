@porcelain
Feature: A set of objects is written out as reading bundles for a theme
  `pub bundle` writes one JSON bundle per object and per name a definition
  goes by, beside each object's canonical bytes. A theme turns bundles into
  pages; the bundles hold everything a page shows, so a theme resolves
  nothing itself.

  Background:
    Given a workspace with the quantity definitions of publication 0

  Scenario: Every object has a bundle beside its canonical bytes
    When I compose a budget claim with energy per tray as three-point estimates
    And I write the bundles
    Then it succeeds
    And the claim's bundle holds its content and scope
    And the claim's bytes are served at its identifier, unchanged
    And the index lists the claim with its bundle's path

  Scenario: A bundle says what its object rests on, and why
    When I compose a budget claim with energy per tray as three-point estimates
    And I write the bundles
    Then the claim's bundle says it rests on the tray dimension as its unit, the kind and the measure
    And the claim's bundle gives the measure's parameters as low, likely and high
    And the claim's bundle summarizes every object it rests on

  Scenario: A bundle says what cites its object
    When I compose a budget claim with energy per tray as three-point estimates
    And I write the bundles
    Then the tray dimension's bundle says the claim uses it as a unit

  Scenario: A value not yet gathered stays null
    When I compose a budget claim with energy per tray not yet known
    And I write the bundles
    Then the claim's bundle holds a null cell

  Scenario: A definition has a bundle under the name it goes by
    When I write the bundles
    Then the name "{tray}" has a bundle naming the tray dimension
    And the name "{tray}" has the address "https://pub.example/def/%7Btray%7D"

  Scenario: A name two definitions share lists both
    When I define another dimension named "{tray}"
    And I write the bundles
    Then the name "{tray}" has a bundle naming both definitions

  Scenario: A directory of object files is bundled without a workspace
    When I export the workspace's objects to a directory
    And I write the bundles from that directory
    Then it succeeds
    And the name "{tray}" has a bundle naming the tray dimension

  Scenario: Bundles are never written over earlier ones
    Given the bundle directory already holds a file
    When I write the bundles
    Then it fails
    And stderr mentions "is not empty"
