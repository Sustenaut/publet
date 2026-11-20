@porcelain
Feature: pub dates the keys and signatures it makes when it makes them
  `created` is the signer's claim of when it signed (Section 4.3). A key
  `pub sign --generate-key` makes, and a signature `pub sign`, `pub build`
  or `pub publish` makes, is dated now, to the second, in UTC. --created
  dates one otherwise, and $PUB_CREATED pins every one, for tests and
  reproducible runs.

  Background:
    Given a workspace to sign in

  Scenario: Unpinned, a new key is dated now
    Given pub's dates are not pinned
    When I make a key
    Then it succeeds
    And the key is dated within a minute of now

  Scenario: $PUB_CREATED pins a new key's date
    Given pub's dates are pinned to "2030-01-02T03:04:05Z"
    When I make a key
    Then it succeeds
    And the key is dated "2030-01-02T03:04:05Z"

  Scenario: --created dates a key, whatever $PUB_CREATED says
    Given pub's dates are pinned to "2030-01-02T03:04:05Z"
    When I make a key with "--created=2031-05-06T07:08:09Z"
    Then it succeeds
    And the key is dated "2031-05-06T07:08:09Z"

  Scenario: Unpinned, a signature is dated now
    Given pub's dates are not pinned
    And a key and an object to sign
    When I sign the object
    Then it succeeds
    And the signature is dated within a minute of now
