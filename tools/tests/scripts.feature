Feature: The maintainer scripts in tools/ and spec/
  These scripts are not protocol code and the functional suite in tests/
  never runs them, so these scenarios load each one as a module and run it
  in-process. `make script-tests` runs them under coverage for SonarQube
  Cloud.

  Scenario: Audit finds the specification consistent
    Then audit finds the specification consistent

  Scenario: Audit reads a path given
    Then audit reads a path given

  Scenario: Audit reports its findings
    Then audit reports its findings

  Scenario: Audit refuses a path outside
    Then audit refuses a path outside

  Scenario: Must coverage writes the report
    Then must coverage writes the report

  Scenario: Must coverage without a specification
    Then must coverage without a specification

  Scenario: Must coverage fails under the floor
    Then must coverage fails under the floor

  Scenario: Must coverage refuses a report outside
    Then must coverage refuses a report outside

  Scenario: Wiki seed fetches the index
    Then wiki seed fetches the index

  Scenario: Wiki seed runs as a script
    Then wiki seed runs as a script

  Scenario: Wiki seed writes each lead sentence
    Then wiki seed writes each lead sentence

  Scenario: Wiki seed requires index and titles
    Then wiki seed requires index and titles

  Scenario: Drawn is below its bound and read from sha 256
    Then drawn is below its bound and read from sha 256

  Scenario: H3 vectors are the committed ones
    Then h3 vectors are the committed ones

  Scenario Outline: Each script confines its paths to the working directory or a temporary one
    Given the script <script>
    When it confines "sub/file"
    Then it admits the path in the working directory

    Examples:
      | script                 |
      | spec/audit.py          |
      | tools/must-coverage.py |
      | tools/wiki-seed.py     |

  Scenario Outline: Each script admits a temporary directory
    Given the script <script>
    When it confines "a file in a temporary directory"
    Then it admits the path in the temporary directory

    Examples:
      | script                 |
      | spec/audit.py          |
      | tools/must-coverage.py |
      | tools/wiki-seed.py     |

  Scenario Outline: Each script refuses a path anywhere else, or a climb out
    Given the script <script>
    When it confines "<path>"
    Then it refuses, saying "must be in the working directory"

    Examples:
      | script                 | path                          |
      | spec/audit.py          | /etc/passwd                   |
      | tools/must-coverage.py | /etc/passwd                   |
      | tools/wiki-seed.py     | /etc/passwd                   |
      | spec/audit.py          | ../../../../../../etc/passwd  |
      | tools/must-coverage.py | ../../../../../../etc/passwd  |
      | tools/wiki-seed.py     | ../../../../../../etc/passwd  |

  Scenario Outline: wiki-seed refuses a path outside the working directory
    When wiki-seed is given a <flag> outside the working directory
    Then it refuses, naming <flag>

    Examples:
      | flag     |
      | --titles |
      | --index  |
      | --out    |
