---
title: "PUB Self-Hosting Plan"
subtitle: "The protocol's vocabulary, algorithms, and design choices as publets"
description: A plan for representing the Publet Protocol's own terms, procedures, and architecture decisions inside a PUB knowledge graph, with the toolchain gaps that must be closed first.
keywords:
  - publet protocol
  - self-hosting
  - ontology
  - knowledge graph
authors:
  - name: David Schryer
    email: schryer@gmail.com
  - name: Claude (Anthropic)
---

+++ { "part": "abstract" }
This plan answers whether the reference implementation of the Publet
Protocol can be used to hold its own documentation, and what has to change
first.

The short answer is: nearly, and the gap is one-sided. Every **reading**
operation the corpus needs already exists as a binary. **Authoring** does
not: the toolchain can create two of the nine object kinds the graph reads,
and the missing seven include relations, which are most of what an ontology
is. Three patches are required before the work can start, one of them
blocking.

The plan also records a structural finding that changes the shape of the
exercise. Three of the five strata proposed -- the dictionary, the phrase
layer, and the design choices -- are **not truth-apt** under Section 5.2 and
will never carry a verdict. This is the system behaving correctly, not a
defect, but it means most of the corpus is valued for structure and
disputability rather than for standing. The strata that *can* earn standing
-- algorithms and measured claims about the system -- earn it by
reproduction, and the reproductions are the repository's own test scripts.
That is the strongest argument for doing this at all: it makes the
documentation checkable by the same machinery that checks the code.
+++

## 1. The question

The vocabulary in the specification and this implementation is
project-local. `publet`, `standing`, `viewpoint`, `divergence factor`,
`lineage`, `domain`, `generation`, `assumed accountability` -- none of these
are terms a reader arrives with. Underneath each sits a construct from the
common vocabulary of computing: content addressing, personalized PageRank,
a seed set, a dispersion measure over a subgraph, an append-only revision
chain, a Merkle-committed membership set, a delta with a root commitment.

A reader who knows the second vocabulary cannot currently reach the first
without reading 13,000 words of specification. A bilingual mapping would
fix that, and the natural place to express such a mapping is a graph of
definitional publets joined by `equivalent` relations -- which is precisely
what this system is for.

So the proposal is to hold the project's own documentation in the project's
own data structure, in five strata:

1. **Dictionary** -- one definitional publet per term.
2. **Phrases** -- multi-word constructions that are not compositional.
3. **Concepts and algorithms** -- what each procedure does and how to run it.
4. **Design and architecture choices** -- what was chosen, and why.
5. **Two overviews** -- one technical, one from a user's perspective.

## 2. What trying it revealed

The assessment below is not from reading the code. Each finding came from
composing real publets about this system with the shipped binaries.

### 2.1 The read path is complete

Every query the corpus needs already has a binary:

| Need | Command |
|---|---|
| What does this term depend on? | `pub-closure` |
| What disputes, supports, or supersedes it? | `pub-edges --kind=K [--in\|--out]` |
| Do two publets presuppose a term differently? | `pub-divergence` |
| What revisions has this definition had? | `pub-lineage` |
| What is this publet's standing, and why? | `pub why` |
| What does this subject resolve to under a policy? | `pub-index` |
| Is this publet well-formed as an assertion? | `pub-lint` |

### 2.2 The write path authors two object kinds out of nine

The graph reads `publet`, `rel`, `ann`, `doc`, `anchor`, `key`, `verdict`,
`critique`, and `triage`, plus `domain`, `generation`, `index`, and `bounty`
elsewhere. The entire toolchain -- 22 binaries and the porcelain -- can
author exactly two: `publet` and `policy`. Everything else is constructed by
hand-rolling CBOR, which is what the Python test suite does in
`tests/support/objects.py`.

For a corpus that is mostly *edges*, this is the blocking gap. There is no
way to say "content address depends on digest" or "standing is equivalent
to personalized PageRank score" without writing bytes by hand.

### 2.3 The classes behave well, and one requirement is a gift

Composing a definition, a procedure, a design choice, and a measurement in
turn:

- `definitional` and `normative` composed clean.
- `procedural` accepted a `--depends` edge onto a term.
- `empirical` **refused to compose without `--method`**, demanding the CID of
  a procedural publet describing how to repeat the observation.

That refusal is the most useful thing the system did. The claim being made
was "the evaluation vectors digest to `014f9e6a936bf4bf` on every tested
architecture". Section 5.5 will not let that be published as a bare
assertion; it requires a method others can execute. The method is
`tools/matrix.sh`. So the documentation's factual claims about the system
are forced to cite the scripts that verify them, and a reader who doubts one
runs it.

### 2.4 Two lint defects, found by using it

Both are the same failure I fixed earlier in the sentence counter: an
advisory tool that over-fires on ordinary technical content teaches its user
to ignore it, and then it protects nothing.

**L1 -- the coordinator test misfires on procedures.** Composing

> to verify an object: recompute its content address from its bytes **and**
> compare it to the identifier it was retrieved under

drew `single-assertion: "and" may join two assertions that could each stand
alone`. It does not. It joins two *steps*. Section 5.7 is written about
assertions -- "negating it yields exactly one coherent counter-claim" -- and
a procedure cannot be coherently negated. The sentence-count and coordinator
tests should not run on the `procedural` class.

This is a specification question before it is a code change: §5.7 does not
currently exempt any class. The exemption should be argued in the spec and
then implemented, not slipped into the linter.

**L2 -- identifiers count as quantities.** The empirical claim above drew
`single-quantity: 5 quantitative claims`. There is one quantity in it; the
other four are digit runs inside the hex digest `014f9e6a936bf4bf`.
`count_quantities` must skip digit runs that sit inside a longer
alphanumeric token, exactly as `mentions()` already skips a term inside a
longer word.

Given how much of this corpus is content addresses and digests, L2 alone
would make the linter useless for it.

### 2.5 No term lookup

Nothing anywhere searches by term. Finding "the publet that defines Merkle
tree" means listing every definitional publet and reading each. At 200 terms
that is the operation performed most often, and it does not exist.

The capability is already built, twice: `Publet::term()` parses the term
from a definitional publet's content, and `contested_terms()` in
`publet-graph/src/lint.rs` already builds the whole term-to-CID map. It has
no command-line surface.

## 3. The finding that reshapes the exercise

`pub why` on a fresh definitional publet returns:

```
class            definitional
result           not-truth-apt
...
Not truth-apt: this class has no verdict and never will.
Look at attribution, usage, and critique instead.
```

Section 5.2 makes `definitional`, `normative`, and `expressive` classes that
accept no verdict. Mapped onto the five proposed strata:

| Stratum | Class | Can it earn standing? |
|---|---|---|
| 1. Dictionary | `definitional` | **Never.** Described by usage, not voted true. |
| 2. Phrases | `definitional` | **Never.** |
| 3. Concepts and algorithms | `procedural`, `formal` | Yes -- by reproduction, or by proof. |
| 3b. Measured claims | `empirical` | Yes -- by independent reproduction. |
| 4. Design choices | `normative` | **Never.** An ought-claim is not truth-apt. |
| 5. Overviews | `doc` | Not a claim; a binding of claims. |

This is correct behaviour. A system that let a majority vote on what a word
means, or on whether a design decision was right, would be the failure mode
the whole protocol is built to avoid. But it means the exercise produces
something different from what "a knowledge base of our documentation" might
suggest.

**What the non-truth-apt strata get instead** is the part worth having:

- **Divergence detection.** `pub-divergence` reports when two publets
  presuppose a term differently. Run across the corpus, it finds the places
  where the specification and the implementation have quietly drifted on
  what a word means.
- **Equivalence classes.** The bilingual mapping of §4 *is* an equivalence
  class, and it is computed rather than asserted by one author.
