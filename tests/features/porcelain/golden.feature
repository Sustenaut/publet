Feature: The same input composes to the same bytes, release after release
  A corpus gathered with one pub keeps its objects when a later pub runs,
  but only if the later pub writes the same bytes for the same input: an
  identifier is the hash of the bytes. These fixtures are composed under a
  fixed author and time and compared with the identifiers committed in
  tests/golden/tallinn.json, so a change to what compose writes fails here
  unless it is deliberate.

  Scenario: The Tallinn fixtures compose to the committed identifiers
    Given a workspace authored by a fixed key with the Tallinn basement
    Then each object composed has the identifier committed for it
