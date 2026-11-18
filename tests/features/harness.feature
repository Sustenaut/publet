Feature: The functional harness is wired correctly
  # Phase 0 delivers the harness before the first binary exists, so that no
  # later phase can defer writing its scenarios.

  Scenario: Binaries are resolved from the environment, not a build path
    Given the program under test is "pub"
    When I run "pub --version"
    Then it succeeds
    And it prints a line matching "pub *"
    And the program it ran is the one in the directory PUBLET_BIN_DIR names
