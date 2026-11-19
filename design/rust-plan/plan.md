---
title: "PUB Reference Implementation Plan"
subtitle: "Rust, composable utilities, phased delivery"
description: A phased plan for a Rust reference implementation of the Publet Protocol, built as small composable utilities over narrow library crates, with per-phase deliverables and acceptance criteria.
keywords:
  - Rust
  - reference implementation
  - publet protocol
  - deterministic evaluation
authors:
  - name: David Schryer
    email: schryer@gmail.com
  - name: Claude (Anthropic)
---

+++ { "part": "abstract" }
This plan describes a reference implementation of the Publet Protocol
(`draft-schryer-publet-protocol-01`) in Rust. It is organized as a set of
small single-purpose utilities composed over narrow library crates, in the
manner of Unix filters and git's plumbing commands, rather than as one
application.

The composition stance is not stylistic. Objects in PUB are immutable and
content-addressed, evaluation is a pure deterministic function, and R16
places all reading on local data — so each operation the specification
defines is already a pure function from bytes to bytes. Exposing them as
such makes each independently testable, makes the conformance suite
language-agnostic, and lets the phases below be delivered and validated one
at a time.

Unit, property, and fuzz testing are in Rust. **All functional testing is
in Python, written as Gherkin feature files** that document each use case
in prose a non-programmer can read and execute it by invoking the binaries
as a user would. The same feature files serve as the cross-implementation
conformance suite.

Ten phases are specified, each with deliverables, acceptance criteria, and
the specification sections it covers.
+++

## 1. Purpose and Scope

### 1.1 Goals

1. A complete, auditable implementation of Sections 4 through 15 of the
   specification.
2. **Bit-identical evaluation** with any other conformant implementation
   (R8), demonstrated by published test vectors rather than asserted.
3. A conformance suite usable by implementations in other languages,
   expressed as readable use cases rather than as code.
4. Local-first operation (R16) as the default path, not a mode.

### 1.2 Non-Goals

- The settlement layer (Section 12) ships as traits and a null
  implementation. No ledger integration.
- Personhood attestation (Section 10.3) ships as a verification trait with
  no scheme implemented.
- No user interface beyond the command line.
- No network discovery beyond static peer lists in the first release.

### 1.3 Reference Practice

Engineering conventions follow the Apollo Rust Best Practices handbook
(`github.com/apollographql/rust-best-practices`). Section 4.2 records how
each chapter is applied here; where this plan departs, it says so and why.

---

## 2. Design Stance: Composable Utilities

### 2.1 Why This Fits

Four properties of the protocol make a filter-oriented design the natural
one rather than an imposed one.

| Protocol property | Consequence for the implementation |
|---|---|
| Objects are immutable (R1) | Tools never mutate inputs; every operation is a pure function |
| Objects are content-addressed (R2) | A CID is a stable, printable token — the natural unit to pipe |
| Evaluation is deterministic (R8) | Evaluation is a filter with no I/O, clock, or randomness |
| Reading is local (R16) | No daemon, no session, no server round-trip in the common path |

A monolithic binary would have to re-derive these boundaries internally
anyway. Exposing them makes each one separately testable.

### 2.2 Plumbing and Porcelain

The split follows git's. **Plumbing** commands are stable, scriptable, and
narrow; **porcelain** is one multi-call binary composing them for humans.

Plumbing commands, one job each:

| Command | Input | Output |
|---|---|---|
| `pub-canon` | object bytes | canonical bytes, or exit 1 with the violation |
| `pub-cid` | object bytes | CID |
| `pub-sign` | CID, key, purpose | signature object |
| `pub-verify` | objects | verdict per object; exit 1 on any failure |
| `pub-cat` | CIDs | object bytes from the store |
| `pub-ls` | domain or store | CIDs, filterable by type and class |
| `pub-edges` | CIDs | related CIDs, by kind and direction |
| `pub-lineage` | CID | lineage CIDs (`--authoritative` or `--full`) |
| `pub-closure` | CIDs | `depends` closure; exit 1 on cycle |
| `pub-equiv` | CIDs, policy | equivalence class members |
| `pub-eval` | CIDs, policy, snapshot | standing records |
| `pub-divergence` | two CIDs | divergent and stale terms |
| `pub-lint` | publet | structural findings (Section 5.7) |
| `pub-merkle` | CIDs | membership root |
| `pub-proof` | CIDs, generation | inclusion, absence, or consistency proof |
| `pub-delta` | two generations | `added` and `removed` lists |
| `pub-pack` / `pub-unpack` | CIDs / stream | object stream / objects |

