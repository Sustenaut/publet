---
package: publet-cli
version: 0.4.0
standard: bc3c5b6eeba4757b5d96bc00be2d0a1d3221bef89072b06a271c2b28e2205e34
blocking: 0
date: 2026-11-05
auditor: rust-crate-quality
commit: 9ec100f0238d90951c18da6df53912fde5994519
last-release: v0.3.0
---

# Quality audit: publet-cli 0.4.0

This report audits publet-cli against the Rust crate standard named above.
publet-cli is a command-line tool (binary only), so section 9 applies. It is
installed from git and is not on crates.io, so this release has no `cargo
publish`. The changes since v0.3.0 are the three signature-checking pull
requests:

- #96 checks generation records' signatures in `pub-sync`, `pub-delta` and a
  corpus's pinned parents, and writes when signatures are checked into spec 4.4.
- #97 counts only evidence its author signed in `pub why` and `pub-index`.
- #99 shows each object's signature status in `pub read` and `pub bundle`.

They are recorded as two `changed` rows and one `added`, which below 1.0 gives
0.4.0. publet-core and publet-algorithms do not change, so they are not
released.

The auditor wrote #96, #97 and #99, so its review of them is not independent.
A second reader of `crates/publet-domain/src/signature.rs`,
`crates/publet-eval/src/gather.rs` and the new `Graph::signature_status` would
add something this report cannot.

## Blocks a release

None. The machine's blocking finding is reclassified as finding 1, as in the
0.2.2 to 0.3.0 audits.

## Falls short of the standard

