Feature: pub sign --restore-key rebuilds a key from its secret
  A backup of a signing key holds the secret alone, .publet/signing.key, not
  the key object or `author`. Put back on a machine whose store lacks them,
  `pub sign --restore-key` rebuilds the key object from the secret and the
  principal, label and creation time it was made with: the same object, with
  the same identifier, which `author` then names again. It never replaces a
  key `author` names that the store holds.

  Background:
    Given a workspace whose key was generated, and its secret kept

  Scenario: A restored secret is the same key again, and signs again
    Given a fresh workspace holding only that secret
    When I run pub "sign" "--restore-key" "--principal=human" "--expect={key}"
    Then it succeeds
    And it prints "key      {key}"
    And the workspace's author is that key
    And the workspace signs with it

  Scenario: With other settings it is another key, and --expect refuses it
    Given a fresh workspace holding only that secret
    When I run pub "sign" "--restore-key" "--principal=organization" "--expect={key}"
    Then it fails
    And stderr mentions "not {key}; check them; nothing was changed"
    And the workspace's author is not that key

  Scenario: A key the store holds as author is never replaced
    Given a workspace with a key of its own, holding that secret instead
    When I run pub "sign" "--restore-key" "--principal=human"
    Then it fails
    And stderr mentions "`author` names the key"

  Scenario: Without a secret there is nothing to restore
    Given a fresh workspace without a secret
    When I run pub "sign" "--restore-key" "--principal=human"
    Then it fails
    And stderr mentions "nothing to restore"

  Scenario: Restoring and generating are different commands
    Given a fresh workspace holding only that secret
    When I run pub "sign" "--restore-key" "--generate-key" "--principal=human"
    Then it fails
    And stderr mentions "are different commands; give one"