- **The contested-term lint.** Once a definition is disputed, every publet
  that uses the term without declaring it gets flagged. This is the
  mechanism that keeps a large corpus honest.
- **Lineage.** A definition that is revised leaves a chain; anything
  referencing the old one keeps referencing the old one.

**What the truth-apt strata get** is the payoff: stratum 3 can be genuinely
accepted, and the reproductions are `make check`, `verify-suite.sh`,
`verify-optional.sh`, and `tools/matrix.sh`. Documentation whose factual
claims are settled by the repository's own CI is a materially different
artefact from documentation that is merely written down.

## 4. The bilingual ontology

This is the highest-value stratum and should be built first after the
patches land, because it is what makes the rest legible.

Each mapping is three objects: a definitional publet in project vocabulary,
a definitional publet in common computing vocabulary, and an `equivalent`
relation between them. Section 11.6 then computes the equivalence class, so
a reader entering from either vocabulary reaches the other.

| Project term | Common term |
|---|---|
| publet | content-addressed immutable assertion record |
| content address (CID) | cryptographic hash of canonical serialization |
| standing | score from personalized PageRank over a trust graph |
| viewpoint | personalization vector / seed set |
| divergence factor | dispersion measure over the dispute subgraph |
| lineage | append-only revision chain with a single authoritative head |
| domain | membership set committed by a sorted Merkle tree |
| generation | delta with a root commitment |
| snapshot root | Merkle root over sorted membership |
| anchor | inclusion proof against a published log root |
| `Fixed6` | fixed-point rational, resolution 10^-6 |
| consistency proof | RFC 6962 append-only proof |
| redundancy (R10) | set containment over grounds identifiers |
| assumed accountability | public vouching without recorded linkage |
| nullifier | per-scope unlinkable pseudonym |

Note that several of these are *not* clean equivalences, and the system is
the right place to record that. "Standing is personalized PageRank" is
approximately true and precisely wrong: the evaluation applies a replication
floor and an evidence-dominance rule that no PageRank variant has. That is
what `equivalent` with an `aspect`, and `disputes`, are for -- and getting
these distinctions written down is most of the value.

## 5. Patches required first

Ordered. P1 blocks everything; P2 and P3 block doing it at scale.

### P1 -- relation authoring (blocking)

A `pub relate` porcelain command and/or a `pub-rel` plumbing binary that
emits a `rel` object:

```sh
pub relate --kind=equivalent --from=CID --to=CID [--aspect=...] [--note=...]
```

All relation kinds the graph reads must be authorable. The acyclicity rule
(§6) is already enforced on load, so an edge closing a cycle on an acyclic
kind will be refused where it should be. Gherkin scenarios in
`tests/features/porcelain/`.

**Without this there is no ontology, only a list.**

### P2 -- term lookup

```sh
pub-term --dir=D <term>        # the CID(s) defining it
pub-term --dir=D --list        # every term, with its CID
```

Reuse `Publet::term()`. Report *all* matches, never one: two competing
definitions of a term is the normal state, and collapsing them to one would
be the system picking a winner, which it must not do. Should also report
whether each is contested.

### P3 -- lint corrections (L1, L2)

L2 is a straightforward fix in `count_quantities`. L1 needs a specification
decision first: propose the class exemption for §5.7, then implement it.
Both need scenarios in `tests/features/conformance/atomicity.feature`,
including the hex-digest case that found L2.

### P4 -- annotation authoring (before stratum 3 can earn standing)

`pub annotate --kind=verdict|reproduction|critique --target=CID ...`. Not
needed to *build* the corpus, but stratum 3's whole point is that it can be
accepted, and nothing can be accepted until reproductions can be recorded.

### P5 -- independence conditions 1--3 (§11.4)

Consume `independence_distance` over the trust graph; read `affiliated`
annotations and bar two signers sharing an organization over an overlapping
period; read the declared `funding` string. Scenarios for each, including
the two-humans-one-institution case and the two-Wikimedia-keys case.

Not required to build the corpus, and required before any statement about
replication in it can be trusted.

### P6 -- the unread annotation kinds and fields

The audit is done (§6.22): seven annotation kinds unread, fifteen declared
fields absent, and that is a lower bound. Not all of it is needed for the
corpus, and the subset that is:

- **`usage`** -- without it a `definitional` publet cannot accumulate the
  corpus evidence its own class definition rests on. Blocks §6.17.
- **`classifies`** -- subject membership. Blocks any taxonomy, arXiv
  included, and reconciles `pub-index` with §13.3.
- **`trusts.subjects`** -- subject-scoped trust, without which per-source
  keys are undifferentiated scalars (§6.15).
- **`affiliated`** -- also required by P5.

The remainder (`assessment`, `attests`, `timestamped`, `well-formed`, and
the scattered fields) should be triaged explicitly into implement-now,
implement-later, or propose-for-removal-from-the-specification. A field in
a published table that nothing implements is a defect in one document or
the other, and deciding which is the point of the triage.

### P7 -- document authoring (before stratum 5)

`pub doc` assembling publets into a `doc` with anchors and bindings. Needed
only for the two overviews.

### P8 -- replace the one source-reading scenario

Unrelated to self-hosting, but found alongside it and worth doing while the
suite is open.

The scenario "the ledger interface cannot express a standing or a read"
currently reads `crates/publet-settle/src/ledger.rs` and greps the trait's
method signatures for forbidden substrings. That is a **naming tripwire, not
a proof of absence**: it would miss a neutrally named method
(`fn apply(&self, ctx: &Ctx) -> Outcome`), a capability arriving by
supertrait or associated type, or a store handle reaching the ledger through
a parameter type. It is also the one scenario in the suite a second
implementation cannot run, because it reads a Rust file by path.

The observable consequence is testable instead, and I have confirmed it
works: put a bounty in the store, read it with `pub-settle`, re-evaluate,
and assert the standing is byte-identical. Verified with a 9000-basis-point
bounty on a live claim -- `pub why` output unchanged to the byte. This is
strictly stronger than grepping the trait, and it needs no source access.
Keep the source-reading test as a Rust unit test where it belongs; the
Gherkin scenario should assert the behaviour.

### P9 -- N-way term divergence

`pub-divergence` over any number of publets, reporting for each shared term
how the definitions partition and which sources sit in which partition.
Pairwise comparison answers a question the corpus is not asking (§6.19).

## 6. Seeding from Wikipedia, and the second trust root

A proposal was made to download the English Wikipedia content dump, sign
content derived from it with an **organization key** to serve as a second
trust root, seed the core dictionary from it, and let two machine
participants debate to produce the rest.

The goals behind this are right, and this section keeps all three. The
mechanisms need rework, because two of them collide with rules this
implementation enforces and a third has a licensing consequence.

### 6.1 An organization key does not do the job it was chosen for

The reason for a second trust root was §8's finding: with one author and one
trust root, every weight is self-derived, so stratum 3 cannot honestly reach
`accepted`.

An organization key does not fix that. From `publet-graph/src/view.rs`:

> Only human principals may author, be counted toward a replication floor, or
> hold stewardship (R11).

An organization key **may** sign, fund, operate infrastructure, and -- since
the policy's `roots` are not principal-filtered -- be named as a trust root.
So the proposal is not forbidden. It simply does not reach the goal:
acceptance for a truth-apt class is governed by the **replication floor**,
not by weight, and organization reproductions do not count toward it. Five
scenarios in the suite already assert this, including
`reproductions_from_an_organization_do_not_count_toward_the_floor` and
`overwhelming_endorsement_cannot_accept_an_unreplicated_claim`.

A second trust root would therefore change the numbers in the `weight` block
of `pub why` and leave `independent consistent 0 (floor 2)` exactly where it
is.

### 6.2 A second key held by one principal is not a second person

This is the deeper problem, and it is the one to take seriously.

