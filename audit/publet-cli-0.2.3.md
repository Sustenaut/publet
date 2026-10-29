---
package: publet-cli
version: 0.2.3
standard: bc3c5b6eeba4757b5d96bc00be2d0a1d3221bef89072b06a271c2b28e2205e34
blocking: 0
date: 2026-10-29
auditor: rust-crate-quality
commit: 55df6a4f0de677c4e6c2824314cd06d9ea9a8930, with this branch's changes on top (see below)
last-release: v0.2.2
---

# Quality audit: publet-cli 0.2.3

This report audits publet-cli against the Rust crate standard named above.
It started from the draft `pubkit audit prepare` (pubkit 0.15.2) wrote, and
each rule that draft left for review was judged by reading the code and
docs. 0.2.3 is the version to release (`pubrel next --package publet-cli`),
after `v0.2.2`. This file should be committed with the release's changes.

The tree audited is `main` at `55df6a4`, with this branch's changes on top
of it. Those changes were not yet committed when the audit was made. They
are in `README.md`, `porcelain/src/requirement.rs`,
`tests/features/porcelain/require.feature` and
`corpus/publets/pkg.publet-cli/unreleased.json` (a `fixed` row). They fix
what this audit first found in #74, and are listed under "Resolved on this
branch". The audit was run again against them.

publet-cli is a crate with only a binary target (`pub`, in `porcelain/`), so
section 9 applies. It is installed from git (`release.json`, `install`:
`cargo install --locked --git ... --tag {tag} publet-cli`) and is not on
crates.io. The only change since v0.2.2 is publet #74, with this branch's
fixes to it. #74 lets a project state the `pub` it needs in
`pub-version.txt` or as `pub=` in `.publet/config`. `pub` checks that before
dispatch (`porcelain/src/requirement.rs`, and `porcelain/src/main.rs:86-95`).
#74 also adds the `pub require` command and a new unknown-command message.
The change was read line by line and run against edge-case inputs (see
"Claims verified").

## Blocks a release

None. The one finding that blocked, a false claim about exit codes, is
fixed on this branch (see "Resolved on this branch", R1).

## Falls short of the standard

