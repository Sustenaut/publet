"""Steps for the optional layers.

These exercise rules rather than mechanisms. The cryptography of a
personhood scheme and the consensus of a ledger are properties of whatever
is plugged in; what the protocol requires, and what is asserted here, is how
those things may be treated once present.

Everything runs the shipped binaries, like the rest of the suite. A scenario
that asserted "the Rust test passes" would be unrunnable against a second
implementation, which is the whole point of writing these in Gherkin.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from support.objects import (
    assumption, attestation, author_key, bounty, cid_of, publet, triage,
    write_store,
)

scenarios("../features/conformance/settlement.feature")
scenarios("../features/conformance/personhood.feature")
scenarios("../features/conformance/assumption.feature")

KA = author_key("K_a")
KB = author_key("K_b")
POLICY = cid_of(b"a settlement policy")
TARGET = cid_of(b"the object under review")


def write_one(tmp_path: Path, data: bytes, name: str) -> Path:
    path = tmp_path / name
    path.write_bytes(data)
    return path


# --- settlement ------------------------------------------------------------

@given("this build carries settlement")
def carries_settlement(bin_dir):
    # A deployment may omit settlement entirely (Section 12.1), and ship no
    # settlement binary: there is then nothing here to test.
    if not (bin_dir / "pub-settle").exists():
        pytest.skip("settlement is not present in this build")


@given("a bounty naming no policy")
def bounty_no_policy(tmp_path):
    write_one(tmp_path, bounty(KA, "2026-09-12T10:00:00Z", TARGET, None, 6000), "bounty.cbor")


@given(parsers.parse("a bounty with a review share of {share:d} basis points"))
def bounty_share(tmp_path, share: int):
    write_one(tmp_path, bounty(KA, "2026-09-12T10:00:00Z", TARGET, POLICY, share), "bounty.cbor")


@then("each line it prints names what it forbids and why")
def each_prohibition_explained(result):
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    assert len(rows) >= 4, rows
    for row in rows:
        assert row["forbids"], row
        assert len(row["reason"].split()) >= 5, row


def ledger_methods() -> str:
    """The trait's whole surface, read from the source that defines it: one
    method signature a line.

    A rule about what an interface *cannot express* is a rule about the
    interface, so the interface is what gets read. There is no run-time
    observation that could establish the absence of a method.
    """
    path = (Path(__file__).resolve().parents[2]
            / "crates/publet-settle/src/ledger.rs")
    if not path.exists():
        # A deployment may omit settlement entirely (Section 12.1). There is
        # then no trait to read, and no rule about it to break.
        pytest.skip("settlement is not present in this build")
    source = path.read_text()
    body = source.split("pub trait Ledger {", 1)[1].split("\n}", 1)[0]
    methods = [line.strip() for line in body.splitlines() if line.strip().startswith("fn ")]
    assert methods, "the ledger trait declares no method"
    return "\n".join(methods)


@when("I read the methods of the ledger interface")
def read_ledger_methods(pubtest_ctx):
    pubtest_ctx.attempt(ledger_methods)


# --- personhood ------------------------------------------------------------

@then("their declared anonymity differs")
def anonymity_differs(result):
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    assert len(rows) == 2, rows
    claims = [tuple(sorted((k, v) for k, v in row.items() if k != "scheme"))
              for row in rows]
    assert claims[0] != claims[1], rows


@given("a verified personhood attestation in a scope", target_fixture="person")
def first_attestation(tmp_path):
    nullifier = b"\x11\x22\x33"
    path = write_one(
        tmp_path,
        attestation(KA, "2026-09-12T10:00:00Z", cid_of(b"key one"),
                    "demo-unlinkable", "domain-a", nullifier),
        "first.cbor",
    )
    return {"dir": tmp_path, "first": path, "nullifier": nullifier}


@when("a second key presents the same nullifier in that scope",
      target_fixture="result")
def same_nullifier_same_scope(runner, person):
    second = write_one(
        person["dir"],
        attestation(KB, "2026-09-12T10:01:00Z", cid_of(b"key two"),
                    "demo-unlinkable", "domain-a", person["nullifier"]),
        "second.cbor",
    )
    return runner.run("pub-person", "--scheme=demo-unlinkable",
                      f"--attest={person['first']}", f"--attest={second}")


@when("the same person presents in a different scope", target_fixture="result")
def same_nullifier_other_scope(runner, person):
    # A different scope means a different nullifier for the same person:
    # that is what unlinkability across scopes *is*. Presenting the same
    # bytes in another scope would be the scheme failing, not the person.
    second = write_one(
        person["dir"],
        attestation(KB, "2026-09-12T10:01:00Z", cid_of(b"key two"),
                    "demo-unlinkable", "domain-b", b"\x44\x55\x66"),
        "second.cbor",
    )
    return runner.run("pub-person", "--scheme=demo-unlinkable",
                      f"--attest={person['first']}", f"--attest={second}")


@then("it is accepted")
def accepted(result):
    assert result.code == 0, result.stderr
    assert len(result.stdout.splitlines()) == 2, result.stdout


@given("a workspace", target_fixture="workspace_dir")
def bare_workspace(runner, tmp_path):
    out = runner.run("pub", "init")
    assert out.code == 0, out.stderr
    return tmp_path


@when("I compose a claim", target_fixture="result")
def compose_without_personhood(runner, workspace_dir):
    return runner.run("pub", "compose", "--class=definitional",
                      "--content=a term: a meaning", "--scope=unconditional")


@then("no personhood attestation was required")
def no_attestation_required(result):
    body = result.stdout + result.stderr
    assert "personhood" not in body.lower(), body
    assert body.strip().startswith("pub:sha2-256:"), body


# --- assumption and triage -------------------------------------------------

@given("a key assuming accountability for another", target_fixture="store")
def one_assumption(tmp_path):
    pseudonym = author_key("K_p")
    own = publet(pseudonym, "2026-09-12T09:00:00Z", "definitional",
                 "a term: a meaning")
    write_store(tmp_path, [
        own,
        assumption(KA, "2026-09-12T10:00:00Z", pseudonym),
    ])
    return {"dir": tmp_path, "assumer": KA, "assumed": pseudonym,
            "publet": cid_of(own)}


@given("a key assuming accountability for three others", target_fixture="store")
def three_assumptions(tmp_path):
    objects = []
    for n in range(3):
        pseudonym = author_key(f"K_p{n}")
        objects.append(
            assumption(KA, f"2026-09-12T10:0{n}:00Z", pseudonym))
    write_store(tmp_path, objects)
    return {"dir": tmp_path, "assumer": KA}


@when("I list the claims authored by the assumed key", target_fixture="result")
def list_by_assumed(runner, store):
    return runner.act("pub-ls", f"--dir={store['dir']}", "--type=claim.prose",
                      f"--author={store['assumed']}")


@when("I list the claims authored by the assumer", target_fixture="result")
def list_by_assumer(runner, store):
    # Vouching moves no authorship: the assumer has staked their standing,
    # not taken the byline.
    return runner.act("pub-ls", f"--dir={store['dir']}", "--type=claim.prose",
                      f"--author={store['assumer']}")


@then("it lists only the assumed key's own publet")
def lists_own_publet(result, store):
    assert result.stdout.split() == [store["publet"]], result.stdout


@when("I list the assumptions the assumer holds", target_fixture="result")
def list_assumptions(runner, store):
    return runner.act("pub-ann", f"--dir={store['dir']}",
                      f"--assumptions-by={store['assumer']}")


def _rows(result) -> list[dict]:
    return [json.loads(line) for line in result.stdout.splitlines() if line.strip()]


@then(parsers.parse("it lists {n:d} {noun}, each of a different key"))
def assumption_count(result, n: int, noun: str):
    rows = _rows(result)
    assert len(rows) == n, rows
    assert len({row["assumed"] for row in rows}) == n, rows


@then("each assumption it lists records only the two keys and the grounds")
def no_identity_recorded(result):
    # Two keys and the grounds. A field for who holds the assumed key is the
    # one thing the record must never carry.
    for row in _rows(result):
        assert set(row) == {"assumer", "assumed", "grounds"}, row


@given("a claim with a standing", target_fixture="workspace")
def claim_with_standing(runner, tmp_path):
    assert runner.run("pub", "init").code == 0
    out = runner.run("pub", "compose", "--class=definitional",
                     "--content=a term: a meaning", "--scope=unconditional")
    assert out.code == 0, out.stderr
    claim = out.stdout.strip()
    why = runner.run("pub", "why", claim)
    assert why.code == 0, why.stderr
    return {"dir": tmp_path, "target": claim, "before": why.stdout}


@given("a triage annotation calling it redundant")
def add_triage(runner, workspace):
    data = triage(KB, "2026-09-12T10:00:00Z", workspace["target"],
                  "redundant-with")
    added = runner.run("pub-store", "--store=.publet/objects.redb", "add",
                       stdin=data)
    assert added.code == 0, added.stderr
    # The comparison below proves nothing unless the annotation landed.
    held = runner.run("pub-store", "--store=.publet/objects.redb", "list")
    assert held.code == 0, held.stderr
    assert added.stdout.strip() in held.stdout, held.stdout


@when("I ask why again", target_fixture="result")
def ask_why_again(runner, workspace):
    return runner.act("pub", "why", workspace["target"])


@then("the standing is unchanged")
def standing_unchanged(result, workspace):
    assert result.stdout == workspace["before"], (workspace["before"], result.stdout)


@given("a triage annotation with no engine declared", target_fixture="store")
def triage_without_engine(tmp_path):
    claim = publet(KA, "2026-09-12T09:00:00Z", "definitional",
                   "a term: a meaning")
    write_store(tmp_path, [
        claim,
        triage(KB, "2026-09-12T10:00:00Z", cid_of(claim), "redundant-with",
               engine=None),
    ])
    return {"dir": tmp_path, "target": cid_of(claim)}


@when("I list the triage findings on the claim", target_fixture="result")
def list_triage(runner, store):
    return runner.act("pub-ann", f"--dir={store['dir']}", f"--triage-of={store['target']}")