If the corpus is generated from a dump by one operator and signed with a
second key, the graph shows two keys and there is one principal. That is a
Sybil. It is the precise attack the replication floor, the independence
rule, and the personhood section exist to prevent, and this implementation
ships no personhood scheme, so nothing would detect it.

For any corpus this would be a flaw. For a corpus whose purpose is to
document this protocol it is self-refuting: the worked example of the system
would be founded on a fabricated independence claim, and every reader who
understood the protocol well enough to benefit from the corpus would be
able to see it.

**There is no mechanism substitute for a second person.** Either someone
else reproduces something, or stratum 3 stays at `open` and the corpus says
so plainly. The latter is an honest and publishable state.

### 6.3 What Wikipedia is genuinely good for here: a second *viewpoint*

The useful reframing is that Wikipedia should be a second **viewpoint**, not
a second **person**.

Viewpoints are *supposed* to differ. R1 makes evaluation viewpoint-relative,
and §11.8 requires that a reader be told whose roots produced what they are
seeing. The single best demonstration this system can give is the same graph
evaluated under two policies with different roots, yielding different
standings -- and that demonstration requires no claim about independence at
all. It needs exactly what the proposal supplies: a second, differently
grounded body of assertions.

So the organization key stays, honestly labelled `principal: organization`,
and is used for what §10.1 permits it to be used for. What changes is the
claim being made about it: it seeds an alternative viewpoint, and it is
never presented as a second reviewer.

### 6.4 Seeding: attribution, not authorship

Content derived from Wikipedia should enter as **`attributive`** publets,
not `definitional` ones:

> the English Wikipedia article "Merkle tree", revision 1234567890, defines
> it as: "<short quotation>"

This is correct on three counts at once.

**It is true.** A paraphrase of a Wikipedia definition is a claim by whoever
wrote the paraphrase, not by Wikipedia. Signing such a paraphrase with a
Wikipedia-derived key would be a false attribution, and §5.2 confines an
attributive verdict to "whether the attribution holds" -- which is precisely
the check that a false attribution fails.

**It is verifiable.** Revision identifiers are stable and permanently
addressable, so provenance is checkable by anyone, offline, against a dump
they fetch themselves.

**It is honest about what it settles.** Under §5.2 a verdict on an
attributive publet speaks to the provenance of the quotation and never to
whether the quoted content is true. Wikipedia being a tertiary source, that
is exactly the epistemic status it should carry.

The project's own `definitional` publets then sit alongside these and
`disputes` them, or declares a scoped `equivalent`, where the project's
usage departs from common usage. That divergence is the most valuable output of the whole exercise --
see §6.6.

### 6.5 Licensing: a real incompatibility to avoid

Wikipedia text is CC BY-SA. This repository is Apache-2.0.

CC BY-SA permits redistribution, so bulk extraction is *licensed*; the
problem is that share-alike **propagates**. A corpus embedding substantial
Wikipedia prose becomes a CC BY-SA work living inside an Apache-2.0
repository, and the two do not compose.

The attributive shape of §6.4 avoids this by construction: store the
citation, the revision identifier, and a short quotation, rather than
extracted article bodies. Short attributed quotation is the ordinary
practice these licences are built to accommodate, and it is also the only
shape that is *true*, which is the better reason to prefer it.

If at some later point bulk text is genuinely wanted, it belongs in a
separate CC BY-SA repository referenced by content address, not merged into
this one.

### 6.6 The debate, and what machine judgement may do

Two machine participants producing verdicts is not available, and the rule
is one this project wrote deliberately. §7.4 requires a machine judgement to
declare its engine, and the evaluation layer reads none of them: a triage
annotation orders attention and decides nothing. There is a scenario
asserting that adding one leaves every standing byte-identical. Machine
output cannot be a verdict, cannot be a reproduction, and cannot count
toward a floor.

Two further points make this more than a formality. Two instances of one
model are not independent of each other in any sense the independence rule
means. And a model summarising Wikipedia and then a model assessing that
summary is a closed loop with no observation in it.

What machine judgement **may** do here is exactly what triage is for, and it
is genuinely useful at this scale:

- ordering ~250 publets by which most need human attention;
- flagging candidate redundancy for a human to confirm, with R10's
  mechanical set-containment test as the arbiter, never the model;
- proposing candidate `equivalent` edges between the two vocabularies for a
  human to accept or reject.

Every one of these is advisory, disclosed, and re-runnable, and none of them
decides anything.

**The real debate is structural, not conversational.** It is the
`attributive` publets saying what common usage is, the `definitional`
publets saying what this project means, `disputes` edges where they differ,
and `pub-divergence` finding term conflicts mechanically. That produces the
thing actually wanted -- a documented record of where this project's
vocabulary departs from the common one, and why -- and every step of it is
checkable by someone who trusts neither participant.

### 6.7 Getting the articles without downloading the dump

The directory originally named cannot support this, and the reason is
structural rather than a matter of size. Its 19 files (48.8 GB) are
page-range splits, each a **single monolithic bzip2 stream**: sampling 8 MB
from 500 MB into one of them finds zero stream headers. Reaching any article
means decompressing sequentially from byte 0. There is no index and no
random access.

The **multistream** dump in the standard `enwiki/` layout is built for
exactly this. It is a concatenation of independently decompressible bzip2
streams of 100 pages each, with a companion index giving one line per
article:

```
offset:pageid:title
565:10:AccessibleComputing
565:12:Anarchism
```

The first field is the byte offset of the stream containing that article. So
retrieving one article is: look up its offset, look up the *next* distinct
offset to get the stream's end, issue one HTTP range request for that slice,
and decompress it on its own. Everything else in the file is never
transferred.

Measured against the live dump while writing this:

| | |
|---|---|
| Multistream dump | 26.8 GB -- never downloaded |
| Index | 285 MB -- downloaded once |
| One stream | ~1.6 MB, exactly 100 pages |
| Cost of one article | one range request |
| Cost of ~300 articles | 285 MB + at most ~480 MB |

Verified end to end: fetching 1,584,813 bytes at offset 100,991,559 of the
26.8 GB file yielded exactly 100 pages including "Hash function", page
13790, revision 1368708252. The remaining 26.8 GB was not transferred.

Recording the **revision identifier** is the part that matters downstream.
It is what makes the resulting `attributive` publet checkable by a third
party, who can re-fetch precisely the revision quoted rather than whatever
the article says today.

`tools/wiki-seed.py` in the implementation repository does this. It batches
by stream so two articles in the same 100-page block cost one request, and
it emits one JSON object per article: title, page id, revision, lead
sentence, source, and licence.

### 6.8 Two pitfalls in the extraction, both found by hitting them

Neither is obvious from the format documentation, and both produce
plausible-looking wrong output rather than an error -- which is the
dangerous kind.

**Nested brackets defeat regular expressions.** Templates (`{{...}}`) and
media links (`[[File:...]]`) both nest, and a non-greedy match stops at the
first inner terminator. The first attempt at "Hash function" returned

> `between keys "John Smith" and "Sandra Dee".]]`

-- a fragment of an image caption, presented as the article's definition.
Every bracketed construct has to be matched by depth counting.

**Entity decoding must come first.** The dump XML-escapes the wikitext, so
an HTML comment arrives as `&lt;!--...--&gt;`. A comment stripper run before
the decode passes it through untouched, and "Hash table" duly returned an
editorial note about underscores as its lead sentence.

With both fixed, a whole 100-page stream extracts **71 lead sentences from
71 articles**. The other 29 pages are 26 redirects and 3 disambiguation
pages, which have no lead sentence to extract; the tool reports them as
skipped rather than counting them as failures.

### 6.9 Politeness and provenance

The dumps are served for bulk use, but a run issuing hundreds of range
requests should identify itself in `User-Agent` and not parallelise
aggressively. The tool refuses to proceed if the server answers a range
request with `200` instead of `206`, because a server ignoring `Range` would
otherwise silently download 26.8 GB.