Porcelain is a single `pub` binary: `pub init`, `pub sync`, `pub read`,
`pub why`, `pub compose`, `pub propose`, `pub witness`.

Every plumbing command is a thin `main.rs` over a library crate. The logic
lives in the library and is unit-tested there; the binary parses arguments
and maps errors to exit codes. No business logic in any `main.rs`.

### 2.3 Stream Formats

Three formats, chosen so that standard Unix tools remain useful:

- **CID lines** — the default on stdin and stdout. One CID per line, plain
  text. This is what makes `sort`, `comm`, `grep`, and `xargs` work
  directly on protocol data.
- **Object stream** — length-prefixed canonical CBOR frames, for bulk
  transfer. Produced by `pub-pack`, consumed by `pub-unpack`.
- **JSON Lines** — structured results, one record per line, for `jq`. Used
  by `pub-eval`, `pub-verify`, `pub-lint`, `pub-divergence`.

Rule: **every command that can accept CID lines does, and every command
that can emit CID lines does so by default**, with `--format=json` for
detail. Two examples that should work on day one of Phase 7:

```
  pub-ls --domain physics.v41 --class empirical \
    | pub-eval --policy mine.policy --format json \
    | jq -r 'select(.result == "unreplicated") | .cid' \
    | pub-cat | pub-lint
```

```
  pub-lineage --full QmTarget | pub-verify && echo "lineage intact"
```

### 2.4 Exit Codes

Uniform across all commands: `0` success; `1` protocol violation
(non-canonical bytes, bad signature, cycle, malformed generation); `2`
usage error; `3` not found; `4` I/O or store error. Machine-readable
detail on stderr as JSON when `--format=json` is set.

---

## 3. Workspace Layout

```
  publet/
  ├── Cargo.toml                 workspace, shared lints, pinned deps
  ├── crates/
  │   ├── publet-core/           objects, canonical CBOR, CID, signatures
  │   ├── publet-graph/          edges, lineage, closures, equivalence
  │   ├── publet-eval/           trust propagation, standing   (no I/O)
  │   ├── publet-merkle/         append-only log + membership tree, proofs
  │   ├── publet-domain/         manifests, generations, deltas, witnesses
  │   ├── publet-store/          persistence, declared sets, GC
  │   ├── publet-net/            HTTP client and server (Section 14.4)
  │   ├── publet-settle/         traits only; null implementation
  │   └── publet-lint/           structural tests (Section 5.7)
  ├── bin/                       one thin crate per plumbing command
  ├── porcelain/                 the `pub` multi-call binary
  ├── vectors/                   committed byte-level test vectors
  ├── fuzz/                      cargo-fuzz targets
  └── tests/                     Python functional suite (Section 6.2)
      ├── pyproject.toml
      ├── conftest.py            fixtures: workspaces, keys, nodes, binaries
      ├── features/
      │   ├── plumbing/          one file per plumbing command
      │   ├── porcelain/         one file per `pub` subcommand
      │   ├── scenarios/         end-to-end user journeys
      │   └── conformance/       one scenario per specification MUST
      ├── steps/                 shared step definitions
      └── support/               object builders, vector loaders
```

Dependency direction is strictly downward: `core → graph → eval`,
`core → merkle → domain`, with `store`, `net`, and the binaries above
those. **`publet-eval` depends only on `publet-core` and `publet-graph`
and MUST NOT depend on `store`, `net`, `std::time`, or any source of
randomness.** This is enforced by a CI check on the dependency graph, not
by convention.

---

## 4. Engineering Constraints

### 4.1 Imposed by the Specification

**Determinism (R8, §11.2) is the hardest requirement in the project** and
drives several decisions:

- A `Fixed6` newtype over `i128` carries all weights. It exposes only
  integer arithmetic with truncating division, and deliberately implements
  no conversion from any float type.
- `#![deny(clippy::float_arithmetic)]` at workspace level, plus a CI grep
  rejecting `f32`/`f64` anywhere under `crates/publet-eval` and
  `crates/publet-core`.
