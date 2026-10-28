---
package: publet-algorithms
version: 0.2.2
standard: bc3c5b6eeba4757b5d96bc00be2d0a1d3221bef89072b06a271c2b28e2205e34
blocking: 0
date: 2026-10-28
auditor: rust-crate-quality
---

# Audit: publet-algorithms 0.2.2

This report was produced by the rust-crate-quality agent, against the Rust
crate standard as pubkit 0.14.6 ships it (`pubkit audit --standard` prints
the hash in the header above). The audit covers `f60d996` (origin/main of
schryer/publet, on branch `claude/release-cli`). That is publet-algorithms
0.2.1 plus the `h3` module and the move to sha2 0.11. It also covers the
documentation fixes listed under "Resolved on this branch". The version to
release is 0.2.2 (`pubrel next --package publet-algorithms`). This file
should be committed with the release's changes.

## Blocks a release

None. Every check passes. The docs build as docs.rs builds them, with no
warnings. Every public function has an example (`make doc-coverage-check`).
No claim in the docs was found false.

## Falls short of the standard

None of these can be fixed in the documentation alone. Each needs a code
decision from a person.

1. **Section 2, `# Panics` (`src/fixed.rs:253`, `Fixed6::halve_fractional`).**
   `value * frac` is a plain `i128` multiplication. `mul_div`, `times` and
   `ratio` saturate instead. For a large value and a large remainder it
   overflows. Where overflow is checked, it panics: in debug builds, and in
   publet's release builds (`overflow-checks = true`). Elsewhere it wraps.
   `Fixed6::from_scaled(i128::MAX / 2).halve_fractional(u64::MAX - 1, u64::MAX)`
   panics in a debug build. In a release build without overflow checks it
   returns a wrapped value. `propagate` reaches it through
   `decay_half_life_days`. The docs say nothing about it. Documenting it
   would make a result that depends on the build profile part of the
   contract. A saturating or checked multiplication would remove the
   panic, so no `# Panics` section would be needed.
2. **Section 2, error types (`src/graph.rs:100`, `CycleThroughStart`).** A
   public unit struct, neither `#[non_exhaustive]` nor an opaque struct
   with a `kind()`. Making it `#[non_exhaustive]` stops callers from
   constructing it, which `closure`'s own example does
   (`Err(CycleThroughStart)`). So the change is breaking, for a 0.3.0
   release.
