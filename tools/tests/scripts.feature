Feature: The maintainer scripts in tools/
  These scripts are not protocol code and the functional suite in tests/
  never runs them, so these scenarios load each one as a module and run it
  in-process. `make script-tests` runs them under coverage for SonarQube
  Cloud.

  Scenario: Audit finds the specification consistent
    When the script "tools/spec-audit.py" runs
    Then the result is "0"
    And it prints "specification.md: consistent"

  Scenario: Audit reads a path given
    Given a scratch directory
    And a file "index.md" copied from "design/spec/specification.md"
    When the script "tools/spec-audit.py" runs with "index.md"
    Then the result is "0"
    And it prints "consistent"

  Scenario: Audit reports its findings
    Given a scratch directory
    And a file "index.md" holding:
      """
      ## 1. Only

      See Section 9.
      """
    When the script "tools/spec-audit.py" runs with "index.md"
    Then the result is "1"
    And it prints "finding(s)"

  Scenario: Audit refuses a path outside
    When the script "tools/spec-audit.py" runs with "/etc/hostname"
    Then it is refused, saying "the specification"

  Scenario: Must coverage writes the report
    Given a scratch directory
    And a file "index.md" copied from "design/spec/specification.md"
    When the script "tools/must-coverage.py" runs with "--spec index.md --report COVERAGE.md"
    Then the result is "0"
    And the file "COVERAGE.md" includes "# Conformance coverage"
    And it prints a line matching "report written to */COVERAGE.md"

  Scenario: Must coverage without a specification
    Given a scratch directory
    When the script "tools/must-coverage.py" runs with "--spec absent.md"
    Then the result is "0"
    And it prints "specification not found"

  Scenario: Must coverage fails under the floor
    Given a scratch directory
    And a file "index.md" holding:
      """
      ## 99. Untested

      An implementation MUST do this.
      """
    When the script "tools/must-coverage.py" runs with "--spec index.md --fail-under 50"
    Then the result is "1"

  Scenario: Must coverage refuses a report outside
    When the script "tools/must-coverage.py" runs with "--report /etc/COVERAGE.md"
    Then it is refused, saying "--report"

  Scenario: Wiki seed fetches the index
    Given a scratch directory
    And downloads are recorded instead of made
    When the script "tools/wiki-seed.py" runs with "--fetch-index index.bz2"
    Then it is not refused
    And the result is empty
    And it downloaded the enwiki index to "index.bz2"

  Scenario: Wiki seed runs as a script
    Given a scratch directory
    And downloads are recorded instead of made
    When the program "tools/wiki-seed.py" runs with "--fetch-index index.bz2"
    Then it is not refused
    And it downloaded the enwiki index to "index.bz2"

  Scenario: Wiki seed writes each lead sentence
    Given a scratch directory
    And a multistream index "index.bz2" listing:
      """
      100:7:Alpha
      100:8:Redirect
      900:9:Beta
      """
    And a file "titles.txt" holding:
      """
      Alpha
      Redirect
      Absent
      """
    And the dump's stream holds a page "Alpha", revision "41", reading "'''Alpha''' is the first letter of the Greek alphabet. More follows."
    And the dump's stream holds a page "Redirect", revision "42", reading "#REDIRECT [[Alpha]]"
    When the script "tools/wiki-seed.py" runs with "--index index.bz2 --titles titles.txt --out seed.jsonl"
    Then it is not refused
    And the dump was read once, from byte 100 to byte 900
    And the JSON in "seed.jsonl" has "title" equal to "Alpha"
    And the JSON in "seed.jsonl" has "page_id" equal to "7"
    And the JSON in "seed.jsonl" has "revision" equal to "41"
    And the JSON in "seed.jsonl" has "lead" equal to "Alpha is the first letter of the Greek alphabet."

  Scenario: Wiki seed requires index and titles
    When the script "tools/wiki-seed.py" runs with "--titles titles.txt"
    Then it is refused

  Scenario: Drawn is read from SHA-256
    When the vector generator draws a number below 1000 from "lat 0"
    Then the result is "751"

  Scenario: Drawn is below its bound
    When the vector generator draws a number below 7 from each of "x 0" to "x 99"
    Then the result is "[0, 1, 2, 3, 4, 5, 6]"

  Scenario: H3 vectors are the committed ones
    Given files the vector generator writes are recorded instead of written
    When the vector generator makes the H3 cell vectors
    Then what it wrote to "crates/publet-algorithms/testdata/h3.json" is what is committed there

  Scenario Outline: Each script confines its paths to the working directory or a temporary one
    Given a scratch directory
    When the script <script> confines "sub/file"
    Then it admits the path "sub/file" in the scratch directory

    Examples:
      | script                 |
      | tools/spec-audit.py    |
      | tools/must-coverage.py |
      | tools/wiki-seed.py     |

  Scenario Outline: Each script admits a temporary directory
    When the script <script> confines a file in a temporary directory
    Then it admits that file

    Examples:
      | script                 |
      | tools/spec-audit.py    |
      | tools/must-coverage.py |
      | tools/wiki-seed.py     |

  Scenario Outline: Each script refuses a path anywhere else, or a climb out
    Given a scratch directory
    When the script <script> confines "<path>"
    Then it is refused, saying "must be in the working directory"

    Examples:
      | script                 | path                          |
      | tools/spec-audit.py    | /etc/passwd                   |
      | tools/must-coverage.py | /etc/passwd                   |
      | tools/wiki-seed.py     | /etc/passwd                   |
      | tools/spec-audit.py    | ../../../../../../etc/passwd  |
      | tools/must-coverage.py | ../../../../../../etc/passwd  |
      | tools/wiki-seed.py     | ../../../../../../etc/passwd  |

  Scenario Outline: wiki-seed refuses a path outside the working directory
    Given a scratch directory
    And a multistream index "index.bz2" listing:
      """
      100:7:Alpha
      """
    And a file "titles.txt" holding "Alpha"
    And the dump's stream holds nothing
    When the script "tools/wiki-seed.py" runs with "<arguments>"
    Then it is refused, saying "<flag>"

    Examples:
      | flag     | arguments                                                      |
      | --titles | --index index.bz2 --titles /etc/seed-test --out out.jsonl      |
      | --index  | --index /etc/seed-test --titles titles.txt --out out.jsonl     |
      | --out    | --index index.bz2 --titles titles.txt --out /etc/seed-test     |