- Iteration is a fixed count, never a convergence test (§11.2). The API
  takes `iterations: u16` and has no tolerance parameter to misuse.
- Ordering is explicit everywhere: no `HashMap` iteration reaches a hash,
  a root, or an output. `BTreeMap` by default; where a `HashMap` is used
  for lookup speed, results are collected and sorted before use.

**Canonical form (§4.1) must reject rather than repair.** Off-the-shelf
CBOR decoders are permissive, so `publet-core` implements a validating
decoder that checks canonical form during parse and errors on non-shortest
integers, unsorted or duplicate map keys, indefinite-length items, any
float major type, or text that is not NFC. The round-trip property
`encode(decode(b)) == b` is a property test and a fuzz target.

**Verification is a type, not a convention.** Following the type state
pattern (handbook Ch. 7), parsed objects are `Unverified<T>` and only
`Verified<T>` is accepted by graph, evaluation, and store APIs. The sole
constructor of `Verified<T>` checks the CID and the required signatures.
It is then impossible to index or evaluate an unverified object by
mistake, because no such function exists.

**Crypto agility (§15).** Algorithm identifiers are in-band, so hashing
and signing are `dyn` trait objects behind a registry keyed by identifier
(handbook Ch. 6: dynamic dispatch is correct here — the set is open and
resolved at runtime). `ed25519` is required; a post-quantum algorithm is
added in Phase 1 subject to crate maturity at the time.

### 4.2 From the Apollo Handbook

| Chapter | Applied as |
|---|---|
| 1 Style and idioms | Borrow over clone in all hot paths — object bytes pass as `&[u8]`, never `Vec<u8>`, through parse and verify |
| 2 Clippy discipline | Lints configured once in `[workspace.lints]`; CI runs `clippy --all-targets -- -D warnings`; suppressions require a comment naming the reason |
| 3 Performance | Profile before optimizing; flamegraph the evaluation loop only after Phase 3 is correct and vectors pass |
| 4 Errors | `thiserror` per library crate with a typed error enum; `anyhow` only in `bin/` and `porcelain/`; **no `unwrap` or `expect` outside tests**, enforced by lint |
| 5 Testing | Doc tests are the primary usage examples for every public API; `insta` snapshots for standing records and proofs; error paths unit-tested, not just happy paths. Functional testing departs from the handbook and is in Python (Section 6.2) |
| 6 Generics and dispatch | Static dispatch by default; `dyn` reserved for the algorithm registries, where the set is genuinely open |
| 7 Type state | `Unverified`/`Verified` objects; domain generation building (`Draft → Sealed → Published`); proposal lifecycle |
| 8 Comments vs docs | Doc comments on every public item; comments explain *why*; TODOs become issues before merge |
| 9 Pointers | No `unsafe` in the workspace. `#![forbid(unsafe_code)]` in every crate |

Two deliberate departures. The handbook reserves `anyhow` for binaries, and
the plumbing binaries here are thin enough that several will have no error
handling of their own beyond mapping a library error to an exit code; that
is intended, since the error types live in the libraries where they can be
tested.

More substantially, **functional tests are not written in Rust.** The
handbook's testing chapter addresses tests that link the code under test.
The behaviour this project must pin down is the behaviour of binaries as a
user encounters them — exit codes, stdout bytes, what one command's output
does when piped into the next — and that is better expressed in a language
that cannot accidentally reach inside the implementation. Section 6.2 gives
the full rationale.

---

## 5. Phases

Each phase is independently shippable and independently verifiable. No
phase begins before its predecessor's acceptance criteria pass in CI.

Every phase from 1 onward delivers **feature files alongside its code**
(Section 6.2.3). A phase whose binaries work but whose scenarios are unwritten
is not complete.

### Phase 0 — Foundation

**Goal.** A workspace that enforces the project's constraints before any
protocol code exists.

**Deliverables.** Workspace skeleton with all crates stubbed; shared
`[workspace.lints]`; `#![forbid(unsafe_code)]` everywhere; CI running
`fmt`, `clippy -D warnings`, `test`, `doc`, and a dependency-direction
check; the no-float CI grep; `cargo-deny` for licences and advisories; a
CI matrix covering `x86_64-unknown-linux-gnu`, `aarch64-apple-darwin`, and
`x86_64-pc-windows-msvc`.

