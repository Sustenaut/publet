---
package: publet-core
version: 0.2.0
standard: bc3c5b6eeba4757b5d96bc00be2d0a1d3221bef89072b06a271c2b28e2205e34
blocking: 0
date: 2026-11-02
auditor: rust-crate-quality
commit: 3a824afea25293ebe33bdd0b008eddbc81c1b880
last-release: publet-core-v0.1.4
---

# Quality audit: publet-core 0.2.0

The only change to the crate's code since publet-core-v0.1.4 is one constant:
`cbor::MAX_OBJECT_BYTES` goes from 65,536 to 1,048,576 bytes (publet #93). The
rest of the diff is a repository URL in the crate docs and the README, two tests,
and the generated `SUPPLY-CHAIN.md` and `TESTING.md`. So the rules that need
judgement were judged by reading that diff, and by relying on the 0.1.4 audit
for anything it does not touch. The Related crates claims were not run again.

The auditor wrote #93, so its review of that change is not independent.

The version is 0.2.0 because #93 records the limit as `changed`. It is part of
the interface: an object between the two limits is refused by 0.1.4 and accepted
by this release.

## Blocks a release

None.

## Falls short of the standard

None.

## Worth considering

1. **Section 4, parsing cost at the new limit.** `cbor::decode` builds a tree of
   `Value`s before anything else checks the object. An array of one-byte items
   grows by roughly the size of `Value` per byte, so a hostile 1 MiB object could
   take about 30 MB to decode, where a 64 KiB one took about 2 MB. This estimate
   was reasoned, not measured. The limit is still a fixed bound, and the owner
   chose this size knowing it.
2. **Section 4, fuzzing near the limit.** The fuzz targets set no input length,
   so they are unlikely to reach objects near 1 MiB. The check at the limit is a
   single comparison, tested on both sides, so this matters little.
3. **Section 2, `Cid::from_digest`'s example (`src/cid.rs:150`) unwraps.** It
   returns an `Option`, and `?` would need `.ok_or(...)`, so the unwrap may be the
   clearer choice. Unchanged since 0.1.4.
4. **Section 10, writing.** Semicolons join two ideas at `src/cid.rs:113` and
   `src/lib.rs:122`. Unchanged since 0.1.4, which noted the second.
5. **Carried forward from 0.1.4, unchanged:** which Ed25519 acceptance rule
   `verify` applies (its finding 7), and the hand-encoded `testdata/canonical.json`
   (its finding 8). Whether `SECURITY.md:65`'s "on every change" (its finding 9)
   is exact was not looked at again.
6. **Outside this crate, but relevant to `verify`.** A search found signatures
   verified by `pub render`, key rotation and `pub-sign` only. The spec has no
   requirement to verify one. A spec and code change is planned after this
   release.

## Sections met

- **The machine's §1.6 findings were wrong.** It said the `minicbor` and
  `serde_cbor` rows give no version and the `ciborium` row says 4.1. Read at
  `src/lib.rs:149-153`, the rows name 0.2.2, 2.3.0, 0.25.2, 0.11.2 and 0.11.3.
  `Cargo.lock` has ciborium 0.2.2.
- **Section 1, crate documentation:** unchanged since 0.1.4, apart from the URL.
  The docs state no size limit in words beyond naming Section 4.5, so nothing went
  stale.
- **Section 2, items:** hidden setup, `# Errors`, `# Panics` and domain sections are
  unchanged since 0.1.4. `decode_with_limit`'s and `MAX_OBJECT_BYTES`'s `usize` is a
  local limit on this machine's memory, as 0.1.4 judged. On a 32-bit target 1 MiB
  still fits.
- **Section 3, tests:** the vector sources and the `ciborium` oracle are unchanged.
  `tests/canonical.rs`'s new test covers acceptance at exactly 1,048,576 bytes, and
  `rejects_oversized_input` refusal at 1,048,577. Their `// covers:` claims were read
  and hold.
- **Section 4, untrusted input:** targets exist for CBOR decoding, object parsing,
  identifier parsing and signature checking. `decode_with_limit` is reached through
  `decode`. `verifying_key` is reached through `signature_verify` only if that
  target calls it, which this audit did not check, and nothing here changes it.
- **Section 5, packaging:** the README names no size limit, and its sections are as
  0.1.4 found.
- **Section 7, `SECURITY.md`:** unchanged since 0.1.4, as the diff shows.
- **Not applicable to a library:** section 9.

## Claims verified

- `git diff publet-core-v0.1.4 HEAD -- crates/publet-core/src` is the constant and
  the URL.
- `cbor::decode` accepts a canonical byte string of exactly 1,048,576 bytes, and
  refuses 1,048,577 bytes with the rule "object size limit".
- `Cargo.lock` has ciborium 0.2.2.

## Checks run

| Check | Result |
|---|---|
| `cargo doc -p publet-core --no-deps` | pass, by `pubkit audit prepare` |
| `cargo clippy -p publet-core --all-targets` | pass, by `pubkit audit prepare` |
| `cargo test -p publet-core` | pass, 94 tests |
| `cargo test --doc -p publet-core` | pass, 53 doctests |
| docs.rs build of the packaged crate on nightly, with docs.rs's flags | pass, no warnings, by `pubkit audit prepare` |
| `cargo publish --dry-run --locked -p publet-core` | pass, by `pubkit audit prepare` |
| `cargo +1.85 check --locked -p publet-core` (MSRV) | pass, by `pubkit audit prepare` |
| `make doc-coverage-check`, `make vectors-check`, `make supply-chain-check`, `make deny`, `make vet` | pass, by `pubkit audit prepare` |

## Checks not run

- `make fuzz-smoke` and `make functional` by this report: CI runs them on the release
  pull request.
- The Related crates claims, which the 0.1.4 audit ran. The versions named have not
  changed.