### 6.10 Wiktionary: yes to a second key, no to a second reason

Adding Wiktionary as a second seed source is worth doing, and the stated
reason for a separate key -- "a different data source, though the same
parent organization" -- is half right in a way the specification can settle
precisely.

**The source distinction does not need a key.** It is already carried,
verifiably, inside the attributive publet: "English Wiktionary entry
*hash*, revision N, sense 3" and "English Wikipedia article *Hash
function*, revision N" are different attributions on their face, and a
third party can check both. A key is an assertion about who signed; the
attribution is a fact anyone can re-fetch. Distinctions belong in the more
checkable place.

**What a separate key does buy is a third viewpoint.** Encyclopedic summary
and lexicographic description are genuinely different groundings, and a
reader who trusts one more than the other holds a legitimate position under
R1. Three policies -- author-rooted, Wikipedia-rooted, Wiktionary-rooted --
make the Phase H comparison substantially better than two.

**But the "same parent organization" instinct is exactly right, and §11.4
already rules on it.** Two reproductions are independent under a viewpoint
only when all four of these hold:

1. no trust path shorter than the policy's `independence_distance` connects
   their signers;
2. **they share no `affiliated` annotation naming the same organization
   over an overlapping period**;
3. they declare no shared funding source;
4. they share no listed materials.

Both projects are Wikimedia Foundation. Condition 2 therefore bars them from
counting separately, and the separate key changes nothing about that. Two
keys, one affiliation, one principal.

`tools/wiki-seed.py` now records `affiliation` on every emitted record for
this reason, so the fact travels with the data rather than living in a
footnote here.

### 6.11 The independence rule is three-quarters unimplemented

Checking the above against the code turned up a genuine conformance defect,
and it is the one that governs this proposal.

| §11.4 condition | Status |
|---|---|
| trust-path distance | `independence_distance` is parsed into the policy and **never read** |
| shared `affiliated` annotation | **not implemented** |
| shared funding source | **not implemented** |
| shared listed materials | implemented |

So the implementation would count two Wikimedia-derived keys as independent
reproductions. More seriously, it would count **two humans in the same
laboratory** as independent, which is the case the rule exists for: two
people sharing an institution, a grant, and a freezer are not a replication.

This matters for the plan beyond the Wikipedia question. §6.2 asserts that
adding keys does not add people -- but today that is a claim this document
makes, not one the code enforces. Implementing conditions 1--3 turns it into
a mechanical rule, which is the standard the rest of this project holds
itself to.

### 6.12 Why the coverage report did not catch it

The conformance report reads 47 of 47 sections, and §11.4 is among them.
Both facts are true and they measure less than they appear to.

`tools/must-coverage.py` maps **RFC 2119 keyword statements** to scenarios.
§11.4 contains one MUST -- reproductions counted toward a floor must be
signed by human principals -- and that MUST is implemented and tested, so
the section reports as covered. The four-condition definition immediately
above it contains no keyword at all. It is a normative *definition*: the
implementation must satisfy it, and no coverage tool looking for MUST,
SHOULD, and MAY will ever ask whether it does.

That is how three of four independence conditions went unimplemented at
100% coverage. The number is not wrong; the claim it supports is narrower
than "the specification is implemented", and this document should be the
place that says so rather than leaving a reader to discover it.

A defensible follow-up is to teach the coverage tool to flag sections
containing a definitional "is ... when" or "are ... when" construction as
requiring a scenario, even absent a keyword. That is a heuristic and will
have false positives, which is the correct trade for a measurement whose
failure mode is silent over-reporting.

### 6.13 More sources: two different axes, often conflated

Three further sources were proposed, each to receive its own key. Sorting
them requires two axes that are easy to conflate, and the table below only
answers one of them.

**Attribution answers credit. Licensing answers copying.** They are
independent. Recording that a source said something, with a pointer anyone
can follow, is citation -- it is what scholarship is made of, and no
licence is needed to credit someone with an idea. Ideas are not
copyrightable; only particular expression is. What a licence governs is
whether their *sentences* may be reproduced, and perfect attribution does
not enlarge that permission -- a fully credited verbatim copy is still a
copy.

So the table below says which sources' **expression** may be reproduced. It
says nothing about which may be cited, credited, or built upon, and the
answer there is: all of them.

| Source | Licence | Verdict |
|---|---|---|
| English Wikipedia | CC BY-SA 4.0 | Usable; share-alike propagates (§6.5) |
| English Wiktionary | CC BY-SA 4.0 | Usable; same constraint |
| **The Rust Reference** | **MIT / Apache-2.0** | **Usable, and the cleanest of all of them** |
| Real Python glossary | Proprietary, commercial | **Not usable** |
| `isLinXu/Stanford-CS-Course` | Mirror's own MIT; content not the mirror's to license | **Not usable as vendored content** |

**The Rust Reference is the best-licensed source proposed so far.**
`rust-lang/reference` is dual MIT/Apache-2.0, and Apache-2.0 is this
repository's own licence. Unlike the Wikimedia sources it carries no
share-alike obligation, so material derived from it composes directly with
the repository instead of creating the CC BY-SA island §6.5 warns about.

**Real Python is a commercial publisher.** The glossary carries no open
licence, and the site returns `403 Forbidden` to automated requests, which
is a plain statement about bulk automated extraction whatever the copyright
position. Its *sentences* may not be harvested into the corpus. Its
*content* is entirely usable in the restatement shape of §6.13.1, which is
the shape that needs no licence because it reproduces nothing.

**The Stanford repository does not hold the rights it appears to grant.**
It declares MIT, but the licence file reads `Copyright (c) 2023 GatiLin` --
the mirror's maintainer. That MIT grant covers the maintainer's own work:
the Sphinx scaffolding, the build files, the README. It cannot cover the
CS231n course material under `source/`, which belongs to Stanford and its
instructors and was never the mirror's to license.

This is worth stating as a general rule rather than a one-off, because it
will recur: **a declared licence on a mirror is a claim about the mirror,
not provenance of rights in what it mirrors.** Checking the copyright line
inside the licence file takes ten seconds and is the check that catches it.
If Stanford's *text* is wanted, it has to come from Stanford under whatever
terms Stanford actually offers -- and if what is wanted is what CS231n
*teaches*, that needs no permission at all (§6.13.1).

#### 6.13.1 Quote or restate: the class system already draws this line

The protocol turns out to encode the distinction exactly, and the choice of
class is the whole of it.

**Quoting** a source produces an `attributive` publet: *the Rust Reference,
commit `abc123`, defines a trait object as "<short quotation>"*. The claim
belongs to the source. Provenance is checkable, §5.2 confines any verdict
to whether the attribution holds, and reproduction of their expression is
what makes a licence necessary.

**Restating** a source produces a `definitional` publet with a citation:
*trait object: a value of an opaque type implementing a set of traits* --
authored by whoever wrote that sentence, crediting the Reference as where
the understanding came from. This is §6.4's point turned around: a
paraphrase is a claim by its paraphraser, not by the source. It reproduces
no protected expression, so **no licence is required, for any source.**

The consequences are practical:

| | `attributive` (quote) | `definitional` (restate) |
|---|---|---|
| Whose claim | the source's | yours |
| Needs a licence | yes | no |
| Wikipedia, Wiktionary | permitted, share-alike propagates | permitted, no propagation |
| Rust Reference | permitted, composes cleanly | permitted |
| Real Python, Stanford | **no** | **yes** |
| Verdict speaks to | provenance of the quote | not truth-apt (§3) |

So the unlicensed sources are not excluded from the corpus. They are
excluded from one of its two shapes. A reader of the finished graph can
still see that a definition was informed by CS231n or by Real Python,
follow the link, and judge for themselves -- which is the whole of what
attribution is for.