Also in this phase: the Python harness skeleton — `tests/pyproject.toml`,
`conftest.py` with the `PUBLET_BIN_DIR` fixture, one trivial feature file,
and a CI job running it. The harness exists before the first binary so that
no phase can defer its scenarios.

**Acceptance.** CI green on an empty workspace. A deliberately added `f64`
in `publet-eval` fails CI. A deliberately added `publet-eval → publet-net`
dependency fails CI. `pytest tests/` runs and passes against a stub binary.

### Phase 1 — `publet-core`

**Spec.** §4 entire, §5.1–5.2, §10.1, §10.5.

**Goal.** Parse, verify, construct, and emit every object type.

**Deliverables.** Validating canonical CBOR codec; CID computation with a
hash registry; signature objects with domain separation and a signature
registry; typed structs for all object types with `Unverified`/`Verified`
states; key objects, rotation, revocation; the 64 KiB ceiling.
Commands: `pub-canon`, `pub-cid`, `pub-sign`, `pub-verify`.

**Features.** `plumbing/canon.feature`, `cid.feature`,
`sign_verify.feature`; `conformance/canonical_form.feature` covering every
rejection rule in §4.1 as a negative scenario.

**Acceptance.** Round-trip property test over generated objects. Fuzz
target on the decoder runs clean for 24h. Signatures verify against vectors
produced independently of this codebase. Every §4.1 rejection rule has a
Gherkin scenario asserting exit code 1 and the named rule on stderr.

### Phase 2 — `publet-graph`

**Spec.** §5.3–5.7, §6, §6.1, §7, §8, §9.1–9.3.

**Goal.** Answer structural questions over a set of verified objects.

**Deliverables.** Forward and reverse edge indices; lineage computation,
authoritative and full, with branch enumeration; `depends` closure with
cycle rejection; acyclicity enforcement for `supersedes`, `derived-from`,
`depends`; equivalence components; definitional divergence and staleness
(§9.2); claim-class rules governing which annotations are admissible.
Commands: `pub-ls`, `pub-edges`, `pub-lineage`, `pub-closure`,
`pub-equiv`, `pub-divergence`, `pub-lint`.

**Features.** `plumbing/ls.feature`, `edges.feature`, `lineage.feature`,
`closure.feature`, `equiv.feature`, `divergence.feature`, `lint.feature`;
`conformance/acyclicity.feature`, `class_rules.feature`.

**Acceptance.** A fixture graph reproducing Appendix A. Cycle-closing edges
rejected for each acyclic kind, each with a negative scenario. A scenario
shows §9.2 separating divergence from staleness on a fixture where both
occur. A verdict annotation on a `normative` publet is rejected.

### Phase 3 — `publet-eval`

**Spec.** §11 entire. **The critical phase.**

**Goal.** A pure function `(policy, objects, target) → standing`, bit-identical
everywhere.

**Deliverables.** `Fixed6` arithmetic; personalized PageRank with fixed
iterations, per-node outbound normalization, subject scoping, and decay;
divergence factor over argued non-redundant disputes; equivalence
aggregation counting each signer once; replication floor and independence;
the acceptance predicate including `unreplicated` and the `restricted`
cap; proof and reproduction dominance; `eval` and `snapshot` objects.
Command: `pub-eval`.

**Features.** `plumbing/eval.feature`;
`conformance/evidence_dominance.feature`, `divergence_factor.feature`,
`novelty.feature`, `equivalence.feature`, `restricted_access.feature`.

**Acceptance.** Golden vectors committed and byte-compared, producing
identical output on all three CI targets. A property test asserts output is
invariant under input permutation and thread count. Every `result` variant
has a scenario. Dominance is tested adversarially in Gherkin: overwhelming
endorsement plus one independent inconsistent reproduction returns
`unreplicated`, never `accepted`. A redundant dispute scenario shows zero
contribution to the divergence factor.

### Phase 4 — `publet-merkle` and `publet-domain`

**Spec.** §14.1, §14.1.1, §14.1.2, §14.3.1.

**Goal.** Domains that can be advanced, proved, and synchronized by delta.

