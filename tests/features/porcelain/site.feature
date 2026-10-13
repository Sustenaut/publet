@porcelain
Feature: A set of objects is shown as a static website
  `pub site` writes a page per object and a page per name a definition goes
  by, beside each object's canonical bytes. The site is a rendering of the
  objects, regenerated from them and never stored.

  Background:
    Given a workspace with the quantity definitions of publication 0

  Scenario: Every object has a page beside its canonical bytes
    When I compose a budget claim with energy per tray as three-point estimates
    And I write the site
    Then it succeeds
    And the claim has a page showing its content and scope
    And the claim's bytes are served at its identifier, unchanged
    And the index links the claim's page

  Scenario: A quantity cell reads in its measure's order
    When I compose a budget claim with energy per tray as three-point estimates
    And I write the site
    Then the claim's page shows low, likely and high in that order
    And the claim's page links the column's kind and measure

  Scenario: A value not yet gathered reads as not yet known
    When I compose a budget claim with energy per tray not yet known
    And I write the site
    Then the claim's page says "not yet known"

  Scenario: A definition is served under the name it goes by
    When I write the site
    Then the name "{tray}" has a page linking the tray dimension's page
    And the index lists the name "{tray}" at "def/%7Btray%7D/"

  Scenario: A name two definitions share lists both
    When I define another dimension named "{tray}"
    And I write the site
    Then the name "{tray}" has a page listing both definitions

  Scenario: Text from an object is shown as text, never as markup
    When I compose a claim whose content holds markup
    And I write the site
    Then the claim's page shows the markup escaped

  Scenario: A directory of object files is shown without a workspace
    When I export the workspace's objects to a directory
    And I write the site from that directory
    Then it succeeds
    And the name "{tray}" has a page linking the tray dimension's page

  Scenario: The site is never written over an earlier one
    Given the site directory already holds a file
    When I write the site
    Then it fails
    And stderr mentions "is not empty"
