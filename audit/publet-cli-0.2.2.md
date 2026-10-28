---
package: publet-cli
version: 0.2.2
standard: bc3c5b6eeba4757b5d96bc00be2d0a1d3221bef89072b06a271c2b28e2205e34
blocking: 0
date: 2026-10-28
auditor: rust-crate-quality
---

# Audit: publet-cli 0.2.2

This report audits publet-cli against the Rust crate standard that pubkit
0.14.6 ships (`pubkit audit --standard` above). The tree is `main` at
`f60d996`, with the documentation fixes listed under "Resolved on this
branch". The version to release is 0.2.2 (`pubrel next --package
publet-cli`). This file should be committed with the release's changes.

publet-cli is a crate with only a binary target (`pub`, in `porcelain/`), so
section 9 applies. Its release also covers the plumbing commands in `bin/`
and the workspace crates it compiles in (`release.json`, `code`), and this
audit reads those where `pub` depends on them. It is installed from git
(`cargo install --git ... --tag vX.Y.Z publet-cli`) and is not on crates.io.

## Blocks a release

None.

## Falls short of the standard

3. **Section 9, `--help` (`porcelain/src/main.rs:44-74, 113`).** `pub
   --help` prints to stderr and exits 2. The standard asks for stdout and
   exit 0. It names every command, but none of their flags. `pub compose`
   alone takes 21 flags, and no subcommand has its own `--help`. None of the
   26 plumbing commands in `bin/` handles `--help`. The standard asks that
   `--help` name every command and flag. These are code changes.
4. **Section 9, metadata (`porcelain/Cargo.toml`).** It has no
   `documentation` (the standard asks for the README's URL in the
   repository), `keywords`, `categories`, `readme` or `include`. It has no
   `publish = false` either, though it cannot be published.
5. **Sections 6 and 9, RS-PKG-02, RS-VER-02 and RS-SUP-02.** Section 6
   requires `publish-check`, `msrv` and `supply-chain-check` for a
   binary-only crate. All three targets exist and pass, but they cover only
   `PUBLISHED := publet-core publet-algorithms` (`Makefile:63`), not
   publet-cli. So nothing builds `pub` on its `rust-version` of 1.98 (the
   pinned toolchain is 1.98.1). No `SUPPLY-CHAIN.md` describes `pub`'s
   dependency tree, and nothing packages it. Adding publet-cli to
   `PUBLISHED` would make `publish-check` fail: `cargo info` finds no
   publet-graph, publet-store or publet-net on crates.io, and publet-cli
   depends on them by path. The README says so ("from git, until the
   workspace's crates are published on crates.io"). Whether to publish them,
   or to declare an exception in `pubkit.json`, is for a person to decide.
6. **Section 9, README: "Why this tool" and "Related tools".** The README
   explains its design choices one by one. It has no section saying what
   `pub` does that a general-purpose tool would get wrong, and no table of
   related tools with the version or date checked and how. Every row would
   need a check that was run, so none was written here.
7. **Section 9, end-to-end tests.** The functional suite (354 scenarios,
   all passing) never runs `pub sync`, `pub witness`, `pub document`, `pub
   --version` or `pub --help`. This was checked by searching
   `tests/steps`, `tests/support` and `tests/features` for each command.
8. **Section 9, the versioned interface, for the plumbing commands.** The
   README now names it (item 18). The plumbing commands' exit codes are
   not the same across commands: "not found" is 3 in four of them and 1 in
   another. They are listed only as `EXIT_*` constants in each `main.rs`.
9. **Section 4, a missing fuzz target.** `publet_net::wire::unpack` decodes
   bytes from a peer and has no fuzz target (see finding 1). Its
   `Truncated { needed: 4 }` is also wrong when one to three header bytes
   remain. That is a code change.

## Resolved on this branch

1b. **Fell short, resolved by #70: section 9, `pub --version` and the README's claim about it
   (`porcelain/build.rs:28`).** The build script runs `git describe --tags`,
   which takes the nearest tag of any package. In this checkout, `pub
   --version` prints "pub unreleased build (publet-core-v0.1.4-19-gf60d996;
   no release precedes it)", though v0.2.1 precedes it. Two annotated tags
   on one commit were tried in a scratch repository: `git describe --tags`
   gave whichever tag was created last. So if `v0.2.2` and
   `publet-algorithms-v0.2.2` tag the same merge commit, and the second is
   created after the first, a clean build from a clone at `v0.2.2` reports
   itself unreleased. The README says such a build prints `pub 0.2.2`.
   `cargo install --git --tag` is not affected: it has no tags and takes the
   manifest version. A fix is `--match 'v[0-9]*'` in `porcelain/build.rs`.
   That is a code change for a person to make, and it matters to this
   release only if both packages are tagged on one commit.
   #70 adds `--match 'v[0-9]*'` to the build script's `git describe`, so
   only publet-cli's own tags name the version. It merges before this
   release is prepared.

1. **Was blocking: section 7, a false claim in `SECURITY.md` (line 65).** It says "the code
   that reads untrusted input is fuzzed on every change", then lists the CBOR
   decoder, object parsing, identifier parsing, Merkle proof checking and
   signature checking. That is true of publet-core and publet-algorithms. It
   is not true of `pub`. `pub sync` and `pub-sync` decode a peer's response
   with `publet_net::wire::unpack` (`crates/publet-net/src/wire.rs:49`), and
   no target in `fuzz/fuzz_targets/` exercises it. The standard asks that
   `SECURITY.md` say exactly what is checked. One fix is to name what is
   fuzzed without claiming it is all of the untrusted-input code: "These
   parts of the code that read untrusted input are fuzzed on every change to
   the code: ...". The other is a fuzz target for `wire::unpack` (finding 9).
   Fixed with the first: `SECURITY.md` (which publet-core and
   publet-algorithms link to) now names what is fuzzed and says that
   `wire::unpack` has no fuzz target yet.

All of these are documentation only. They change the crate's
documentation, and should be recorded with `pubrel add --package publet-cli
internal "..."`.

10. **Was blocking: false claim, section 10 (`README.md`,
    `porcelain/src/main.rs:12`).** Both said "every command says which mode
    it used". Only `pub read` and `pub why` print their mode. `pub get` and
    `pub bundle` read the workspace and say nothing about it. Both files
    now say the true thing: only `pub sync` contacts a peer (no other
    module uses `publet_net`), `pub read` and `pub why` say they read
    locally, and `pub sync` says what its request disclosed.
11. **Was blocking: false claim (`README.md`, `main.rs` usage text,
    `porcelain/src/propose.rs`).** `pub propose` was described as
    submitting objects and recording their basis. It sends nothing and
    stores nothing: it prints the basis (`--basis=N`, or the head
    generation held, or 0) and how each object is stale. All three now say
    so. The usage text for `pub witness` said "record the log root". It
    prints it, and now says that.
12. **Was blocking: false claim (`README.md`, "Serving and syncing";
    `bin/pub-sync/src/main.rs:8`).** Both said "a peer serving altered bytes
    is caught on arrival". `pub-sync` computes each identifier from the
    bytes it received, then stores them under it (`main.rs:107-108`). The
    check in `Store::put` therefore cannot fail. Both now say that each
    object is stored under the identifier of its bytes, so altered bytes
    cannot pass for the object they alter. They also say that nothing
    checks the objects received against the domain's generation records.
13. **Was blocking: false claim (`porcelain/src/compose.rs`,
    `evidence_for`).** It said `citation` was "the only evidence role `pub
    compose` writes besides `method`". `pub compose` also writes
    `derivation`, `statement`, `quote` and `source` entries. The doc now
    names where each one is written.
14. **Was blocking: false claim (`porcelain/src/annotate.rs`).** The module
    docs said "Four kinds are covered here", then listed five. The command
    writes nine (`annotate.rs:330-333`). All nine are now listed. The
    `--kind is required` message listed six; it now lists all nine.
15. **Was blocking: stale claims in module docs (`porcelain/src/sign.rs`,
    `porcelain/src/relate.rs`).** `sign.rs` said nothing in the codebase
    produced a `sig` or `key` object, and that "every object this corpus
    has built is self-declared". `relate.rs` said "the porcelain composed
    two" object kinds. All three statements were once true and are not
    now. They were rewritten in the present tense. `sign.rs`'s summary line
    now also names `--rotate`.
16. **Section 9, README and `--help` disagreed.** The README did not list
    `get`, `document`, `relate`, `annotate`, `sign`, `policy`, `domain` or
    `--version`, and `--help` did not list `corpus renderings` or
    `--version`. The README now lists every command `main.rs` dispatches,
    with their required flags (checked against each module's error
    messages). The usage text adds `renderings` and `--version`. Only
    string literals changed.
17. **Section 9, the README's central use.** It had a synopsis, but no
    runnable command. It now has an example that creates a workspace,
    composes a claim, reads it and asks why. It was run with a fresh build
    of `pub`. The README also says what leaving out `--scope` does, which
    was run too (exit status 1).
18. **Section 9, the versioned interface, exit codes, MSRV.** The README
    now names the interface: the commands and flags, the exit codes (`pub`:
    0, 1, and 2 for no command or `--help`, all checked against
    `main.rs`), the output meant for scripts, and the files read and
    written. It states the minimum Rust version, 1.98. It states the MSRV
    policy in the standard's terms, which **is for a person to confirm**,
    since the repository did not state one for `pub`.
19. **Section 9, versioning (`README.md`, "Versions and releases").** The
    table said `added` bumps the minor version. Below 1.0, pubrel 0.5.4
    bumps the patch number, which is why `pubrel next` gives 0.2.2. The
    table now has pubrel's "From 1.0.0" and "Below 1.0.0" columns, as in
    pubrel 0.5.4's README, and the `internal` row. The README also now says
    that installing `publet-cli` installs `pub` only. Each plumbing command
    is a package of its own.
20. **Section 9, module docs of items other modules rely on.** `cargo
    clippy -p publet-cli -- -W clippy::missing_docs_in_private_items`
    reported 60 undocumented `pub(crate)` items. They were in `build.rs`
    (`Tree`, `Built`, `LockEntry`, `Lock::read`, `Lock::write`), in
    `compose.rs` (`ClaimFlags`' 17 fields) and in `render.rs` (`Names::read`,
    `Names::resolve`, `Ctx`, `Pipeline`, `cell_text`, `Rendering`,
    `Pinned`). Each now has a doc comment, written after reading the code.
    The run now reports none. The 390 that remain are module-private.
21. **Smaller corrections.** `Lock::render` had two doc paragraphs, and
    the first was stale ("keys sorted"). It was removed. `render.rs`
    documented labels as `Title [TAG] -- identifier`, but the code writes an
    em dash. The docs now show the em dash, as the README already did.

## Worth considering

22. **Section 10.** `domain.rs`, `revise.rs` and `policy.rs` open with
    the module's history ("Until now nothing in the toolchain could write
    these object kinds"). Each is still true as history, but describing the
    present would read better.
23. **Section 9.** `pub` exits 1 for an unknown command and 2 for no
    command. Both are usage errors.
24. **README install line.** It names `--tag v0.2.0`. That release
    exists, but v0.2.1 is the latest.

## Sections met

- **4, untrusted input:** apart from finding 9, objects, identifiers,
  proofs and signatures from outside go through publet-core and
  publet-algorithms, whose fuzz targets cover them. Downloads by `pub env`
  are checked against their identifiers. Every crate forbids `unsafe`.
- **7, supply chain:** `SECURITY.md` says how to report privately, lists
  `publet-cli`'s supported versions, and describes what fuzzing found.
  `cargo deny` and `cargo vet` cover the whole workspace.
- **8, cross-platform:** the `cross` job runs `--workspace --all-features`
  (`pubkit.json`), so it includes `pub`.
- **9, module docs:** `main.rs` and every module in `porcelain/src/` has
  `//!` docs saying what it does and why. So does every plumbing command's
  `main.rs`. `// covers:` comments are optional for a binary, and
  `porcelain/` has none.