**Deliverables.** Append-only log with consistency proofs (RFC 6962
algorithms) and sorted membership tree with inclusion and absence proofs;
domain manifests with bound and `closed_under` enforcement; generation
records with `added`/`removed` and mandatory removal justification;
malformed-generation rejection; delta computation, application, and
self-verification against the membership root; exponentially spaced
checkpoints; witness attestations. Commands: `pub-merkle`, `pub-proof`,
`pub-delta`, `pub-pack`, `pub-unpack`.

**Features.** `plumbing/merkle.feature`, `proof.feature`, `delta.feature`,
`pack.feature`; `conformance/generations.feature`, `consistency.feature`,
`witnessing.feature`.

**Acceptance.** Proof round-trips for all three kinds, against RFC 6962
reference vectors where applicable. Scenarios assert: a generation removing
an object without a `ref` is rejected; a tampered delta fails root
comparison; a client 300 generations behind syncs in O(log n) fetches; a
split view is detected from two witness attestations at one generation.

### Phase 5 — `publet-store`

**Spec.** §13.1, §13.2, §14.6.

**Goal.** Hold domains on disk with fast open and verified integrity.

**Deliverables.** Embedded key-value store (`redb` recommended: pure Rust,
no C++ toolchain; confirm maturity at implementation time); declared-set
management as domain CIDs; garbage collection outside the declared set;
tombstone records; integrity scan. Extends `pub-cat`, `pub-ls`.

**Features.** `plumbing/cat.feature` extended; `scenarios/store.feature`
covering declared sets, GC, and integrity scanning.

**Acceptance.** A domain of 10^6 objects opens in under a second and
answers `pub-cat` in constant time. A scenario asserts GC never removes an
object inside the declared set, and that an integrity scan detects a
corrupted object by CID mismatch.

### Phase 6 — `publet-net`

**Spec.** §13.2–13.4, §14.4, §14.3.2.

**Goal.** Two nodes synchronize a domain over HTTP.

**Deliverables.** Server (`axum`) implementing every §14.4 endpoint;
client (`reqwest`) with mandatory CID verification on receipt; declared-set
publication; tombstone serving; **no `have`/`want` negotiation of any
kind**, per §14.3.2. Anonymizing-transport support via a configurable
proxy.

**Features.** `scenarios/two_node_sync.feature`,
`conformance/no_have_want.feature`, `scenarios/tombstone_replication.feature`.

**Acceptance.** A scenario starts two nodes, advances one by twenty
generations, syncs the other by delta, and asserts identical membership
roots. A node returning tampered bytes is rejected by the client. A
wire-level scenario asserts the client transmits no object identifiers
during synchronization, and that no endpoint accepts a holdings list.

### Phase 7 — Porcelain

**Spec.** §14.2, §14.3.3.

**Goal.** The local-first workflow, end to end.

**Deliverables.** `pub init`, `pub sync`, `pub read`, `pub why` (standing
with its components and scope), `pub compose`, `pub propose` with `basis`
recording and relevant-delta reporting, `pub witness`. Mode indication:
every command states whether it is operating locally or in query mode
(§14.3).

**Features.** `porcelain/` in full — one file per subcommand;
`scenarios/appendix_a.feature` reproducing A.1 through A.10 of the
specification as a single narrative; `scenarios/stale_basis.feature`;
`scenarios/privacy_modes.feature`.

**Acceptance.** `appendix_a.feature` runs from an empty state and passes.
`pub propose` against a stale basis succeeds and reports all three
staleness cases, each asserted separately. A scenario asserts query mode is
visibly labelled in output and local mode is the default where a replica
exists.

### Phase 8 — Conformance Suite

**Goal.** Let a second implementation prove itself.

**Deliverables.** `vectors/` — canonical-form positive and negative cases,
CID and signature vectors, evaluation vectors with policies and expected
standings, Merkle proof and delta vectors. The `features/conformance/` tree
completed and tagged, so that the Gherkin suite *is* the conformance
definition: a second implementation sets `PUBLET_BIN_DIR` and runs
`pytest tests/ -m conformance`. A coverage report mapping every normative
statement in the specification to the scenarios exercising it, and naming
those with none.

**Acceptance.** The suite passes against this implementation, and correctly
fails a deliberately broken build. Every MUST in §4, §11, and §14.1 has at
least one tagged scenario. The coverage report is published with the
release and its gaps are listed, not hidden.

