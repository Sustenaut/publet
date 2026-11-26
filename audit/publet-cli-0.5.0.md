---
package: publet-cli
version: 0.5.0
standard: 45390b67d5e4cbf27491f4de7ea4a2ca013482e4ebc474978fd5a1d49c65e163
blocking: 0
date: 2026-11-26
auditor: rust-crate-quality
commit: e6addf949b68949f088137ecb2ba43879d53e371
last-release: v0.4.1
---

# Quality audit: publet-cli 0.5.0

This report audits publet-cli against the Rust crate standard named above.
publet-cli is a command-line tool (binary only), so section 9 applies. It is
installed from git, or as the static `pub` attached to each release, and is
not on crates.io, so this release has no `cargo publish`. The changes since
v0.4.1 that reach users:

- #127 dates the keys and signatures pub makes when it makes them:
  `pub sign --generate-key`, `--rotate` and `--target`, and the
  signatures `pub build --sign` and `pub publish` make, take `created` from
  `sign::created()` (`$PUB_CREATED`, else the current UTC time to the
  second) instead of a fixed 2026-09 instant. `pub sign --restore-key`
  without a committed key object now needs `--created`.
- #130 moves `url` to 2.5.9 for RUSTSEC-2026-0592 (and `form_urlencoded`
  to 1.2.3 with it).

They are recorded as one `changed` row and one `security` row, which below
1.0 gives 0.5.0 (`pubrel next --package publet-cli`).

The auditor wrote #127 and #130, so its review of them is not independent.
A second reader of `porcelain/src/sign.rs`'s `created()` and `restore` would
add something this report cannot.

## Blocks a release

None. The machine's blocking finding is reclassified as finding 1, as in the
0.2.2 to 0.4.1 audits.

## Falls short of the standard

1. **RS-PKG-01, packaging (reclassified from "Blocks a release").** `cargo
   publish --dry-run --locked -p publet-cli` fails, because publet-cli depends
   by path on crates that are not on crates.io. It is never published there,
   so this cannot break a publish. Carried forward from 0.4.1, finding 1,
   including the decision it asks of a person: `publish = false` with an
   exception in `pubrules.json`, or publishing the workspace crates.
2. **Section 5.1 and section 9, metadata (`porcelain/Cargo.toml`).** No
   `documentation`, `keywords`, `categories` or `include`. Carried forward
   from 0.4.1, finding 2.
3. **Section 9.1, README: "Why this tool", "Related tools", installation and
   Minimum Rust version.** Carried forward from 0.4.1, finding 3.
4. **Section 9.5, usage text.** `pub --help` prints to stderr and exits 2.
   The README's command list names `--restore-key`'s new `--created`.
   Carried forward from 0.4.1, finding 4.
5. **Section 9.4, end-to-end tests.** No scenario runs `pub sync`, `pub
   witness`, `pub document` or `pub --help`. Carried forward from 0.4.1,
   finding 5. The new behaviour is covered:
   `tests/features/porcelain/created.feature` has four scenarios (an
   unpinned key and signature are dated now, `$PUB_CREATED` pins a key,
   `--created` beats it); `build.feature` shows a second `pub build --sign`
   of unchanged sources signs nothing and stores nothing, with the date
   unpinned; `sign.feature` refuses `--restore-key` without `--created` and
   names the old default. The suite pins `PUB_CREATED`, so every other
   scenario keeps its identifiers.
6. **Section 9.3, the versioned interface, for the plumbing commands.**
   Carried forward from 0.4.1, finding 6.
7. **Section 4.1, entry points without a fuzz target.**
   `publet_net::wire::unpack` and `ProseClaim::from_object` are carried
   forward from 0.4.1, finding 7. The new code reads one thing from outside,
   `$PUB_CREATED`, which it passes to the object builder as `created`, as it
   already did `--created`; the builder checks it.
8. **Section 7, `SECURITY.md`.** Its list of fuzzed parts does not name the
   `defines_parse` target. Carried forward from 0.4.1, finding 8.

## Worth considering

9. **Section 3.2, property tests.** proptest is not a dev-dependency of
   publet-cli. Carried forward from 0.4.1, finding 9.
10. **`created` is still a fixed instant in the commands that author
    content** (`compose`, `annotate`, `relate`, `revise`, `document`,
    `policy`, `domain`) and in `pub build`'s fallback for undated sources.
    #127 left them on purpose, since dating build's content now would give
    every rebuild new identifiers. Sustenaut/publet#128 tracks moving them.
11. **Exemptions, not audits, cover the new `url` and `form_urlencoded`.**
    No imported audit covers `url` 2.5.9 or `form_urlencoded` 1.2.3 yet; their
    cargo-vet exemptions carry dated notes. `cargo vet regenerate imports`
    should replace them once one does.
12. **Carried forward from 0.4.1, unchanged:** findings 10 to 12.

## Sections met

- **Section 3.1, test vectors:** publet-cli has none of its own. `make
  vectors-check` passes.
- **Section 3.3, oracles:** as 0.4.1 found.
- **Sections 3.4 and 9.7, `// covers:` comments:** optional for a binary.
  The new scenarios were read, and each exercises what its name says.
- **Section 5.5, README:** the README now says how pub dates keys and
  signatures, what `PUB_CREATED` and `--created` do, that a rebuild signs
  nothing new, and what `--restore-key` needs for a key made by pub 0.4.1 or
  earlier.
- **Section 7, supply chain:** `cargo deny` passes again with `url` 2.5.9;
  `cargo vet` passes; SUPPLY-CHAIN.md is current.
- **Section 9.2, module docs:** `sign.rs`'s module docs say `--created` has
  no default for `--restore-key` and why; `created()`, `CREATED_VAR` and
  `LEGACY_CREATED` each have docs.
- **Section 9.3, the versioned interface:** keys and signatures carry a
  different `created`, and `--restore-key` without a committed key object
  needs `--created`: recorded as `changed`. The new `PUB_CREATED` is
  documented in the README.
- **Not applicable to a command-line tool (binary only):** sections 1.1 to
  1.9, 2.1 to 2.7 and 5.4.

## Claims verified

- `pubrel next --package publet-cli` gives 0.5.0.
- `make functional` passed 559 scenarios on #127's branch, and CI's
  functional job passed on #127's head.
- `cargo deny`, `cargo vet`, `make supply-chain-check` and `cargo test
  --workspace` pass with `url` 2.5.9.

## Checks run

| Check | Result |
|---|---|
| `cargo doc -p publet-cli --no-deps` | pass |
| `cargo clippy -p publet-cli --all-targets` | pass |
| `cargo clippy -p publet-cli -- -W clippy::missing_docs_in_private_items` | 0 undocumented private item(s) |
| `pub --help` | exit 2 |
| `cargo publish --dry-run --locked -p publet-cli` | fails |
| `cargo +1.98 check --locked -p publet-cli` (MSRV) | pass |
| `make vectors-check` (whole repository) | pass |
| `make supply-chain-check` (whole repository) | pass |
| `make deny` (whole repository) | pass |
| `make vet` (whole repository) | pass |

## Checks not run

- `make fuzz-smoke`: CI runs it on the release pull request.
- `cargo test --doc` and the docs.rs build: publet-cli has no library target.