1. **RS-PKG-01 and RS-PKG-02, packaging (reclassified from "Blocks a
   release").** `cargo publish --dry-run --locked -p publet-cli` fails, because
   publet-cli depends by path on crates that are not on crates.io. It is never
   published there, so this cannot break a publish. Carried forward from 0.3.0,
   finding 1, including the decision it asks of a person: `publish = false` with
   an exception in `pubkit.json`, or publishing the workspace crates.
2. **Section 9, metadata (`porcelain/Cargo.toml`).** No `documentation`,
   `keywords`, `categories`, `readme`, `include` or `publish = false`. Carried
   forward from 0.3.0, finding 2.
3. **Section 9, README: "Why this tool" and "Related tools".** Carried forward
   from 0.3.0, finding 3.
4. **Section 9, usage text.** `pub --help` prints to stderr and exits 2, and no
   subcommand or plumbing command has a `--help`. Carried forward from 0.3.0,
   finding 4.
5. **Section 9 and section 2's `# Errors`: the requirement check's docs.**
   Unchanged. Carried forward from 0.3.0, finding 5.
6. **Section 9, end-to-end tests.** No scenario runs `pub sync`, `pub witness`,
   `pub document` or `pub --help`. Carried forward from 0.3.0, finding 6. The new
   behaviour is covered: `record_signatures.feature` through `pub-delta`,
   `signed_sync.feature` through `pub-serve` and `pub-sync`, two corpus scenarios
   for pinned parents, `evaluation_signatures.feature` through `pub why`, and
   `signature_status.feature` through `pub read` and `pub bundle`. `pub-index`'s
   warning is not run by any scenario.
7. **Section 9, the versioned interface, for the plumbing commands.** Carried
   forward from 0.3.0, finding 7.
8. **Section 4, entry points without a fuzz target.** `publet_net::wire::unpack`
   (`SECURITY.md:68-69`) and `ProseClaim::from_object` are carried forward from
   0.3.0, finding 8. The new code reads objects from a peer in `pub-sync` and from
   a directory in `pub-delta`. It parses them with `Object::parse`, which is
   fuzzed, and verifies signatures with `publet_core::verify`, which is fuzzed by
   `signature_verify`. By reading, `check_records`, `records_of` and
   `signature_graph` do not index, and do no arithmetic on values from outside.

## Worth considering

9. **Section 4, `pub-serve` scans its whole store for each delta.** To send
   each record's signatures and keys (#96), `signatures_of` in
   `crates/publet-net/src/server.rs` reads every held object on every delta
   request. A client repeating requests makes the node do work in proportion to
   its store. An index of signatures by target would bound it.
10. **The rule for unsigned records is a policy choice.** Unsigned records are
    accepted, with a warning, until a domain's first signed one. An attacker could
    therefore strip the signatures from a domain that has not signed yet. David
    chose this on 2026-11-03, and `publet_domain::unsigned_accepted` is the one
    place to change it.
11. **What users see changes.** A local annotation no longer counts in `pub why`
    until its author signs it. The README says so, and it is recorded as
    `changed`. Nothing else in the release notes it beyond that row.
12. **Debug builds optimise three dependencies** (`curve25519-dalek`,
    `ed25519-dalek`, `sha2`, in `Cargo.toml`). This changes nothing in a release
    build. It keeps the debug suite at about 64 seconds.
13. **Section 3, property tests.** proptest is not a dev-dependency of
    publet-cli. Carried forward from 0.3.0, finding 11.
14. **Carried forward from 0.3.0, unchanged:** the 4 KiB limit can split a
    character (finding 12); the README install line (finding 13); exit codes for
    usage errors (finding 14); semicolons joining two ideas (finding 15); a load
    fails whole on an unreadable object (finding 9); the load warning printed by a
    library (finding 10); parsing cost at the 1 MiB limit (finding 16).

## Sections met

- **Section 3, test vectors:** publet-cli has none of its own. The evaluation
  vectors and their pinned output are unchanged, since they hold gathered
  evidence, and `tools/check-eval-digest.sh` passes on `014f9e6a936bf4bf`.
- **Section 3, oracles:** signatures in the new scenarios are made by
  `tests/support/signing.py` with the `cryptography` package's Ed25519, which is
  independent of publet's code.
- **Section 3 and section 9, `// covers:` comments:** optional for a binary.
  `porcelain/` has none. The new tests in `publet-domain` and `publet-eval` carry
  them, and were read: each exercises what it names.
- **Section 5, README:** as 0.3.0 found. The README now says what `pub why`
  counts, how to sign, and what `pub read` and bundles show about signatures.
- **Section 7, `SECURITY.md`:** unchanged, as is what it describes. Finding 8
  says what is not fuzzed.
- **Section 9, module docs:** the new `crates/publet-domain/src/signature.rs`
  opens with `//!` docs saying what it does and why. `gather.rs`'s module docs say
  what counts.
- **Section 9, the versioned interface:**
  - `pub-sync`, `pub-delta` and corpus commands refuse what they accepted before.
  - `pub why` and `pub-index` count less.
  - `pub read` prints a new line, and `--json` and bundles carry a new field.

  All of this is recorded: two `changed` rows and one `added`.
- **Section 9, semver checks:** not applicable to a binary.
- **Not applicable to a command-line tool:** the library rules in sections 1.1 to
  1.9 and 2.1 to 2.7, and the docs.rs build.

## Claims verified

- `pubrel next` gives publet-cli 0.4.0, and nothing for publet-core or
  publet-algorithms.
- `cargo test -p publet-cli`: 46 tests pass.
- The scenarios named in finding 6 pass on main at `9ec100f`.
- `tools/check-eval-digest.sh`: clean on the same digest as v0.3.0.

## Checks run

| Check | Result |
|---|---|
| `cargo doc -p publet-cli --no-deps` | pass, by `pubkit audit prepare` |
| `cargo clippy -p publet-cli --all-targets` | pass, by `pubkit audit prepare` |
| `cargo clippy -p publet-cli -- -W clippy::missing_docs_in_private_items` | 0 undocumented private items, by `pubkit audit prepare` |
| `pub --help` | exit 2, by `pubkit audit prepare` |
| `cargo test -p publet-cli` | pass, 46 tests |
| `cargo publish --dry-run --locked -p publet-cli` | fails, see finding 1 |
| `cargo +1.98 check --locked -p publet-cli` (MSRV) | pass, by `pubkit audit prepare` |
| `make vectors-check`, `make supply-chain-check`, `make deny`, `make vet` | pass, by `pubkit audit prepare` |
| `make check` on this branch | see the pull request |

## Checks not run

- `make fuzz-smoke`: CI runs it in the merge queue and on main.
- `cargo test --doc` and the docs.rs build: publet-cli has no library target.