### Phase 9 — Optional Layers

**Deliverables.** `publet-settle` traits with a null implementation;
personhood verification trait with no scheme; hooks for a triage provider
(§7.4) that is advisory-only by construction — the API returns
annotations and has no path to suppress an object.

**Acceptance.** The workspace builds and the full Gherkin suite passes with
these crates absent, demonstrating §12.1's claim that settlement is
optional.

---

## 6. Testing Strategy

Testing is split by what it is testing, and the split is strict.

### 6.1 Rust: Inside the Code

| Level | Scope | Tooling |
|---|---|---|
| Unit | Every library function, error paths included | `cargo test` |
| Doc | Every public API carries a runnable example | `cargo test --doc` |
| Property | Round-trips, permutation invariance, determinism | `proptest` |
| Fuzz | CBOR decoder, proof verifier, delta application | `cargo-fuzz` |
| Snapshot | Standing records, proofs, internal structures | `insta` |
| Golden | Cross-platform byte comparison of evaluation | `vectors/` |

These test *functions*. They link the crates and reach internals, which is
appropriate for invariants with no user-visible surface — canonical
decoding rules, fixed-point arithmetic, Merkle node construction.

### 6.2 Python and Gherkin: Outside the Binaries

**Every functional test is a Gherkin scenario in Python, executed by
invoking the binaries as a subprocess.** No functional test links, imports,
or otherwise reaches into the Rust code.

Three reasons this is the right boundary here rather than a preference:

1. **The deliverable is a set of binaries with a composition contract**
   (Section 2). Exit codes, stdout bytes, and pipe behaviour are the
   product. A test that links the library cannot observe any of them.
2. **A test that cannot reach inside cannot drift inward.** Rust
   integration tests tend to acquire a helper constructing a state the CLI
   could not produce, and then they have stopped testing the program.
3. **The same scenarios run against any implementation.** Binaries are
   resolved from `PUBLET_BIN_DIR`, so an implementation in another
   language runs this suite unmodified. That is what makes Phase 8 a
   conformance suite rather than a regression suite.

**Tooling.** `pytest-bdd`, for pytest's fixtures (temporary stores, key
material, multi-node topologies), `pytest-xdist` for parallelism, and the
wider plugin ecosystem. `behave` is the purer Gherkin runner and the
reasonable alternative if fixture complexity stays low.

#### 6.2.1 Feature Files Are the Use-Case Documentation

A feature file states a use case in prose that someone who does not program
can read, review, and dispute. It is the artifact connecting the
specification's normative language to observable behaviour.

```gherkin
Feature: Canonical form is rejected, never repaired
  # Specification 4.1: an implementation MUST reject non-canonical bytes
  # and MUST NOT re-canonicalize and accept.

  Scenario Outline: Non-canonical encodings are refused
    Given an object encoded with <defect>
    When I run "pub-canon" with that object on stdin
    Then the exit code is 1
    And stderr names the violated rule "<rule>"
    And stdout is empty

    Examples:
      | defect                     | rule                   |
      | a non-shortest integer     | shortest-form integers |
      | unsorted map keys          | sorted map keys        |
      | a duplicate map key        | unique map keys        |
      | an indefinite-length array | no indefinite length   |
      | a float value              | no floating point      |
      | text in NFD                | NFC normalization      |
```

The evidence-dominance rule is where a readable scenario is worth most,
because the behaviour is deliberately counter-intuitive:

```gherkin
Feature: No amount of agreement substitutes for one replication
  # Specification 11.4.1 (R9)

  Scenario: Overwhelming endorsement cannot accept an unreplicated claim
    Given an empirical publet "P1" with an open method
    And 50 trusted keys each affirming "P1"
    And no reproductions of "P1"
    When I evaluate "P1" under policy "strict"
    Then the result is "unreplicated"

  Scenario: One inconsistent reproduction outweighs any endorsement
    Given an empirical publet "P1" with an open method
    And 50 trusted keys each affirming "P1"
    And 1 independent reproduction of "P1" with outcome "inconsistent"
    When I evaluate "P1" under policy "strict"
    Then the result is not "accepted"
```

A MUST NOT is testable at the wire level, which no unit test can reach:

