---
package: publet-cli
version: 0.4.1
standard: 45390b67d5e4cbf27491f4de7ea4a2ca013482e4ebc474978fd5a1d49c65e163
blocking: 0
date: 2026-11-19
auditor: rust-crate-quality
commit: 59588fd91a70d1c054ef78f8e90220c10f1c9a12
last-release: v0.4.0
---

# Quality audit: publet-cli 0.4.1

This report audits publet-cli against the Rust crate standard named above.
publet-cli is a command-line tool (binary only), so section 9 applies. It is
installed from git, or as the static `pub` attached to each release, and is
not on crates.io, so this release has no `cargo publish`. The changes since
v0.4.0 that reach users:

- #124 adds `pub sign --restore-key [--expect=CID]`. It rebuilds the key
  object of a secret put back from a backup in `.publet/signing.key`, and
  makes `author` name it again (`porcelain/src/sign.rs`).
- `pub-serve` reads a delta's signatures from a new signature index in the
  store (`publet_store::Store::signatures_of`), not from a walk of every
  object held (`crates/publet-net/src/server.rs`). A store made before the
  index gets it built once, when it is opened.

They are recorded as one `added` row and one `fixed` row. The other eight rows
are `internal`: supply-chain updates, rustix 1.1.6 for RUSTSEC-2026-0486, a
`defines_parse` fuzz target, pubrules, the functional suite's step changes, and
publet-core's README link. Below 1.0 that gives 0.4.1 (`pubrel next --package
publet-cli`).

The auditor wrote #124, so its review of `restore` is not independent. A
second reader of `porcelain/src/sign.rs` would add something this report
cannot.

## Blocks a release

None. The machine's blocking finding is reclassified as finding 1, as in the
0.2.2 to 0.4.0 audits.

## Falls short of the standard

1. **RS-PKG-01, packaging (reclassified from "Blocks a release").** `cargo
   publish --dry-run --locked -p publet-cli` fails, because publet-cli depends
   by path on crates that are not on crates.io. It is never published there,
   so this cannot break a publish. Carried forward from 0.4.0, finding 1,
   including the decision it asks of a person: `publish = false` with an
   exception in `pubrules.json`, or publishing the workspace crates.
2. **Section 5.1 and section 9, metadata (`porcelain/Cargo.toml`).** No
   `documentation`, `keywords`, `categories` or `include`. Carried forward from
   0.4.0, finding 2.
3. **Section 9.1, README: "Why this tool", "Related tools", installation and
   Minimum Rust version.** The README installs from git and from the release
   asset under "Versions and releases", and `rust-toolchain.toml` pins the
   toolchain, but it has no sections by these names. Carried forward from
   0.4.0, findings 3 and 14.
4. **Section 9.5, usage text.** `pub --help` prints to stderr and exits 2.
   The README's command list (`README.md:211`) names `--restore-key` and
   `--expect`. Carried forward from 0.4.0, finding 4.
5. **Section 9.4, end-to-end tests.** No scenario runs `pub sync`, `pub
   witness`, `pub document` or `pub --help`. Carried forward from 0.4.0,
   finding 6. The new behaviour is covered: `tests/features/porcelain/sign.feature`
   has seven scenarios for `--restore-key`. They cover a restored secret
   signing again, other settings refused by `--expect`, an `author` the store
   holds never replaced, no secret, `--restore-key` with `--generate-key`,
   the committed key object used with no settings, and a secret that is not
   the committed key's. The signature index is covered by
   `a_targets_signatures_are_found_by_the_index` and
   `a_store_from_before_the_index_gets_it_built_when_opened` in
   `crates/publet-store/tests/store.rs`, and through `pub-serve` by
   `signed_sync.feature`.
6. **Section 9.3, the versioned interface, for the plumbing commands.**
   Carried forward from 0.4.0, finding 7.
7. **Section 4.1, entry points without a fuzz target.**
   `publet_net::wire::unpack` and `ProseClaim::from_object` are carried
   forward from 0.4.0, finding 8. The new code reads two things from outside.
   `restore` reads the committed key object with `Object::parse`, which is
   fuzzed, and checks it against `--expect` with `verify`. The signature index
   reads stored objects with `Object::parse` too. `--expect` is parsed as a
   `Cid` before it names a file, so it cannot name a path outside `objects/`.
8. **Section 7, `SECURITY.md`.** Its list of fuzzed parts
   (`SECURITY.md:64-67`) does not name the new `defines_parse` target. What it
   says is still true, but it is incomplete.

## Worth considering

9. **Section 3.2, property tests.** proptest is not a dev-dependency of
   publet-cli. Carried forward from 0.4.0, finding 13.
10. **Opening an old store now writes to it.** The first `Store::open` after
    upgrading builds the signature index in one write transaction over every
    object held. On a large store that first open is slower, and it needs write
    access. Later opens only read the `meta` flag.
11. **The 0.4.0 finding about `pub-serve`'s scan (finding 9) is resolved.**
    Each delta now does one range read per record sent.
12. **Carried forward from 0.4.0, unchanged:** findings 5, 10, 11 and 12; and
    from 0.3.0 by way of 0.4.0's finding 14, the 4 KiB split, exit codes for
    usage errors, semicolons joining two ideas (42 places, by the machine's
    count), a load that fails whole on an unreadable object, the load warning
    printed by a library, and parsing cost at the 1 MiB limit.

## Sections met

- **Section 3.1, test vectors:** publet-cli has none of its own. The
  repository's vectors come from their independent sources, and `make
  vectors-check` passes.
- **Section 3.3, oracles:** the signatures in the scenarios are made by
  `tests/support/signing.py` with the `cryptography` package's Ed25519, which
  is independent of publet's code. `sign.feature` checks that a restored key
  signs again.
- **Sections 3.4 and 9.7, `// covers:` comments:** optional for a binary.
  `porcelain/` has none. The two new store tests were read, and each exercises
  what its name says.
