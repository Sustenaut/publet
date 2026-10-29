@porcelain
Feature: A project says which pub it needs, and pub says when it is not that one
  A project states a version requirement for pub in pub-version.txt, or as
  pub= in a workspace's .publet/config. pub looks for it in the current
  directory and its parents, and stops before running anything when this
  build does not meet it, naming the release to install. Nothing is fetched.

  Scenario: A command this release does not have names the release and how to update
    Given an empty directory
    When I run pub with "nonesuch"
    Then it fails
    And stderr mentions "unknown command: nonesuch"
    And stderr mentions "This is pub "
    And stderr mentions "cargo install --locked --git https://github.com/schryer/publet"

  Scenario: A project needing a newer pub stops it before anything runs
    Given an empty directory
    And the directory needs pub "999.0.0+"
    When I run pub with "init"
    Then it exits 2
    And stderr mentions "this project needs pub 999.0.0+ (from"
    And stderr mentions "--tag v999.0.0"
    And no workspace was created

  Scenario: A met requirement lets every command run
    Given an empty directory
    And the directory needs pub "0.1+"
    When I run pub with "init"
    Then it succeeds

  Scenario: A workspace's requirement is found from a directory inside it
    Given a workspace that needs pub "999.0.0+"
    When I run pub with "read" from a directory inside it
    Then it exits 2
    And stderr mentions "config)"

  Scenario: The check can be skipped on purpose
    Given an empty directory
    And the directory needs pub "999.0.0+"
    When I run pub with "init" and PUB_IGNORE_VERSION=1
    Then it succeeds

  Scenario: A script asks whether this pub meets a requirement
    Given an empty directory
    When I run pub with "require 0.1+"
    Then it succeeds
    And stderr is empty
    When I run pub with "require 999.0.0+"
    Then it exits 2
    And stderr mentions "this project needs pub 999.0.0+ (from the command line)"

  Scenario: The version is shown even when the requirement is not met
    Given an empty directory
    And the directory needs pub "999.0.0+"
    When I run pub with "--version"
    Then it succeeds

  Scenario: Something that is not a requirement is refused by name
    Given an empty directory
    And the directory needs pub "latest"
    When I run pub with "init"
    Then it exits 2
    And stderr mentions "which is not a version requirement"
    When I run pub with "require latest"
    Then it exits 2

  Scenario: pub require with nothing given checks the requirement declared here, or says there is none
    Given an empty directory
    When I run pub with "require"
    Then it exits 2
    And stderr mentions "no requirement given, and none declared here"
    Given the directory needs pub "0.1+"
    When I run pub with "require"
    Then it succeeds