1. **RS-PKG-01 and RS-PKG-02, packaging (reclassified from "Blocks a
   release").** `cargo publish --dry-run --locked -p publet-cli` fails:
   "failed to select a version for the requirement `publet-algorithms =
   \"^0.2.2\"`", because crates.io has publet-algorithms 0.2.1 and 0.2.0
   only. Once that is published it would still fail: `cargo info` finds no
   publet-graph, publet-store, publet-net, publet-quantity, publet-eval or
   publet-domain on crates.io, and publet-cli depends on each by path
   (`porcelain/Cargo.toml:15-22`).

   The check the rule names passes. `make publish-check` packages
   `PUBLISHED := publet-core publet-algorithms` (`Makefile:63`,
   `pubkit.mk:102-105`), and `pubkit.json` lists only those two under
   `published`. publet-cli is never published to crates.io. It is installed
   from git, and the README says so (`README.md:375-376`, "from git, until
   the workspace's crates are published on crates.io"). So the failure
   cannot break a publish, and this release does not depend on it. The
   0.2.2 audit judged the same situation as falling short (its findings 4
   and 5), and nothing about it has changed since, so this report does the
   same.

   What still falls short:
   - Section 6 requires `publish-check`, `msrv` and `supply-chain-check`
     for a binary-only crate, and all three cover only the two libraries.
   - Nothing in CI builds `pub` on its `rust-version`. It does build:
     `cargo +1.98 check --locked -p publet-cli` passes.
   - No `SUPPLY-CHAIN.md` describes `pub`'s dependency tree.
   - `license = "Apache-2.0"` is declared, and `LICENSE` is at the
     repository root. `porcelain/` has neither a copy nor an `include`, so a
     package of it would not ship the licence.

   A person should decide between `publish = false` together with an
   exception in `pubkit.json` for RS-PKG-01 and RS-PKG-02 (section 11:
   rule, reason, date), and publishing the workspace crates.
2. **Section 9, metadata (`porcelain/Cargo.toml:1-8`).** It sets
   `description`, `license`, `repository` and `rust-version`. It has no
   `documentation` (the standard asks for the README's URL in the
   repository), no `keywords`, no `categories`, no `readme`, no `include`
   list, and no `publish = false`, though it cannot be published (finding
   1). Carried forward from 0.2.2, finding 4.
3. **Section 9, README: "Why this tool" and "Related tools".** The README
   explains its design choices one at a time ("`pub why` never reduces a
   standing to a badge", `README.md:225`). It has no section saying what
   `pub` does that a general-purpose tool would get wrong. It has no table
   of related tools with the version or date checked and how. Every row
   would need a check that was run, so this audit wrote none. Carried
   forward from 0.2.2, finding 6.
4. **Section 9, usage text (`porcelain/src/main.rs:44-77`).** `pub --help`
   prints its 1840 bytes to stderr and exits 2. The standard asks for stdout
   and exit 0. It names every command, but not their flags (`pub compose`
   alone takes 21), and no subcommand has a `--help` of its own. It does not
   name the aliases `-h`, `help` and `version` (`main.rs:115, 126`). None of
   the plumbing commands in `bin/` handles `--help`. #74 added `require
   [REQ]` to it, which agrees with the README. These are code changes.
   Carried forward from 0.2.2, finding 3.
5. **Section 9 and section 2's `# Errors`: what remains imprecise in the
   requirement check's docs.** Each was checked against a run.
   - `README.md:202-205` says that when "what it finds is not a
     requirement", `pub` stops "naming the requirement, where it was
     stated, and the `cargo install` line for a release that meets it".
     For a malformed requirement it names the requirement and the file, but
     prints no install line. It asks for a well-formed requirement instead
     (`requirement.rs:126-130`). This was run with `latest`.
   - The exit-code paragraph (`README.md:218-222`) does not list `pub
     require` with more than one argument, which exits 2 with a usage line
     (`requirement.rs:197`). It is judged imprecise rather than false,
     because the paragraph already gives 2 to the other usage error, no
     command. A declaring file that is not UTF-8 also exits 2. The README
     covers that case only if "not a requirement" is read to include it.
   - `check`'s `# Errors` (`requirement.rs:121-123`) says it fails "when
     this build does not meet it". It also fails when the requirement is
     not well formed (`requirement.rs:125-131`). `enforce`'s `# Errors`
     (`requirement.rs:163-165`) says the same, and it also fails when a
     declaring file cannot be read as text (`requirement.rs:173`).
6. **Section 9, end-to-end tests.** #74 is tested by nine scenarios
   (`tests/features/porcelain/require.feature`), which pass. They now
   include a malformed requirement and `pub require` with nothing given,
   with and without a declaration. None runs an empty `pub=` or a file that
   is not UTF-8. The scenario "A met requirement lets every command run"
   (`require.feature:25`) runs `init` only. Carried forward from 0.2.2,
   finding 7: no scenario runs `pub sync`, `pub witness`, `pub document` or
   `pub --help`. `pub --version` is now run once (`require.feature:55`),
   checking only that it succeeds. This was checked by searching
   `tests/steps`, `tests/support` and `tests/features` for each command.
7. **Section 9, the versioned interface, for the plumbing commands.** Their
   exit codes differ between commands. "Not found" is 3 in four of them and
   1 in another. They are listed only as `EXIT_*` constants in each
   `bin/*/src/main.rs`. `bin/` is unchanged since v0.2.2. Carried forward
   from 0.2.2, finding 8.
8. **Section 4, an entry point without a fuzz target.** `publet_net::wire::
   unpack` decodes a peer's bytes for `pub sync` and has no target in
   `fuzz/fuzz_targets/`. `SECURITY.md:68-69` says so. Carried forward from
   0.2.2, finding 9.

   #74 adds text from outside that `pub` reads on every command: a
   `pub-version.txt` in a cloned repository. This branch bounds it. Only
   regular files are read, at most 4096 bytes of them
   (`requirement.rs:54-71`). `well_formed` (`requirement.rs:107-116`)
   admits only digits, dots, a leading `^` and a trailing `+` before
   anything reaches `publet_algorithms::version::satisfies`. By reading,
   neither function indexes or does unchecked arithmetic. A fuzz target
   for them would be cheap, but is not needed to trust them.

## Worth considering

9. **Section 3, property tests (`porcelain/Cargo.toml:27-28`).** proptest
   is not a dev-dependency of publet-cli. `well_formed` and `declared` have
   invariants worth testing over generated input. One is that every string
   `well_formed` accepts is one `satisfies` can decide. Another is that the
   nearest declaration wins.
10. **Section 4, the 4 KiB limit can split a character
    (`requirement.rs:60-69`).** The limit is applied in bytes, before UTF-8
    decoding. A valid UTF-8 `pub-version.txt` whose 4096th byte falls inside
    a multi-byte character is refused as "not UTF-8 text". It then stops
    every command with exit 2. This was run: 4095 `#` bytes, then `é`, then
    `0.1+`. A file that long is unlikely, since a requirement is one short
    line, but the message is wrong for it. Decoding only the valid prefix
    (`Utf8Error::valid_up_to`) would avoid it. That is a code change. By
    reading, a `pub=` line beyond the first 4096 bytes of `.publet/config`
    is not seen at all.
11. **README install line (`README.md:379`).** It names `--tag v0.2.0`, two
    releases behind v0.2.2. It sits under "Versions and releases" rather
    than an installation section of its own. When a requirement is not met,
    `pub` prints an install line for `publet-cli pub-store`
    (`requirement.rs:157`). The README and `release.json` install
    `publet-cli` alone, and nothing says why `pub-store` is added.
12. **Section 9, exit codes for usage errors.** `pub` exits 1 for an
    unknown command (`main.rs:134-137`, now with #74's message). It exits 2
    for no command, `--help`, `pub require` with extra arguments, and a
    requirement the build does not meet. An unknown command is a usage
    error too. Carried forward from 0.2.2, finding 23.
13. **Section 10, writing.** Some sentences carry two ideas across a
    semicolon. #74's "Which pub" paragraph has one in a parenthesis
    (`README.md:197`, "`0.2.2+`; blank lines and `#` comments are
    skipped"), and `requirement.rs:118` has another. Others are older
    (`README.md:232, 241, 263, 268, 279-280, 329, 387`). The "Which pub"
    paragraph (`README.md:196-209`) is long for one paragraph. `domain.rs:4`
    still opens with the module's history ("Until now nothing in the
    toolchain could write these object kinds"). Carried forward from 0.2.2,
    finding 22.

## Resolved on this branch

These were found in #74 by the first pass of this audit and fixed by the
uncommitted changes described above. They were checked again against the
current files, and each fix was run.

- **R1. Was blocking: section 9, a false claim about exit codes.** The
  README said `pub` exits 1 when it refuses. But `pub require` exits 2 when
  the requirement is not met, is malformed, or is neither given nor
  declared. Any command the check stops also exits 2. The paragraph now
  lists those cases (`README.md:218-222`). Running `pub require 999.0.0+`,
  `pub require latest` and `pub require` with nothing declared each gave
  exit 2. Finding 5 covers two narrow cases the paragraph still leaves out.
- **R2. Fell short: the interface did not name #74's files, and the docs
  did not name the commands the check skips.** "What a release promises"
  now lists `pub-version.txt`, the `pub=` key and the environment variable
  `PUB_IGNORE_VERSION` (`README.md:401-404`). The README now says the check
  runs before every command "except `--version`, `help` and `require`"
  (`README.md:200-201`). The module docs name all six spellings the code
  skips (`requirement.rs:13-14`, `main.rs:90`). The README's three are the
  documented forms, and `-h` and `--help` are spellings of `help`.
- **R3. Fell short: a malformed requirement was reported as one the build
  does not meet.** A byte-order mark is now stripped (`requirement.rs:70`).
  `#` starts a comment anywhere on a line (`requirement.rs:74-76`).
  Anything not well formed is refused by name (`requirement.rs:125-131`).
  The README now states the three forms a requirement takes
  (`README.md:199-200`). Run: `0.1+` after a byte-order mark and `0.2.2+ #
  pinned` are both accepted. `latest` gives "states \"latest\", which is
  not a version requirement" and exit 2.
- **R4. Worth considering: reading files from the directory and its
  parents.** The requirement is quoted with `{:?}`, so control characters
  are escaped. A file holding `ESC[31mRED` printed `"\u{1b}[31mRED"`, with
  no escape byte reaching the terminal. Only regular files are read
  (`requirement.rs:56-59`). A FIFO, and a symlink to `/dev/zero`, were both
  skipped, and `pub read` went on to its own error. A file that is not
  UTF-8 is now an error naming the file, not skipped
  (`requirement.rs:64-69`).
- **R5. End-to-end and unit tests.** Two scenarios were added
  (`require.feature:58, 67`). Two unit tests were added too:
  `only_requirements_are_accepted_and_others_are_quoted` and
  `a_fifo_or_an_oversized_file_never_blocks_the_check`. Both were read.
  They exercise `well_formed`, `check`'s quoting, and `declared`'s FIFO and
  size handling, as their names say.

These changes alter documentation and code, and are recorded in
`corpus/publets/pkg.publet-cli/unreleased.json` as `fixed`.

## Sections met

- **Section 3, test vectors:** publet-cli has none of its own, and the
  standard asks for them only when a crate has them. `make vectors-check`
  passes for the repository's vectors, which belong to the libraries.
- **Section 3, oracles:** no established tool implements what `pub` does
  for comparison. The oracles for CBOR and RFC 6962 belong to the libraries
  (`SECURITY.md:86-87`).
- **Section 3 and section 9, `// covers:` comments:** optional for a binary.
  `porcelain/` has none, including #74's four unit tests. All four were
  read and do what their names say.
- **Section 5, README:** for a binary-only crate the README is the
  documentation (section 9). It has:
  - usage;
  - a runnable example (`README.md:149-157`);
  - the minimum Rust version and its policy (`README.md:408-412`);
  - a Security section saying how to report, and pointing to `SECURITY.md`
    for the checks (`README.md:318-323`).

  The draft's findings that the README has no Minimum Rust version section
  and no installation section went by headings. The content is there, as
  bold paragraphs. Finding 11 covers where the install line sits.
- **Section 7, `SECURITY.md`:** it says how to report privately, the
  supported versions of publet-cli, what is checked and when, and what
  fuzzing found. It names what is fuzzed without claiming more, and says
  that `wire::unpack` has no target.
- **Section 8, cross-platform:** the `cross` job runs `--workspace
  --all-features` (`pubkit.json`), so it includes `pub`.
- **Section 9, the README's coverage:** it says what the tool is for and
  gives its central use, an overview of its commands, the minimum Rust
  version and versioning. #74's `pub require` is listed (`README.md:193`)
  and agrees with `--help`. The changes are recorded as `added` and `fixed`,
  which below 1.0 bump 0.2.2 to 0.2.3.
- **Section 9, module docs:** `requirement.rs` opens with `//!` docs saying
  what it does and why, and so do `main.rs` and every other module.
  `cargo clippy -p publet-cli -- -W clippy::missing_docs_in_private_items`
  reports 391 items, all module-private. No `pub(crate)` item is
  undocumented, including #74's `LIMIT`, `Declared` and `well_formed`.
- **Section 9, semver checks:** not applicable to a binary. `release.json`
  does not set `semver-checks` for publet-cli, as is correct.
- **Not applicable to a command-line tool:** the library rules in sections
  1.1 to 1.9 and 2.1 to 2.7, and the docs.rs build.

## Claims verified

- #74's behaviour, run with `target/debug/pub` built from this tree in a
  scratch directory:
  - An unmet requirement (`999+`) stops `pub read` with exit 2, naming the
    requirement and the file.
  - `pub --version` prints and exits 0 even when the declaring file is not
    UTF-8.
  - `PUB_IGNORE_VERSION=1` skips the check (a scenario, passing).
- Each input under "Resolved on this branch" and in finding 10 was run as
  described there.
- `pub require a b`: exit 2 with the usage line. `pub nonesuch`: exit 1,
  with "This is pub 0.2.2" and an install line.
- `pub --help`: 1840 bytes on stderr, none on stdout, exit 2.
- crates.io: `cargo info` finds publet-core 0.1.4 and publet-algorithms
  0.2.1. It finds no publet-cli, publet-graph, publet-store, publet-net,
  publet-quantity, publet-eval or publet-domain.
- The pubrel bump rule below 1.0 (`added` and `fixed` bump the patch
  number): the README's table (`README.md:347-352`), as verified for 0.2.2.

## Checks run

On the current tree, with this branch's changes:

| Check | Result |
|---|---|
| `make doc` | pass |
| `make lint` | pass |
| `cargo test -p publet-cli` | pass, 44 tests, including #74's four |
| `make functional` | pass, 364 scenarios, including #74's nine |
| `cargo +1.98 check --locked -p publet-cli` (MSRV) | pass |
| `cargo clippy -p publet-cli -- -W clippy::missing_docs_in_private_items` | 391 module-private items, no `pub(crate)` item |
| `make msrv` | pass; it builds publet-core and publet-algorithms only |
| `make publish-check` | pass; it packages publet-core and publet-algorithms only |
| `make doc-coverage-check` | pass; libraries only, not required of a binary |
| `make supply-chain-check` | pass; publet-core and publet-algorithms only |
| `make vectors-check` | pass |
| `cargo publish --dry-run --locked -p publet-cli` | fails: publet-algorithms ^0.2.2 is not on crates.io (finding 1) |
| `make deny`, `make vet` | pass at `55df6a4`, run by the draft; this branch changes no dependency |

## Checks not run

- `cargo test --doc` and the docs.rs build: publet-cli has no library
  target, and docs.rs renders nothing for a binary.
- `make fuzz-smoke`: not on this audit's list. CI runs it on the release
  pull request.