3. **Section 4, fuzz targets.** `fuzz/fuzz_targets/log_verify.rs` covers
   `log::verify_inclusion` and `log::verify_consistency`. Two other entry
   points that read input from outside have no target:
   - `h3::Cell`'s `FromStr` and `Cell::from_bits`
     (`src/h3.rs:231`, `src/h3.rs:100`). They parse text that comes from
     objects (a singular's location) and from `pub get` path segments
     (`porcelain/src/get.rs:57`).
   - `membership::verify` (`src/membership.rs:227`). It checks proofs
     that come from someone else (`crates/publet-net/src/server.rs`,
     `bin/pub-proof`). It calls `verify_inclusion`, which is fuzzed. Its
     own absence logic is not.

## Resolved on this branch

The first pass of this audit, on `f60d996`, found the findings below. The
fixes are documentation only: doc comments in `src/`. No code, test or
`Cargo.toml` changed. `TESTING.md` was regenerated (`make doc-coverage`) and
did not change. The change should be recorded with `pubrel add` for
publet-algorithms, as `internal`.

1. **Section 2, hidden setup.** Hidden `# let` lines defined names used
   in visible examples:
   - `leaves`, in four examples in `src/log.rs`: `inclusion_proof`,
     `verify_inclusion`, `consistency_proof` and `verify_consistency`;
   - `members`, in five examples in `src/membership.rs`;
   - `edges` and `next`, in three examples in `src/graph.rs`: `reachable`,
     `reaches` and `closure`.

   Each of those lines is now visible.
2. **Section 2, `# Panics` (`src/fixed.rs`, `Fixed6::mul_div` and
   `Fixed6::ratio`).** Both panic in every build profile when the
   saturated product is `i128::MIN` and the divisor is
   `Fixed6::from_scaled(-1)`. The quotient does not fit in `i128`. Each
   now has a `# Panics` section giving the exact condition. The boundary
   was checked by running it:
   - `ratio` panics at `i128::MIN / SCALE - 1` and not at
     `i128::MIN / SCALE`;
   - `mul_div` panics for a product of exactly `i128::MIN`, and not for
     one 2 above it.

   `mul_div`, `times` and `ratio` now also say that the product
   saturates. `halve_fractional` now says it returns `self` unchanged
   when `denominator` is 0.
3. **Section 2, `# Panics` (`src/propagate.rs`, `propagate` and
   `propagate_within`).** Both normalize weights with `mul_div`. Crafted
   negative weights reach its panic: seed weights, or one node's edge
   weights, summing to `Fixed6::from_scaled(-1)`. Both cases were run, and
   both panic. Both functions now have a `# Panics` section.
4. **Section 2, `# Complexity`.** No traversal or proof had one. These
   now have one, each checked against the code:
   - `log`: `root`, `inclusion_proof`, `verify_inclusion`,
     `consistency_proof`, `verify_consistency`;
   - `membership`: `Membership::root`, `Membership::prove`, `verify`;
   - `graph`: `reachable`, `reaches`, `closure`, `root`,
     `topological_order`;
   - `propagate`: `propagate`, `propagate_within`, `reachable_within`;
   - `tree`: `Node::hash`.

   Where it matters, they say how cost is bounded on input from a peer.
   For example, `verify_inclusion` checks the path's length against
   `size` before any hashing, so it does at most 64 node hashes.
   `topological_order`'s now says its recursion depth grows with the
   longest dependency chain.
5. **Section 2, `# Errors`.** Each is now worded as a promise ("Fails
   only if ..."):
   - `graph::closure`: says which cycles are an error and which are not;
   - `graph::topological_order`: says which cycle is reported, the first
     one the depth-first walk meets;
   - `h3::Cell::from_bits`.
6. **Section 2, examples use `?` (`src/h3.rs`).** The module example and
   five method examples parsed cells with `.parse().unwrap()`. They now
   use `?`, with `# Ok::<(), Box<dyn std::error::Error>>(())` hidden.
7. **Section 2, empty results (`src/log.rs`).** `inclusion_proof` and
   `consistency_proof` return an empty proof for some arguments, without
   saying so. `inclusion_proof` does for an index out of range.
   `consistency_proof` does for `m` of 0, equal to the size, or above it.
   Both now say so. `verify_consistency` said the round-trip tests
   exercise "every `(m, n)` pair". It now says `n` goes up to 48, as
   `tests/log.rs` does.
8. **Section 10, writing.** Sentences carrying two ideas across a
   semicolon were split:
   - `src/lib.rs`: lines 8, 109 and 141, and the `semver` row;
   - `src/graph.rs`, `src/h3.rs`, `src/fixed.rs`, `src/tree.rs`,
     `src/propagate.rs` and `src/version.rs`.

   "would simply always fail" in `src/log.rs` lost the "simply". The
   crate root's Minimum Rust version section now names `make msrv`.

## Worth considering

9. **Section 3, independence of test vectors.**
   - `testdata/fixed.json` and `testdata/versions.json` are generated by
     this project's own `tools/vectors/generate.py`. That is less
     independent than `log.json` (the Certificate Transparency project's
     roots) and `h3.json` (h3-py 4.5.0).
   - For `version::satisfies`, the `semver` crate's `VersionReq` could
     serve as an oracle for the caret form on three-part versions, as a
     dev-dependency.
10. **Section 7, `SECURITY.md:65`.** It says "fuzzed on every change". CI
    skips fuzzing on a pull request that touches no Rust code, Cargo
    files, `fuzz/` or workflow files (RS-FUZZ-02), so "on every change to
    the code" would be exact. The publet-core 0.1.4 audit reported the
    same sentence. The file is byte-identical to the repository's
    `SECURITY.md` and publet-core's, so it was left alone here. It should
    change in all three at once.
11. **Section 2, stack depth.** `graph::topological_order` (its inner
    `visit`) and `tree::Node::hash` recurse. A long enough dependency chain
    or a deep enough tree exhausts the stack and aborts the process, which
    is not a panic. The `# Complexity` sections now say so. Whether to
    bound the depth or iterate instead is a code decision.
12. **`src/propagate.rs:285`, `reachable_within`.** It runs all `distance`
    rounds even after the frontier is empty, so `u32::MAX` loops about
    4×10⁹ times for nothing. Its `# Complexity` now says it runs every
    round. Stopping on an empty frontier would change no result.
13. **Section 5, `Cargo.toml` `description`.** It lists every module except
    `graph` and `version`. The README and crate root list all eight.

## Sections met

- **1, crate documentation:** every part is there and in order:
  - one sentence on what the crate is for, then a runnable example;
  - an overview table of the eight modules, and the invariant they keep:
    a fixed order;
  - a map of the page, and a cookbook of three `## Example:` blocks;
  - Why this crate, Related crates, Crate features ("None"), Minimum Rust
    version with the policy, and Versioning.

  The `_documentation` module wires `testing`, `supply_chain`, `security`
  and `changelog`.
- **2, items:** `deny(missing_docs)` and
  `warn(missing_debug_implementations)` are set. `CellError` and
  `membership::Proof` are `#[non_exhaustive]`. `tree::Node` says why it is
  exhaustive. Sizes and indexes that come with a peer's proof are `u64`
  (`verify_inclusion`, `verify_consistency`, `Proof`). Only proof
  construction over leaves in memory takes `usize`.
- **3, tests:** the vectors come from independent sources (CT roots,
  h3-py), with proptest properties for graphs and logs, and `ct-merkle`
  as an oracle (dev-dependency). The `// covers:` claims spot-checked
  match what the tests exercise:
  - `tests/oracles.rs` (`root`, `inclusion_proof`, `consistency_proof`
    against `ct-merkle`);
  - `tests/graph.rs` (`topological_order`, `closure`, `reachable`,
    `reaches`);
  - `tests/propagate.rs:157` (`reachable_within`);
  - `tests/membership.rs:112-154`.
- **4, untrusted input:** the Merkle log verifiers are fuzzed, with two
  kept regressions (`fuzz/regressions/log_verify/`). The workspace sets
  `unsafe_code = "forbid"`. See finding 3 for the gaps.
- **5, packaging:**
  - the metadata is complete, `include` is anchored, and
    `[package.metadata.docs.rs]` has `all-features` and
    `--generate-link-to-definition`;
  - `cargo package --list` ships only `src/`, `tests/`, `testdata/`, the
    licence and the six Markdown files;
  - `make publish-check` uses `CARGO_TARGET_DIR=target/publish-check`
    and `--locked`;
  - the README has Documentation (saying what the docs cover), Usage, one
    example, Minimum Rust version and Security.
- **6, versions:** `release.json` has `"semver-checks": true` for
  publet-algorithms. The MSRV is 1.85 and `make msrv` builds it there.
  The policy (it rises only with the second number) is stated in the
  README and the crate root.
- **7, security:** `SECURITY.md` says how to report privately, what is
  checked on every pull request, nightly and in every release, and the
  four bugs fuzzing found. It matches `CHANGELOG.md`'s 0.2.0 Security
  entry. The supported-version table names the `publet-algorithms-vX.Y.Z`
  tags, which exist (`publet-algorithms-v0.1.0` to `v0.2.1`).
- **8, cross-platform:** the log's absurd-size regression tests build and
  run on 32-bit targets (CHANGELOG 0.2.0). The `cross` job is pubkit's.

## Claims verified

Building crates downloaded from crates.io was not permitted in this
session. So each behaviour claim in the "Related crates" table was checked
against the crate's published source, from the local cargo registry,
rather than by running it. Every version in the table was checked with
`cargo info`, and each is the newest on crates.io.

- `ct-merkle` 0.3.0: an RFC 6962 tree type (`MemoryBackedTree`). The
  `tests/oracles.rs` proptests compare roots, audit paths and consistency
  proofs with it byte for byte, and pass.
- `rs_merkle` 1.5.0: `Hasher::concat_and_hash` hashes `left || right` with
  no `0x01` prefix, and carries an odd node up unhashed. So its roots
  differ from RFC 6962's.
- `petgraph` 0.8.3: `page_rank` is generic over `UnitMeasure`, which is
  implemented only for `f32` and `f64`.
- `pathfinding` 4.16.0: `topological_sort` returns `Result<Vec<N>, N>`,
  and its docs say the error is "an arbitrary node involved in a cycle".
- `rust_decimal` 1.43.0: division rounds the last digit
  (`src/ops/div.rs`), where `Fixed6` truncates.
- `h3o` 0.11.0: `LatLng` holds `f64` coordinates, which `to_cell` takes.
- `h3ron` 0.18.0: it depends on `h3ron-h3-sys`, the C library's bindings,
  and its source uses `unsafe`.
- `semver` 1.0.28: `Version`'s parser requires a dot after the minor
  number, so `0.15` is not a version.
- The `h3` module's Tallinn example: `make vectors-check` regenerates
  `testdata/h3.json` from h3-py 4.5.0's `latlng_to_cell(59.437, 24.7536, 10)`.
  That gives `8a089b1a2177fff`, with the resolution-5 and resolution-7
  parents the examples use. The committed copy matched.
- `membership::verify`'s claim that adjacency by index proves absence: the
  proof's `size` is not bound to the root. This was checked by brute force
  over RFC 6962 tree shapes, for every set of up to 69 members and every
  claimed size up to 4n + 3. No claimed size lets two leaves that are not
  adjacent verify at adjacent indexes. Domain separation fixes every leaf's
  depth.

## Checks run

All were run on `f60d996`, and all passed. After the documentation fixes,
every check was run again except `make msrv`, `make publish-check`,
`make supply-chain-check` and `make vectors-check`. No code, dependency or
test vector changed. Those runs also passed.

| Check | Result |
|---|---|
| `make doc` | pass |
| `make lint` | pass |
| `make msrv` (Rust 1.85) | pass |
| `make publish-check` | pass |
| `make doc-coverage-check` | pass (`TESTING.md` current) |
| `make supply-chain-check` | pass |
| `make vectors-check` | pass (regenerated, no diff) |
| `make fmt-check` | pass |
| `cargo test --doc -p publet-algorithms` | pass (58 doctests) |
| docs.rs build: `cargo package --no-verify`, unpacked outside the repository, `cargo +nightly doc --no-deps --all-features` with `--cfg docsrs -Z unstable-options --generate-link-to-definition -D warnings` | pass, no warnings |

Not run:
- `make fuzz-smoke`. The agent's list doesn't include it, and CI runs it
  on the release pull request.
- Running the related crates. As above, building crates downloaded from
  crates.io was not permitted, so their claims were checked from source.
