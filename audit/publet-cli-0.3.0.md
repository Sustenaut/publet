---
package: publet-cli
version: 0.3.0
standard: bc3c5b6eeba4757b5d96bc00be2d0a1d3221bef89072b06a271c2b28e2205e34
blocking: 0
date: 2026-11-02
auditor: rust-crate-quality
commit: 8ad5cee19615e191d4b44c112554e0345bf246a4, with this branch's changes on top (see below)
last-release: v0.2.3
---

# Quality audit: publet-cli 0.3.0

This report audits publet-cli against the Rust crate standard named above.
publet-cli is a command-line tool (binary only), so section 9 applies. It is
installed from git and is not on crates.io. The changes since v0.2.3 are
publet #90 (PDC families and editions, the rule that definitions at a PDC code
are changed and not debated, a load that leaves out inadmissible objects, and
signed generation records), plus internal updates to the supply-chain audits.
No file under `bin/` changed, but every plumbing command that loads objects
changes behaviour through `publet_graph::load`.

The auditor wrote #90, so its review of that change is not independent. A
second reader of `crates/publet-graph/src/edition.rs` and `load.rs` would add
something this report cannot.

## Blocks a release

None. The one finding the machine marked as blocking is reclassified as
finding 1, as in the 0.2.2 and 0.2.3 audits.

## Falls short of the standard