- **Section 5.5, README:** as 0.4.0 found. `README.md:437-445` now says how a
  backed-up secret is restored, and what `--expect` checks.
- **Section 9.1, documentation:** the README and `sign.rs`'s module docs
  describe `--restore-key` and `--expect`. Finding 4 says what `--help` lacks.
- **Section 9.2, module docs:** `porcelain/src/sign.rs` opens with `//!` docs
  that now say what `--restore-key` does and why. `restore`, `key_object`,
  `Store::signatures_of`, `signed` and `signature_key` each have docs.
  `cargo clippy -W clippy::missing_docs_in_private_items` finds nothing.
- **Section 9.3, the versioned interface:** `pub sign` gains `--restore-key`
  and `--expect=CID`, recorded as `added`. Nothing that existed changes:
  `--generate-key` and `--rotate` behave as before, and the error naming both
  now names all three. `pub-serve` sends the same delta, faster, recorded as
  `fixed`.
- **Section 9.8, related tools:** none named, as finding 3 says.
- **Section 10.1, writing:** the new docs and messages are plain and
  specific. They say what was refused and that nothing was changed. The
  semicolons the machine counts are carried in finding 12.
- **Not applicable to a command-line tool (binary only):** sections 1.1 to
  1.9, 2.1 to 2.7 and 5.4.

## Claims verified

- `pubrel next --package publet-cli` gives 0.4.1.
- `cargo test --locked -p publet-cli -p publet-store`: 46 and 21 tests pass,
  with 1 ignored.
- `make vectors-check`, `make supply-chain-check`, `make deny` and `make vet`
  pass, run by `pubrules audit prepare` at `59588fd`.

## Checks run

| Check | Result |
|---|---|
| `cargo doc -p publet-cli --no-deps` | pass |
| `cargo clippy -p publet-cli --all-targets` | pass |
| `cargo clippy -p publet-cli -- -W clippy::missing_docs_in_private_items` | 0 undocumented private item(s) |
| `pub --help` | exit 2 |
| `cargo publish --dry-run --locked -p publet-cli` (with --allow-dirty: the tree has uncommitted changes) | fails |
| `cargo +1.98 check --locked -p publet-cli` (MSRV) | pass |
| `make vectors-check` (whole repository) | pass |
| `make supply-chain-check` (whole repository) | pass |
| `make deny` (whole repository) | pass |
| `make vet` (whole repository) | pass |

## Checks not run

- `make fuzz-smoke` and `make functional`: CI runs them on the release pull
  request.
- `cargo test --doc` and the docs.rs build: publet-cli has no library target.