- **9, semver checks:** not applicable to a binary. `release.json` does
  not set `semver-checks` for publet-cli, as is correct.

## Claims verified

- The README example: run in an empty directory with `pub` built from this
  tree. `pub read` ended with `[local] read from your replica; nothing was
  disclosed`. `pub why` gave `result undetermined`. `pub compose` without
  `--scope` exited 1.
- `pub --help`: 1722 bytes on stderr, none on stdout, exit 2. `pub bogus`:
  exit 1.
- Which modules contact a peer: `grep -l publet_net porcelain/src/*.rs`
  finds `main.rs` only, in `sync`.
- The render pipeline's first step is `pub myst`
  (`corpus/publets/render.myst-classicthesis/publet.json`, `write-myst`).
- pubrel 0.5.4's bump rule below 1.0: its README, "Category" table, and
  `src/version.rs:107`.
- crates.io: `cargo info` finds publet-core 0.1.4. It finds no publet-cli,
  publet-graph, publet-store or publet-net.
- `git describe --tags` with two annotated tags on one commit: tried in a
  scratch repository, both orders.

## Checks run

| Check | Result |
|---|---|
| `make doc` | pass, before and after the fixes |
| `make lint` | pass, before and after |
| `make msrv` (Rust 1.85) | pass; it builds publet-core and publet-algorithms only |
| `make publish-check` | pass; it packages publet-core and publet-algorithms only |
| `make doc-coverage-check` | pass, before and after; libraries only, which section 6 does not require of a binary |
| `make supply-chain-check` | pass; publet-core and publet-algorithms only |
| `make vectors-check` | pass |
| `make fmt-check` | pass, after the fixes |
| `make functional` | pass, after the fixes (354 scenarios) |
| `cargo clippy -p publet-cli -- -W clippy::missing_docs_in_private_items` | 60 undocumented `pub(crate)` items before, none after |

Not run:

- `cargo test --doc` and the docs.rs build. publet-cli has no library
  target, and docs.rs renders nothing for a binary.
- `make fuzz-smoke`. It is not on the agent's list, and CI runs it on the
  release pull request.

The make targets were run while the publet-algorithms audit was editing
that crate's docs in the same checkout. So the workspace-wide results
(`doc`, `lint`, `fmt-check`, `functional`) cover both sets of edits as they
stood at the time.