1. **RS-PKG-01 and RS-PKG-02, packaging (reclassified from "Blocks a
   release").** `cargo publish --dry-run --locked -p publet-cli` fails, because
   crates.io has publet-algorithms 0.2.1 and 0.2.0 only. It would still fail
   after that is published: publet-graph, publet-store, publet-net,
   publet-quantity, publet-eval and publet-domain are not on crates.io. The
   check the rule names, `make publish-check`, packages only publet-core and
   publet-algorithms (`Makefile:63`). publet-cli is never published, so this
   cannot break a publish. Carried forward from 0.2.3, finding 1, including what
   still falls short: no `msrv` or `SUPPLY-CHAIN.md` covers `pub`, and a package
   of `porcelain/` would not ship the licence. A person should decide between
   `publish = false` with an exception in `pubkit.json`, and publishing the
   workspace crates.
2. **Section 9, metadata (`porcelain/Cargo.toml`).** No `documentation`,
   `keywords`, `categories`, `readme`, `include` or `publish = false`. Carried
   forward from 0.2.3, finding 2.
3. **Section 9, README: "Why this tool" and "Related tools".** Neither section
   exists. Every related-tools row would need a check that was run, so this audit
   wrote none. Carried forward from 0.2.3, finding 3.
4. **Section 9, usage text (`porcelain/src/main.rs:45`).** `pub --help` prints
   1840 bytes to stderr and exits 2. The standard asks for stdout and exit 0.
   No subcommand or plumbing command has a `--help`. Carried forward from 0.2.3,
   finding 4. Run for this report.
5. **Section 9 and section 2's `# Errors`: the requirement check's docs.**
   Unchanged by this release. Carried forward from 0.2.3, finding 5.
6. **Section 9, end-to-end tests.** No scenario runs `pub sync`, `pub witness`,
   `pub document` or `pub --help`. Carried forward from 0.2.3, finding 6. #90 is
   covered: `tests/features/conformance/families.feature` and
   `tests/features/porcelain/families.feature` drive `pub compose`, `annotate`,
   `relate`, `revise`, `bundle`, `publish`, `domain`, and the plumbing commands
   `pub-ls`, `pub-term`, `pub-lineage` and `pub-divergence`. A load that leaves an
   object out is tested through `pub-ls` and `pub domain`, and not through each
   command that loads.
7. **Section 9, the versioned interface, for the plumbing commands.** Exit codes
   differ between commands, and are listed only as `EXIT_*` constants. Carried
   forward from 0.2.3, finding 7.
8. **Section 4, entry points without a fuzz target.** `publet_net::wire::unpack`
   has none (`SECURITY.md:68-69`), carried forward from 0.2.3, finding 8. #90
   adds another: `Definition::from_value` now reads `family` and `edition` from
   objects others write, through `ProseClaim::from_object`, and no target reaches
   it, as no target reached the older sorts. By reading, `family`, `member`,
   `edition`, `numbered` and `tally` in `crates/publet-graph/src/quantity.rs` do
   not index. The one sum over values from outside, of each section's `families`,
   runs only after each is checked equal to a map's length, so it cannot overflow.
   `crates/publet-graph/src/edition.rs` adds lengths of held arrays. A target for
   `ProseClaim::from_object` would be cheap and is worth adding.

## Worth considering

9. **Section 4, a load still fails whole on an unreadable object.** #90 leaves
   out objects inadmissible given others, but a family of the wrong shape, a
   cycle-closing edge or a bad anchor from another key still makes
   `publet_graph::load` fail, and so stops every command reading that directory.
   This is the behaviour of earlier releases, not a regression.
10. **The load warning is printed by a library.** `load::report` writes to stderr
    from `publet_graph`. This guarantees every command that loads reports what it
    left out, at the cost of a library printing. publet-graph is not published.
11. **Section 3, property tests (`porcelain/Cargo.toml:27`).** proptest is not a
    dev-dependency of publet-cli. Carried forward from 0.2.3, finding 9.
12. **Section 4, the 4 KiB limit can split a character.** Unchanged. Carried
    forward from 0.2.3, finding 10.
13. **README install line.** It sits under "Versions and releases", and
    `requirement.rs:157` installs `pub-store` too, with nothing saying why.
    Carried forward from 0.2.3, finding 11.
14. **Section 9, exit codes for usage errors.** `pub` exits 1 for an unknown
    command and 2 for other usage errors. Carried forward from 0.2.3, finding 12.
15. **Section 10, writing.** The machine lists 39 lines where a semicolon joins
    two ideas, mostly older. This report read those in `README.md` and sampled
    `porcelain/src`, and judged them as the 0.2.3 audit did (its finding 13): they
    fall short of the rule and do not mislead. `bundle.rs:3` is one such line.

## Resolved on this branch

- **R1. Was wrong: the recorded change understated #90.** #90 recorded only
  `added`, which would have made this 0.2.4. The README lists exit codes,
  plumbing stdout and object shapes as the interface, and says a change to any is
  recorded as `changed`. #90 changes all of these: `pub-ls` and the rest exit 0,
  not 1, on a directory holding a refused verdict, and list one object fewer; a
  dispute on a concept, accepted by 0.2.3, is refused; `pub publish` writes a
  signature into `objects/`. This branch records `changed`, so the version is
  0.3.0.
- **R2. Fell short: the README did not name the new behaviour.** The exit-code
  paragraph now says what creating and reading such an object do.

## Sections met

- **Section 3, test vectors:** publet-cli has none of its own. `vectors/families/`
  is new, is written by `tests/support/family_vectors.py` without the code under
  test, and a scenario checks the committed files match it. Those cases are built
  by the same author as the code, so they are independent of the code and not of
  its reading of the specification.
- **Section 3, oracles:** no established tool implements what `pub` does. New
  generation signatures are checked in `tests/steps/test_families.py` with the
  `cryptography` package's Ed25519, which is independent of publet's code.
- **Section 3 and section 9, `// covers:` comments:** optional for a binary.
  `porcelain/` has none.
- **Section 5, README:** for a binary-only crate the README is the documentation.
  It has usage, a runnable example, the minimum Rust version and a Security
  section, as the 0.2.3 audit found. The machine's findings that it lacks an
  installation and a Minimum Rust version section go by headings. The content is
  there, as bold paragraphs.
- **Section 7, `SECURITY.md`:** it says how to report privately, what is checked
  and when, and what fuzzing found. Finding 8 says what it does not yet name.
- **Section 8, cross-platform:** the `cross` job runs `--workspace --all-features`,
  so it includes `pub`.
- **Section 9, the README's coverage:** it says what the tool is for, gives an
  overview of its commands, the minimum Rust version and versioning. #90 adds no
  command or flag, so the overview still holds. `--defines` takes the new sorts,
  and the specification's Section 5.9.1 defines them.
- **Section 9, module docs:** the new `crates/publet-graph/src/edition.rs` opens
  with `//!` docs saying what it does and why. The report's clippy run finds 0
  undocumented private items in `porcelain`.
- **Section 9, the versioned interface:** see R1. The bundle's new `classes` and
  `family` fields add to its shape, and `VERSION` stays 1.
- **Section 9, semver checks:** not applicable to a binary.
- **Not applicable to a command-line tool:** the library rules in sections 1.1 to
  1.9 and 2.1 to 2.7, and the docs.rs build.

## Claims verified

Run with `target/debug/pub` and plumbing built from this tree:

- `pub-ls --dir=vectors/families/drop-family-disputes` prints
  `warning: dropped <CID>: ...` and exits 0.
- `pub-ls --dir=vectors/families/reject-family-code-twice` exits 1.
- `pub --help`: 1840 bytes on stderr, exit 2.
- crates.io has publet-core 0.1.4 and publet-algorithms 0.2.1, and no
  publet-graph.
- `git diff v0.2.3 -- bin` is empty.
- The bump rule below 1.0 (`changed` bumps the minor number): `README.md`'s table
  and `pubrel next --package publet-cli`, which gives 0.3.0.

## Checks run

| Check | Result |
|---|---|
| `cargo doc -p publet-cli --no-deps` | pass, by `pubkit audit prepare` |
| `cargo clippy -p publet-cli --all-targets` | pass, by `pubkit audit prepare` |
| `cargo clippy -p publet-cli -- -W clippy::missing_docs_in_private_items` | 0 undocumented private items, by `pubkit audit prepare` |
| `cargo test -p publet-cli` | pass, 44 tests |
| `make check` at #90's last commit, `b089851` | pass, 519 functional scenarios |
| `conformance/verify-suite.sh` at `b089851` | pass, every break detected |
| `cargo publish --dry-run --locked -p publet-cli` | fails, see finding 1 |
| `cargo +1.98 check --locked -p publet-cli` (MSRV) | pass, by `pubkit audit prepare` |
| `make vectors-check`, `make supply-chain-check`, `make deny`, `make vet` | pass, by `pubkit audit prepare` |

## Checks not run

- `make fuzz-smoke` and `make functional` on this branch: CI runs them on the
  release pull request. This branch changes only this report, the README and a
  changelog fragment.
- `cargo test --doc` and the docs.rs build: publet-cli has no library target.