One thing attribution genuinely does not fix: **share-alike propagates
regardless of how well a quote is credited.** §6.5 stands. Crediting
Wikipedia impeccably does not discharge CC BY-SA's obligation on the
resulting work; only not reproducing the expression does, which is a
further argument for preferring the restatement shape by default and
quoting only where the exact wording is the point.

### 6.14 These sources do not have the same standing to define

The licence gate is the practical filter. The interesting one is
epistemic, and it is a distinction the corpus has not needed until now.

- **The Rust Reference does not describe what a Rust term means; it
  stipulates it.** It is the normative authority for the language's
  vocabulary. If it and Wikipedia disagree about "trait object", the
  Reference is not merely better sourced -- it is constitutive.
- **Wiktionary describes usage.** That is precisely what the
  `definitional` class says a meaning is settled by, which is why §6.10
  moved the dictionary stratum there.
- **Wikipedia summarizes published work and disclaims original research by
  its own policy.** It is tertiary on purpose.
- **Course material teaches**, and good teaching is often knowingly
  imprecise: a definition simplified for a lecture is a pedagogical claim,
  not a precision claim, and promoting one to a definition misrepresents
  what its author was doing.

All four seed as `attributive` publets, and §5.2 keeps the verdict on each
confined to whether the attribution holds -- correct for all of them. What
differs is not how they are recorded but how much a reader should weight
each, and *on which terms*.

### 6.15 Subject-scoped trust is specified and unimplemented

That "on which terms" is the crux, and the specification already provides
for it. From §18.5, a `trusts` annotation carries:

> `weight` 1..1000, `subjects`

`subjects` is the mechanism for "I trust the Rust Reference on Rust
terminology and not on hash functions". It is exactly what makes a
per-source key worth having.

It is not implemented. `gather.rs` reads `weight` from a `trusts`
annotation and nothing else; `subjects` appears nowhere in the workspace.
So today every trust edge is one undifferentiated scalar, and five source
keys would yield five undifferentiated roots -- a reader could turn the
Rust Reference up or down, but not turn it up *for Rust terms only*.

This is the second specified-but-unimplemented mechanism found in as many
questions, and like the independence conditions of §6.11 it was invisible
to the coverage report for the same reason: the `subjects` field is
described in a table, and a table cell carries no RFC 2119 keyword.

Two findings in two turns, both from asking what a proposed feature would
actually do, suggests the gap is systematic rather than coincidental: the
suite tests the statements that say MUST, and the object-shape tables are
where the unimplemented fields are hiding. **An audit of every field named
in the §18.5 tables against the code is warranted before the corpus work
starts**, because the corpus will exercise exactly these paths.

### 6.16 A stopping rule for keys

"These would all get separate keys" invites a proliferation the plan should
bound, and §6.10 already supplies the principle: the attribution carries
the source, verifiably; a key buys a *viewpoint*.

So the rule is: **a source earns a key when someone would genuinely want to
read the corpus under it.** A Rust implementer would want to read it rooted
in the Rust Reference. Nobody wants to read a knowledge graph rooted in a
single commercial tutorial site. Sources failing that test are still
perfectly good *citations* inside a publet; they simply do not need a
signing identity of their own.

There is a second, harder constraint that §6.13.1 exposes: **the
restatement shape cannot produce a source key at all.** A restated
definition is signed by whoever restated it, so it yields an authored
publet with a citation, not a source-attributed one. Only quotation
produces objects attributed to a source, and quotation is exactly what
needs a licence. So a source can hold a meaningful key only if its
expression is quotable -- which ties the licence gate and the key question
together after all, though not in the direction it first appeared.

By that rule the corpus has three seeded keys -- Wiktionary, Wikipedia, the
Rust Reference -- plus the author's. Four viewpoints, each of which someone
would plausibly choose, and each licensed for the use. Which is also as
many columns as the Phase H comparison can present without becoming the
undifferentiated wall of numbers §7.1 forbids.

### 6.17 The concept is not any of its wordings

The model to build on is that a **concept** is the thing being recorded, and
the sentences various sources use for it are evidence about where its
boundaries lie -- not competing candidates for being the definition.

This is closer to the specification than what §6.13.1 proposed. The
`definitional` class is "a stipulated meaning, **described by usage** rather
than voted true", and several sources' wordings of the same idea are
precisely usage evidence. Nothing about that framing was invented for this
corpus; it is what the class already meant.

It also resolves the licensing tension of §6.13 properly, rather than by
manoeuvre. If a concept is what several wordings agree on, then no single
source's expression is load-bearing, and what the corpus needs from each is
a *short* quotation held next to the others for comparison. That is exactly
the shape copyright accommodates -- and it is the right shape for the
epistemics first, with the licensing falling out as a consequence. A corpus
that needed one source's paragraph in full would be one that had mistaken a
wording for the concept.

So the arrangement is:

- **descriptive publets**, one per source, `attributive`, each a short
  attributed quotation with its revision or commit -- the evidence;
- **a concept publet**, `definitional`, authored by whoever did the
  synthesis, citing every descriptive publet it was drawn from -- the
  claim;
- **`equivalent` relations** among the descriptive publets, which compute
  into an equivalence class (§11.6): the machine-visible statement that
  these wordings are about one thing;
- **`disputes` or divergence** where they are not, which is where a
  boundary has been found.

The concept publet is not truth-apt (§3) and never will be. But the
**procedure** by which boundaries were drawn is a `procedural` publet, and
that class *is* settled by reproduction: another person running the same
triangulation over the same sources should reach the same boundaries. The
corpus's method is therefore checkable even though its definitions are not,
which is a better position than it may first appear.

### 6.18 One correction: concepts are not assembled from word definitions

"Built up from publet word definitions" holds for compositional
constructions and fails for most of the interesting vocabulary, and the
failure is not incidental -- it is what makes a term a term.

A hash function is not a *hash* that is a *function*. A trait object is not
a *trait* that is an *object*. A content address is not an *address* of
*content* in any sense recoverable from the two words. Where the meaning
*is* recoverable from the parts, the construction does not need a publet at
all; §7's stratum D exists precisely for the phrases "a reader cannot
assemble from the parts".

The specification is unambiguous about what the edge means. §5.4: `depends`
lists publets whose meaning is **presupposed**. Presupposition is not
composition. A concept publet depends on its terms being fixed -- it is not
derived from them, and an implementation that tried to compute meaning by
walking `depends` would be reading the edge as something it does not say.

The practical consequence is a reordering, not a removal. The dictionary
stratum is a **prerequisite** for the concept stratum, not a constructor of
it: it fixes the vocabulary in which concept publets can be stated without
ambiguity, and the contested-term lint then enforces that they use it. The
concepts still have to be written by someone who understands them.

### 6.19 Divergence is pairwise; triangulation needs an N-way view

The machinery for "boundaries and connections" mostly exists.

**Connections** are in hand. `equivalent` relations compute into
equivalence classes over any number of members (§11.6), so a concept with
four source wordings is one class, not six assertions.

**Boundaries** are not. `publet-graph::compare` takes `left` and `right`,
and `TermConflict` carries exactly two sides. With four sources and ~250
terms, finding where they diverge means six pairwise runs per term and
fifteen hundred results with no aggregate view -- and the interesting
question is not "do these two differ" but "on this term, how do all four
partition, and which is the outlier".

That is the shape triangulation actually needs, and it is a modest
extension rather than a new mechanism: the same term extraction, grouped
rather than compared. Added as P9.

### 6.20 Sources discovered along the way

The source list is open. Anything encountered while working -- the arXiv
subject taxonomy is the example raised -- can be added as it is found, and
nothing in the design requires the set to be fixed in advance. Two gates
apply to each addition and neither is onerous:

- the licence gate of §6.13, which governs only whether the source's
  *expression* may be quoted, never whether it may be cited or restated;
