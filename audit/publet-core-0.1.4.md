---
package: publet-core
version: 0.1.4
standard: bc3c5b6eeba4757b5d96bc00be2d0a1d3221bef89072b06a271c2b28e2205e34
blocking: 1
date: 2026-10-28
auditor: Claude Code, following the rust-crate-quality agent (pubkit 0.14.0)
---

# Audit: publet-core 0.1.4

This report was produced in a Claude Code session by following the
rust-crate-quality agent's definition and the Rust crate standard exactly as
pubkit v0.14.0 ships them (`plugins/rust-crate-quality/`). The agent itself was
not installed on the machine. The audit covers `main` at `f2071fc`, which is
publet-core 0.1.3 plus the move to ed25519-dalek 3 and sha2 0.11 (#61). The
version to release is 0.1.4 (`pubrel next --package publet-core`). Nothing was
edited except this file, which should be committed with the release's changes.

## Blocks a release

1. **Section 7 (`SECURITY.md`, judged): a false claim.**
   `crates/publet-core/SECURITY.md:86`, the same file as the root `SECURITY.md`,
   ships in the package and renders as `_documentation::security`. It says
   "Advisory checks run when the code changes, not on a schedule". But
   `.github/workflows/nightly.yml` runs `cargo deny` and `cargo vet` (`audit`,
   `required: deny vet`) and OSV (`osv`) every day at 03:23 UTC
   (`schedule: [{ cron: '23 3 * * *' }]`). The standard counts a false claim in
   the docs as blocking. The fix is documentation only: drop that bullet from
   "What is not yet done", and say under "What is checked" that the advisory
   checks also run nightly. Because the file changes, `crates/publet-core`
   changes, so record it with `pubrel add --package publet-core internal ...`
   (and for publet-algorithms, whose copy is the same file).

## Falls short of the standard

2. **Section 2, `# Errors` (`src/sig.rs:146`).** `verify` says only "Returns
   [`SigError`] describing which check failed." The standard asks for exactly
   when each error happens. `verify` returns `PurposeMismatch` when the purposes
   differ (checked first, before any cryptography), `PurposeContainsNul`,
   `MalformedKey` (not 32 bytes, or not a valid point), `MalformedSignature`
   (not 64 bytes) and `BadSignature`. It never returns `UnknownAlgorithm` or
   `MalformedSecretKey`.
3. **Section 2, hidden setup (`src/sig.rs:153`).** In `verify`'s example,
   `seed` comes from a hidden line (`# let seed = [7u8; 32];`), so a reader
   can't tell where the visible `&seed` comes from. The crate root's example
   shows the same line visibly.
4. **Section 1.6, Related crates (`src/lib.rs:153`).** The `cid` row gives no
   version checked. It is at 0.11.3 on crates.io today.
5. **Section 7, `SECURITY.md:36-39`.** It lists the audit sets imported as
   "Mozilla, Google, the Bytecode Alliance, Zcash, ISRG or Embark Studios", but
   `supply-chain/config.toml` also imports `pubunit`. That set covers none of
   publet-core's own dependencies, but the sentence describes the repository's
   `cargo vet`.

## Worth considering

6. **Section 10, writing (`src/lib.rs:122-125`).** "General-purpose decoders
   accept them all; `ciborium` and `minicbor` both decode ..." carries two
   ideas across a semicolon. The paragraph's next sentence starts on the same
   overlong source line as the end of this one.
7. **Section 2 (`src/sig.rs`, `verify`).** The docs don't say which Ed25519
   acceptance rule applies. It is ed25519-dalek's `Verifier::verify`
   (cofactorless check, as RFC 8032 allows), not `VerifyingKey::verify_strict`,
   which also rejects small-order public keys and `R` values (the group-element
   malleability check, per ed25519-dalek 3.0.0's docs). For a protocol whose signatures are evidence, this is
   worth one sentence, or a decision to use `verify_strict`. That decision is
   a code change for a person to make.
8. **Section 3, test vectors (`testdata/canonical.json`).** Its source is
   "Hand-encoded from the specification", by this project. That is less
   independent than the RFC 8032 and Python-generated vectors. The `ciborium`
   property tests partly compensate. A second encoder (for example, Python
   `cbor2` in canonical mode, with Section 4.1's key order) would make it
   independent.
9. **Section 7, `SECURITY.md:60`.** "fuzzed on every change": the CI skips
   fuzzing on a pull request that touches no Rust code, Cargo files, `fuzz/` or
   workflow files (RS-FUZZ-02). "on every change to the code" would be exact.
10. **Section 1.6.** minicbor 2.3.1 is out. The row says 2.3.0, which is the
    version checked, so this is not wrong.

## Sections met

- **1, crate documentation:** every part is there and in order, with a
  `_documentation` module. The "Related crates" claims were re-checked (below).
- **2, items:** `deny(missing_docs)` and `warn(missing_debug_implementations)`
  are set. Every public error enum is `#[non_exhaustive]`. The only `usize`
  public items are local limits (`MAX_OBJECT_BYTES`, `DEFAULT_MAX_DEPTH`).
- **3, tests:** RFC 8032 and independent-implementation vectors, proptest
  round-trips, and a ciborium oracle. The `// covers:` claims spot-checked in
  `tests/vectors.rs` and `tests/canonical.rs` match what the tests exercise.
- **4, untrusted input:** fuzz targets exist for CBOR decoding, object
  parsing, identifier parsing and signature checking. The crate forbids
  `unsafe` (workspace `unsafe_code = "forbid"`).
- **5, packaging:** the metadata is complete, `include` is anchored, and
  `cargo package --list` ships only the intended files. The README has
  Documentation, Usage, Example, Minimum Rust version and Security.
- **6, versions:** the MSRV policy is stated. `release.json` has
  `"semver-checks": true`. `pubrel check` on #61 found nothing beyond a patch.
- **8, cross-platform:** the `cross` job runs in CI and nightly.

## Claims verified

- `ciborium` 0.2.2: decoding with `ciborium::de::from_reader` into `Value`
  accepted a two-byte `5`, indefinite-length text, unsorted keys, duplicate
  keys, an integer key, a half float and a tag. It read `0x18 0x05` as
  `Integer(5)`.
- `minicbor` 2.3.0: `Decoder::skip` accepted the same seven inputs.
- `dcbor` 0.25.2: it rejected the padded integer, indefinite length, unsorted
  and duplicate keys, and `{"aa":1,"b":2}` (sorted by bytes, as Section 4.1
  requires). It accepted an integer key, a tag, and the float 1.5. So "rejects
  this crate's canonical objects" and "admits floats, tags and non-text keys"
  both hold.
- `serde_cbor` 0.11.2 is unmaintained: RUSTSEC-2021-0127.
- The `cid` row is checked against the crate's documented text form, not by
  running it.

## Checks run

| Check | Result |
|---|---|
| `make doc` | pass |
| `make lint` | pass |
| `make msrv` (Rust 1.85) | pass |
| `make publish-check` | pass |
| `make doc-coverage-check` | pass |
| `make supply-chain-check` | pass |
| `make vectors-check` | pass |
| `cargo test --doc -p publet-core` | pass (53 doctests) |
| docs.rs build: `cargo package --no-verify`, unpacked, `cargo +nightly doc --no-deps --all-features` with `--cfg docsrs -Z unstable-options --generate-link-to-definition -D warnings` | pass, no warnings |

Not run: `make fuzz-smoke`. The agent's list doesn't include it, and CI runs it
on the release pull request.