```gherkin
Feature: Synchronization discloses only a generation index
  # Specification 14.3.2: have/want negotiation MUST NOT be used.

  Scenario: The client never enumerates its holdings
    Given a node at generation 41
    And a peer at generation 47
    When the node synchronizes from the peer
    Then the peer received no object identifiers from the node
    And the node's membership root equals the peer's generation 47 root
```

Composition is itself tested behaviour, being the contract of Section 2.3:

```gherkin
Feature: Plumbing commands compose over CID lines

  Scenario: Unreplicated empirical claims listed in one pipeline
    Given a domain "physics.v41" containing 200 empirical publets
    And 3 of them meet the replication floor under policy "mine"
    When I run the pipeline:
      | pub-ls --domain physics.v41 --class empirical      |
      | pub-eval --policy mine --format json               |
      | jq -r 'select(.result == "unreplicated") \| .cid'  |
    Then stdout contains exactly 197 lines
    And every line is a valid CID
```

#### 6.2.2 Organization

| Directory | Contains | Written during |
|---|---|---|
| `features/plumbing/` | One file per plumbing command: arguments, exit codes, stdin and stdout contracts | The phase delivering that command |
| `features/porcelain/` | One file per `pub` subcommand, from a user's standpoint | Phase 7 |
| `features/scenarios/` | End-to-end journeys, including Appendix A of the specification | Phases 7 and 8 |
| `features/conformance/` | One scenario per normative MUST and MUST NOT | Continuously |

Step definitions live in `steps/` and are shared across features. They stay
thin: build inputs, run a process, assert on exit code and bytes. Fixture
construction — publets, keys, policies, domains — lives in `support/` as a
fluent builder, so scenarios read as prose rather than as setup.

#### 6.2.3 Rules

- **Feature files are written in the same phase as the code they test**,
  never retrofitted. A phase is not complete until its features pass.
- **Every MUST and MUST NOT carries a tag** of the form `@must-4.1` naming
  its specification section. A CI check reports which normative statements
  have no scenario, and that report is the definition of conformance
  coverage.
- **No functional test imports Rust or links a crate.** Enforced by the
  suite having no build dependency on the workspace.
- **Binaries are resolved from `PUBLET_BIN_DIR`.** No path into the Cargo
  target directory appears anywhere in the suite.
- **Scenarios assert on bytes**, not on parsed and re-serialized values,
  wherever the specification constrains encoding.

### 6.3 Two Project-Specific Rules

**Determinism is tested as a cross-platform property, not a local one.** A
golden vector passing on one machine proves nothing about R8. The CI matrix
compares bytes across three targets on every commit touching
`publet-eval`, at both the Rust golden-vector level and the Gherkin
`pub-eval` level.

**Every MUST NOT gets a negative scenario.** A parser accepting what it
should reject fails silently in production and is invisible to positive
tests. Phase 1 and Phase 4 acceptance depend on these.

## 7. Risks and Sequencing Notes

**Determinism regressions are silent.** A `HashMap` iteration order
reaching an output, or a library update changing a rounding path, produces
correct-looking results that differ across implementations. Mitigated by
the CI matrix and by keeping `publet-eval` dependency-free beyond `core`
and `graph`.

**Canonical CBOR may require writing rather than adopting a codec.**
Permissive decoders are the norm. Budget Phase 1 for the possibility that
no crate rejects strictly enough and the validating decoder is written
from scratch against §4.1.

**Post-quantum signature crates are young.** `ed25519` is required and
sufficient for conformance. Treat the second algorithm as a Phase 1
stretch item and verify crate maturity rather than assuming it.

**Evaluation cost is unaddressed by this plan.** Appendix B.5 of the
specification records it as open. The reference implementation targets
correctness and determinism; it will be too slow for large domains, and
that is acceptable for a reference. Do not optimize before Phase 3
vectors pass.

**Phases 1 and 3 carry most of the project risk.** Everything downstream
assumes byte-exact parsing and byte-exact evaluation. Phases 2, 4, and 5
are comparatively ordinary engineering.

---

## 8. Deliberately Out of Scope

Recorded so the boundary is a decision rather than an omission: no ledger
or settlement implementation; no zero-knowledge personhood scheme; no DHT
discovery in the first release; no graphical interface; no performance
work beyond correctness; no automated triage provider, only the advisory
interface.