- the key rule of §6.16 -- a source earns a signing identity when someone
  would want to read the corpus rooted in it, and otherwise is simply a
  citation.

The arXiv taxonomy is a different kind of thing from the others, and worth
naming as such. It is not a set of definitions; it is a **classification
scheme**. Under §13.3 that is not a definitional publet at all -- subjects
are objects with `classifies` annotations attaching things to them, and
competing taxonomies coexist as sets of `classifies` annotations by
different keys, selected among per viewpoint. A taxonomy is therefore the
natural way to give the corpus *subjects*, which nothing else proposed so
far supplies.

It also lands squarely on an unimplemented mechanism -- see §6.22.

### 6.21 The deliverable is the map, not the route to it

The end product is the linked map of core concepts with their weights, not
a record of how it was arrived at. That is right, and it separates cleanly
into two things worth keeping apart because they are easy to conflate.

**Drafting history should not exist in the first place.** The protocol
records lineage for what is *published*, not for what was thought. A
definition revised four times before anyone else sees it should be composed
once, when it is ready. Nothing forces working notes into the graph, and
they should not go in.

**Derivation structure must be kept**, and is not history. Which sources a
concept was triangulated from, and which terms it presupposes, are
`depends` edges and citations -- present-tense structure that says what the
concept rests on, not a diary of how it was found. This is exactly the
"lower level publets link to the original sources" property, and it is what
lets a reader audit a concept without reading an account of its
composition.

So: no drafting history, full derivation structure. The protocol already
keeps these on separate axes.

**One constraint on the map itself.** For `definitional` publets `result`
is permanently `not-truth-apt` (§3), so the weights on a concept map are
*not* truth weights. They measure how far a given viewpoint's trust reaches
a publet -- useful, and precisely the R1 demonstration, but a different
quantity from "how correct is this".

§11.3 is explicit: clients MUST NOT reduce standing to a badge without
exposing its components, and MUST render `scope` wherever they render a
standing. A concept map with a single number per node is the exact artifact
that rule anticipates. Every node in the delivered map therefore has to
carry whose roots produced its weight and the scope of the claim, or the
map becomes the "47 endorsements" failure in graph form. This is a design
constraint on the deliverable, not an obstacle to it, but it needs to be
designed in rather than retrofitted.

### 6.22 The audit, run: seven annotation kinds are never read

P6 proposed auditing the specification's object-shape tables against the
code, on the suspicion that the two mechanisms found by accident were not
the only ones. The audit has now been run -- `tools/check-fields.py` -- and
the suspicion was correct.

**Seven of seventeen annotation kinds are not read anywhere in the
workspace**, and fifteen declared fields are absent:

| Never read at all | Declared fields absent |
|---|---|
| `assessment`, `attests`, `affiliated`, `classifies`, `timestamped`, `usage`, `well-formed` | `trusts.subjects`, `verdict.effort`, `critique.defect`, `critique.omitted`, `proof-checked.system`, `proof-checked.artifact`, `reproduction.funding`, `reproduction.data`, `resolution.thread_root`, `affiliated.period`, `attests.identity`, `classifies.subject`, `usage.corpus`, `timestamped.service`, `well-formed.test` |

The check is deliberately crude -- it asks whether the field name occurs as
a string literal anywhere -- which over-reports success. A clean row means
little; a miss is decisive. So this is a **lower bound** on what is absent.

Two of these are directly load-bearing for the ideas of the last two
sections, which is how they came to light:

- **`usage` is never read.** Its table entry is "corpus evidence", "for
  `definitional` publets" -- it is the mechanism by which a definition is
  "described by usage rather than voted true". The entire concept-
  triangulation model of §6.17 rests on it, and nothing implements it.
- **`classifies` is never read.** §13.3 defines subject membership as
  `classifies` annotations, and `pub-index` -- whose own documentation
  begins "Resolve a subject under a declared policy" -- requires a policy
  and filters by class without ever consulting one. It resolves something;
  it does not resolve subject membership as specified. Any taxonomy work,
  arXiv included, needs this first.

`affiliated` being unread is the §6.11 independence finding seen from the
other side, and confirms it was not an isolated omission.

### 6.23 Partial correctness, and why it is not a number

A usage can be right in its own context and misleading outside it: a
definition of "hash function" that omits collision resistance is sound in
an introductory setting and actively harmful in a security one. The
question is how to record that, and whether `usage` should grow a guide
field to hold it.

It should not, and the specification already answers the question three
ways that compose into one.

**Implicit assumptions become explicit publets.** `scope.conditions` is a
list of *CIDs* (§5.3), not prose. Each assumption a definition rests on is
its own publet, addressable, citable, and disputable on its own terms. The
"surrounding context" is not something to describe in a guide; it is
something to name.

**Partial correctness is an `assessment`.** §5.2's vocabulary already
contains `sound-in-scope` beside sound, superseded, unsupported, refuted
and undetermined. An assessment is a signer's judgement rather than an
input to evaluation, which is exactly why it may be filed about a
definitional publet where no verdict may be cast -- and the loader gates
the class rule on the `verdict` kind alone, so it always could be. This is
now implemented: filing one shows under a heading saying it is not an
input, and the result stays `not-truth-apt`.

A basis is required. A judgement with no stated basis is a preference, and
a reader cannot weigh a preference.

**Partial equivalence is `equivalent` with an `aspect`.** Relations carry
one (§6), so "these agree *in the cryptographic sense*" is a scoped edge
rather than a bare claim of sameness.

#### Why there is no partial-correctness weight

Tracking "weights of partial correctness" is the one part to decline, and
declining it is a design commitment rather than an omission.

§11.3's outcome set is `accepted`, `contested`, `rejected`,
`undetermined`, `unreplicated`, `not-truth-apt`. There is deliberately no
"70% true", and a scalar would be worse than absent. **A claim that is 70%
true is a claim that is true under some conditions and false under others,
and naming the conditions says strictly more than the number does.** The
number also discards exactly what a reader needs: which conditions, and
whether theirs are among them.

It would also collide with rules the project already holds. §7.1 and §11.3
forbid reducing standing to a badge without exposing its components, and a
partial-correctness percentage is a badge with no components at all.

#### One way, not four

The apparent multiplicity resolves once the question is asked precisely,
because the three mechanisms answer three different questions:

| The question | The mechanism |
|---|---|
| Under what conditions does this hold? | `scope.conditions` -- on the publet |
| Does someone judge it sound only there? | `assessment: sound-in-scope` -- an annotation |
| Do two statements agree in some respect only? | `equivalent` with `aspect` -- a relation |

One is a property of the claim, one is a judgement about it, one is a
relation between claims. A "usage guide" field would be a fourth way of
saying the first, in prose nothing can compute on, and adding it would
break the rule that there be one obvious way.

#### A correction to this plan

Earlier revisions of this document referred to a `refines` relation. **No
such kind exists**: §18.4 registers `supersedes`, `translates`, `depends`,
`disputes`, `supports`, `equivalent`, `retracts`, `derived-from`, and
`delegates`. Where "refines" appeared, the mechanism meant is `equivalent`
carrying an `aspect`, or `disputes`. The references have been corrected.

### 6.24 `well-formed`: a specification defect, argued for removal

The last unread annotation kind should not be implemented. It should come
out of the specification.

Its row in the annotation table reads "structural test results, Section
5.7", and **§5.7 never mentions it**. The cross-reference points at a
section that defines atomicity, the authoring warnings, decomposition
profiles, and the prohibition on similarity deduplication -- and says
nothing about publishing results as annotations. The kind exists only as a
table row and a registry entry.

Three reasons to remove rather than define it:

**It adds no information.** §5.7's tests are computed locally from the
publet's own content. Any reader can run `pub-lint` and get the same
findings at no cost. An annotation asserting them tells a reader something
they could already determine, which is the opposite of the case for
`usage`, where the citation points at a corpus the reader does not hold.

