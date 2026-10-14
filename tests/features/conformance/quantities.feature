@conformance
Feature: A number names its unit, its kind, how sure it is, and how it was computed
  Units, quantity kinds and statistical measures are definitional claims
  carrying `defines`; a column cites them, and they sit in its claim's
  dependency closure. A cell in a measured column is a quantity whose keys
  are the measure's parameters. A computed value names its calculation.

  Background:
    Given a workspace with the quantity definitions of publication 0

  @must-5.9.1
  Scenario: A definition states what it defines in checkable form
    Then reading the tray dimension shows "class     definitional"

  @must-5.9.1
  Scenario: Only a definitional claim may carry defines
    When I compose a normative claim defining
      """
      {"sort": "dimension", "symbol": "{tray}"}
      """
    Then it fails
    And stderr mentions "`defines` belongs on a `definitional` claim only"

  @must-5.9.1
  Scenario Outline: A definition of an unknown sort or shape is refused
    When I compose a definitional claim defining
      """
      <defines>
      """
    Then it fails
    And stderr mentions "<reason>"

    Examples:
      | defines                                                       | reason          |
      | {"sort": "currency", "symbol": "[EUR]"}                       | defines.sort    |
      | {"sort": "dimension", "symbol": "tray"}                       | defines.symbol  |
      | {"sort": "unit", "symbol": "{flat}", "value": "6e0", "unit": "{tray}"} | defines.value |
      | {"sort": "measure", "name": "range", "describes": "spread", "parameters": []} | defines.describes |
      | {"sort": "concept", "name": "LED shelf electricity", "boundary": {"includes": [], "excludes": []}} | defines.pdc |
      | {"sort": "concept", "pdc": "631.544", "name": "LED shelf electricity", "kind": 7, "boundary": {"includes": [], "excludes": []}} | defines.kind |

  @must-5.9.2 @must-5.9.3 @must-5.9.4
  Scenario: A measured column cites its unit, kind and measure, which become dependencies
    When I compose a budget claim with energy per tray as three-point estimates
    Then it succeeds
    And reading it shows "energy (kW.h/{tray})"
    And reading it shows "    measure  "
    And the claim presupposes the tray dimension, the kind and the measure

  @must-5.9.4
  Scenario: A quantity in a column with no measure is refused
    When I compose a budget claim with the data
      """
      {"columns": [{"name": "setup"}, {"name": "energy", "unit": "kW.h"}],
       "rows": [["LED", {"low": "0.8", "likely": "1.1", "high": "1.4"}]]}
      """
    Then it fails
    And stderr mentions "a quantity needs a column with a `measure`"

  @must-5.9.4
  Scenario: A plain value in a measured column is refused
    When I compose a budget claim with a measured column holding "1.1"
    Then it fails
    And stderr mentions "quantities or null in a column with a `measure`"

  @must-5.9.2
  Scenario: A column's unit definition missing from depends is refused by the loader
    Given a store holding a claim whose column cites a unit claim not in depends
    When I load the store
    Then loading the store fails
    And stderr mentions "must also be listed in `depends`"

  @must-5.9.1
  Scenario: A concept goes by its PDC code and presupposes the kind it narrows
    When I compose a concept at PDC code "631.544" narrowing the kind
    Then it succeeds
    And the concept presupposes the kind

  @must-5.9.1
  Scenario: A concept whose kind is missing from depends is refused by the loader
    Given a store holding a concept whose kind is not in depends
    When I load the store
    Then loading the store fails
    And stderr mentions "defines.kind cites"

  @must-5.9.1
  Scenario: A relation concept binds slots by role to a concept or a kind
    Given a concept at PDC code "631.544" narrowing the kind
    When I compose a relation concept relating "631.544" to the kind
    Then it succeeds
    And the relation concept presupposes the concept and the kind

  @must-5.9.1
  Scenario: A relation concept naming a code with no concept in depends is refused
    When I compose a relation concept relating "631.999" to the kind
    Then it fails
    And stderr mentions "PDC code 631.999 is named"

  @must-5.9.5
  Scenario: A calculation solves a slot of a relation concept, stating its defaults
    Given a concept at PDC code "631.544" narrowing the kind
    And a relation concept relating "631.544" to the kind
    When I compose a calculation solving the relation for "share" with optional "energy"
    Then it succeeds
    And the calculation presupposes the relation concept and the default

  @must-5.9.5
  Scenario: A calculation naming a role its relation has no slot for is refused
    Given a concept at PDC code "631.544" narrowing the kind
    And a relation concept relating "631.544" to the kind
    When I compose a calculation solving the relation for "harvest" with optional "energy"
    Then it fails
    And stderr mentions "role `harvest` is not a slot"

  @must-5.5 @must-5.9.5
  Scenario: A computed value names its calculation instead of a method
    When I compose an empirical claim derived by the multiplication
    Then it succeeds

  @must-5.5
  Scenario: A claim naming both a method and a derivation is refused
    When I compose an empirical claim with both a method and a derivation
    Then it fails
    And stderr mentions "never both"

  @must-5.9.2 @must-5.9.3
  Scenario: A unit that does not measure the column's kind is refused
    When I compose a budget claim with trays per batch in the kind of energy per tray
    Then it fails
    And stderr mentions "but `electrical energy per tray` is"

  @must-5.9.2
  Scenario: A unit naming a symbol nothing declares is refused
    When I compose a budget claim whose energy column is in "kW.h/{trays}"
    Then it fails
    And stderr mentions "{trays}"

  @must-5.9.4
  Scenario: A quantity whose keys are not the measure's parameters is refused
    When I compose a budget claim with energy per tray as the quantity
      """
      {"low": "0.8", "high": "1.4"}
      """
    Then it fails
    And stderr mentions "exactly its measure's parameters"

  @must-5.9.2
  Scenario: Units in a system this build does not implement are left unchecked, not passed
    Given a definition of the system "SI" version "9"
    When I compose a budget claim with energy per tray under that system
    Then it succeeds
    And stderr mentions "unchecked"