**An accumulating count of them is the badge §7.1 forbids.** "Forty-seven
keys found this well-formed" is a raw annotation count presented as a
quality signal, and the specification already prohibits exactly that. A
kind whose natural use is a prohibited one is a hazard shipped as a
feature.

**It duplicates an existing channel.** A signer who wants to record a
structural judgement about a publet has `assessment`, which carries a basis
and is already the mechanism for "a signer's judgement". Adding a second
way to say the same thing breaks the rule that there be one obvious way.

The recommendation is therefore to strike `well-formed` from §18.5 and from
the annotation table. If a structural finding is worth publishing, it is
worth publishing as an `assessment` with `unsupported` and a basis naming
the test that fired.

### 6.25 Independence: three conditions of four

Section 11.4's four conditions now stand as follows.

| Condition | Status |
|---|---|
| 1. No short trust path between signers | **not implemented** -- see below |
| 2. No shared `affiliated` organization over an overlapping period | implemented |
| 3. No shared funding source | implemented |
| 4. No shared listed materials | implemented |
| *(beyond the four)* `same-person-as` attestation | implemented |

Condition 1 is not an oversight and should not be closed casually.
§11.4 makes independence **viewpoint-relative** -- "independent *under a
viewpoint*" -- while `evidence_for` gathers facts before any policy is
known. Affiliation, funding and materials are *declared facts* about the
reproductions and belong in the gather pass. A trust path is not a fact
about the reproductions at all; it is a fact about the reader.

Closing it therefore means either passing the policy into `evidence_for`
or moving the independent-count computation into `evaluate`. Both are
architectural changes to the boundary that currently keeps gathering
policy-free, and the boundary is load-bearing: it is why the same gathered
evidence can be evaluated under four viewpoints in Phase H without
re-reading the graph. The change is worth making deliberately and is not
corpus-blocking.

### 6.26 L1 is a contradiction inside the specification, not a linter bug

L1 was recorded as "the coordinator test misfires on procedural publets".
That was too narrow in one direction and too generous in another, and both
corrections matter before the corpus starts.

**It is not only procedural.** Running the tests over representative
content for all eight classes splits them exactly in half:

| Atomicity tests pass | Atomicity tests fire |
|---|---|
| `formal`, `empirical`, `definitional`, `normative` | `procedural`, `attributive`, `archival`, `expressive` |

The split is not arbitrary. It is precisely the four classes whose content
**is** the assertion against the four whose content **instructs, quotes,
records, or expresses**. §5.2's own table says so: an instruction, "*X*
said *Y*", a primary-source record, and poetry are not claims whose
internal structure is one assertion. §5.7's test -- "negating it yields
exactly one coherent counter-claim" -- cannot be applied to any of them.
A procedure does not negate. Negating an attribution denies that *X* said
it, which says nothing about how many sentences *Y* has.

**It hits the seed, not just the algorithms.** The earlier note said this
would become visible when the algorithms stratum is written. That is wrong:
seed material enters as `attributive` publets (§6.4), so every seeded
quotation longer than a sentence draws a warning from the first day of
Phase A2.

**It is a contradiction inside the specification.** §5.5 requires an
empirical publet's evidence to include *exactly one* entry with
`role: "method"` referencing a **`procedural` publet** describing how the
observation may be repeated, and §5.7 tells implementations to warn when a
publet joins clauses. A method joins clauses; that is what a method is. So
one section obliges a shape the other flags, and fixing the linter alone
would leave that standing in the normative document.

A first draft of this section argued further that a method therefore
*cannot* be decomposed. That was wrong, and the error is worth recording
because it was an inference rather than a reading. §5.5's "exactly one" is
a requirement on the **citation** -- one identifier names the method
unambiguously -- not a requirement that the method be a leaf. A procedure
may name sub-procedures in `depends`, each naming further ones until base
steps are reached, and `depends` being acyclic guarantees the
decomposition terminates. `pub-closure` already resolves the whole tree,
so the mechanism existed before the question was asked.

The exemption survives the correction and its justification improves: a
step is not an assertion however small it is. Negating "warm the sample"
yields no counter-claim, at any depth of the tree.

#### What the section conflates

§5.7 runs five tests and treats them as one family. They are two:

| Test | Property | Applies to |
|---|---|---|
| more than one independent clause | atomicity | assertion classes |
| a coordinating conjunction joining stand-alone assertions | atomicity | assertion classes |
| more than one quantitative claim | atomicity | assertion classes |
| unresolved anaphora pointing outside the publet | self-containment | **all classes** |
| a contested term absent from `depends` | self-containment | **all classes** |

Self-containment is not negotiable for any class. A method saying "then add
it" with no antecedent is a defective method; a quotation cut so that its
pronouns dangle is a badly cut quotation. What varies is atomicity, and it
varies exactly with whether the content is an assertion.

#### Recommendation

Change the specification first, then the code, in that order and in one
commit each.

The alternative -- exempting classes in the linter and leaving §5.7 as it
is -- would create the same defect this session has spent its time
cataloguing, in the opposite direction. Every gap found so far was the
specification saying something the implementation did not do.
`tools/check-fields.py` measures that direction only. An implementation
doing something the specification does not say would be invisible to it,
and a second implementation reading §5.7 would warn on every method and
every quotation, leaving its authors to guess at an exemption nobody wrote
down.

The cost is low. This is a draft under the authors' control rather than a
published RFC with independent implementers, and the edit is a paragraph
and a table.

#### One design note on the code change

`publet-lint` takes text and a caller-supplied term list, and depends on
nothing (§6.15, §2.2). Passing a `Class` into it would pull the class
vocabulary into a crate that deliberately has no protocol types.

The signature should carry the decision rather than the class:
`check(content, terms, atomic: bool)`. The caller already knows the class
-- `publet-graph::check_in` has the publet -- and the linter keeps knowing
only about text. The layering that made the similarity prohibition
structural is worth preserving for the same reason it was built.

## 7. Phases

**Phase A -- patches.** P1, P2, P3. Acceptance: `make check` clean; new
scenarios for each; L2 demonstrated against a real content address.

**Phase A2 -- the seed pipeline.** Already built and verified:
`tools/wiki-seed.py` resolves titles through the multistream index and
fetches one stream per range request, emitting title, page id, revision,
project, affiliation, and lead sentence only -- never article bodies (§6.5,
§6.7). It serves both Wikimedia projects. The Rust Reference is a git repository
rather than a dump, so it needs a separate small reader -- and being
Apache-2.0, it is the one source whose material composes with this
repository directly (§6.13). Remaining work is the three term lists, three
key objects, and three policies naming them as trust roots.
Acceptance: the seed run transfers under 1 GB against a 26.8 GB dump; every
emitted record carries a revision identifier a third party can re-fetch; the
organization key is refused by the replication floor, with a scenario
asserting it.

**Phase B -- the bilingual dictionary.** The ~15 mappings of §4, plus the
terms they depend on. Three objects each. Acceptance: `pub-term` resolves
every project term; every mapping is a computed equivalence class, not an
asserted one; `pub-divergence` reports no unintended term conflicts between
the specification's usage and the implementation's.

**Phase C -- the full dictionary.** Every term in the specification's 16
rules and the implementation's 290 public API items that is not
compositional. Expect 150--250 publets.

Seeded from **Wiktionary rather than Wikipedia**, which is the better fit
and was not obvious before §6.10. An encyclopedia describes *things*; a
dictionary describes *words* -- senses, part of speech, usage. The
`definitional` class is "a stipulated meaning, described by usage rather
than voted true", and `Publet::term()` parses exactly dictionary shape,
`term (qualifier): meaning`, matching the specification's own
`quantum (adj., physics): ...` example. Wiktionary's numbered senses also
supply the competing-definitions case that §9.2 divergence exists to
detect, at no extra cost. Wikipedia seeds stratum 3 instead, where
describing a thing is what is wanted. Acceptance: no publet in later
strata uses a contested term without declaring it -- this is the lint doing
the work, and it is why P3 must land first.

**Phase D -- phrases.** Non-compositional constructions: "viewpoint-relative
evaluation", "evidence dominance", "declared set", "local-first bounded
domain". These are the ones a reader cannot assemble from the parts.

**Phase E -- algorithms.** One `procedural` publet per algorithm, each
naming its method. Then `empirical` publets for the measured claims (the
cross-architecture digest, the coverage figure, the scenario count), each
citing the script that reproduces it. Acceptance: every empirical claim's
method is a script in the repository that a reader can run, and at least one
claim carries two independent reproductions and reaches `accepted`.

**Phase F -- design choices.** `normative` publets: the composable-utilities
stance, no floating point, Python for functional tests, local-first
retrieval. Each `depends` on the terms it uses, and each carries the
reasoning. They will never be accepted, and the reason why is itself worth a
publet.

**Phase G -- the two overviews.** Documents, not claims: one binding the
technical strata for an implementer, one binding the user-facing strata for
a reader. Requires P5.

**Phase I -- the map.** The deliverable: core concepts, their relations,
and their weights, rendered from the graph rather than written by hand.
Every node carries whose roots produced its weight and the scope of the
claim (§6.21, §11.3). Derivation structure is retained as links to the
descriptive publets and their sources; drafting history does not appear
because it was never composed. Acceptance: every node's weight is
reproducible by a reader who runs the named policy over the published
graph, and no node presents a number without its roots.

**Phase H -- the viewpoint comparison.** Evaluate the whole corpus under
all four policies -- author, Wiktionary, Wikipedia, Rust Reference -- and
publish the result: one graph, four sets of roots, four sets of standings,
with `pub why` naming which roots produced each. Acceptance: at least one
publet whose standing differs materially between viewpoints, with the
difference explained; and, if P6 has landed, at least one term where
subject-scoped trust is what produces the difference. This is the deliverable
that demonstrates R1, and it is what the Wikipedia-derived material is
genuinely for (§6.3).

## 8. Readiness

**Not yet, and the remaining list is short and specific.** What follows
replaces the earlier assessment, which was written before any of the gaps
were closed.

### 8.1 Closed

`pub relate` and `pub annotate` exist, so the porcelain can author
relations and eight annotation kinds rather than two object kinds. Of the
mechanisms the audit found unread: `usage`, `classifies`,
`trusts.subjects`, `affiliated`, `assessment`, `attests` and `timestamped`
are implemented and tested. Independence holds three of its four
conditions plus the same-person link. One unread kind remains and is
argued for removal (§6.24) rather than implementation.

### 8.2 Still blocking

Three items, none large, and the first two are what make the difference
between authoring a corpus and fighting one.

- **P2, term lookup.** Nothing searches by term. At 250 terms this is the
  operation performed most often, and without it authoring publet 200
  means tracking 199 identifiers by hand. The capability already exists
  twice inside the library; it has no command.
- **P3/L2, identifiers counted as quantities.** The linter reads each run
  of digits in a content address as a separate quantitative claim. A
  corpus about this protocol is full of content addresses, so the warning
  would fire on nearly everything and be trained away within a day --
  which is the failure mode that makes an advisory tool worthless.
- **P9, N-way divergence.** The triangulation model of §6.17 asks how four
  sources partition on a term. `compare` answers whether two differ.

**P3/L1** is a contradiction between §5.5 and §5.7 rather than a linter
bug, and it affects four classes rather than one -- including
`attributive`, which is what the seed material is (§6.26). It should be
settled in the specification before the corpus starts, because it is
visible from the first seeded quotation.

### 8.3 Not blocking

Document authoring (P7) is needed only for the two overviews in Phase G.
The remaining absent fields -- `critique.defect`, `critique.omitted`,
`proof-checked.system`, `proof-checked.artifact`, `reproduction.data`,
`resolution.thread_root`, `verdict.effort` -- serve strata the corpus
reaches late or not at all. Independence condition 1 is architectural
(§6.25).

### 8.4 The pattern worth naming

Five consecutive design questions -- the second trust root, a second
lexical source, concept triangulation, partial correctness, and this one --
each landed on a mechanism the specification named and the implementation
did not have. None was found by the test suite. The suite tests statements
containing MUST, and the object-shape tables are where the unimplemented
parts live.

`tools/check-fields.py` now measures this directly, and the count has gone
from seven unread kinds to one. That the count is *measured* is the change
that matters: the earlier claim of 47/47 coverage was true and meant less
than it sounded, and there is now a second number beside it that says what
the first one does not.

## 9. Superseded readiness note

The following was written before any gap was closed and is kept because
the plan should not quietly rewrite its own history.

**The plan is ready. The implementation is further from ready than the plan
assumed when it was written**, and the difference is now measured rather
than estimated.

What changed: §6.22's audit converted P6 from an open-ended suspicion into
a count -- seven unread annotation kinds and fifteen absent fields, as a
lower bound. Phase A is correspondingly larger than P1--P3, because two of
the unread kinds are load-bearing for the corpus rather than incidental to
it. `usage` is the mechanism a `definitional` publet uses to accumulate the
evidence its class is defined by; `classifies` is subject membership. The
concept model of §6.17 and any taxonomy both need them.

What did not change: the strata, the licence framework, the
attribution/quotation distinction, the viewpoint arrangement, and the
patch list's ordering. P1 remains the single blocker for building anything
at all.

The honest summary is that three questions in succession -- the second
trust root, a second lexical source, and concept triangulation -- each
landed on a specified-but-unimplemented mechanism. That is not bad luck.
The conformance suite tests statements containing MUST, and the object
shapes are where the unimplemented parts live. **Phase A should be
resequenced to put the §6.22 triage first**, because every later phase
exercises those paths and discovering the gaps one at a time from inside
the corpus work would be the expensive way to find them.

A schedule should not be committed to until that triage is done. Sizing
the four corpus-blocking items is a day's work; sizing the remainder
honestly requires deciding, per field, whether the specification or the
implementation is wrong.

## 10. Risks and honest limits

**The corpus is single-author, and no key arrangement changes that.**
Stratum 3 cannot honestly reach `accepted` without a second person
reproducing something (§6.2). Adding keys adds keys, not people. Until a
second participant exists the exercise validates *structure* and
*viewpoint-relativity*, not the replication floor, and the corpus should say
so in a publet of its own rather than leave a reader to infer it.

**The seeded viewpoint must never be described as review.** The
organization key is a second grounding, not a second reviewer. Every
interface presenting the two-viewpoint comparison has to say which roots
produced which column, or it recreates exactly the "47 endorsements"
failure §7.1 forbids.

**Self-reference is safe but not free.** Nothing breaks when the system
holds its own definitions -- definitions do not feed evaluation except
through `depends` and the contested-term lint. But a wrong definition in the
corpus is invisible to every mechanical check, because non-truth-apt claims
have no verdict. The dictionary is exactly as reliable as its author.

**The 4096-byte content ceiling** is ample for definitions and tight for
algorithms. Expect some algorithms to decompose into several procedural
publets joined by `depends`, which is the intended shape but is more work
than writing a paragraph.

**This will find drift.** Running `pub-divergence` across the specification's
and the implementation's usage of the same terms is likely to turn up places
where they disagree. That is the point, and it should be budgeted for: the
output of Phase B is partly a list of corrections to make elsewhere.

## 11. Deliberately out of scope

- Extracting publets from source automatically. The value is in the
  judgement about what a term means; a generated corpus would have the
  structure and none of the content.
- Publishing the corpus to a public peer. Local first; syncing is a separate
  decision.
- Replacing the specification or this plan. Those are prose documents for
  linear reading, and a graph is not better at that job.
