"""Steps for the rules implemented after the coverage report named them.

Each of these covers a normative statement the report listed as untested,
and each turned out to be untested because it was also unimplemented.
"""

from __future__ import annotations

import json
from pathlib import Path

from pytest_bdd import given, parsers, scenarios, then, when

from support.signing import Key
from support.objects import (
    author_key, cbor_map, cid_of, head, obj, publet, relation, text, uint,
    write_store,
)

scenarios("../features/conformance/evidence_required.feature")
scenarios("../features/conformance/redundancy.feature")
scenarios("../features/conformance/human_signatory.feature")

KA = author_key("K_a")


def arr(items):
    return head(4, len(items)) + b"".join(items)


def key_object(seed: str, principal: str | None) -> bytes:
    body = [("alg", text("ed25519")), ("pubkey", head(2, 4) + b"\x00\x01\x02\x03")]
    if principal is not None:
        body.append(("principal", text(principal)))
    return obj("key", author_key(seed), "2026-09-12T00:00:00Z", body)


# --- 5.5 and 5.4 -----------------------------------------------------------

@given("an empirical publet naming no method", target_fixture="store")
def empirical_without_method(tmp_path):
    data = obj("claim.prose", KA, "2026-09-12T10:00:00Z", [
        ("class", text("empirical")),
        ("lang", text("en")),
        ("content", text("the rate fell")),
        ("depends", arr([])),
    ])
    write_store(tmp_path, [data])
    return {"dir": tmp_path}


@given("an empirical publet naming a method", target_fixture="store")
def empirical_with_method(tmp_path):
    write_store(tmp_path, [
        publet(KA, "2026-09-12T10:00:00Z", "empirical", "the rate fell")
    ])
    return {"dir": tmp_path}


@given("two publets that presuppose each other", target_fixture="store")
def mutual_dependency(tmp_path):
    a = publet(KA, "2026-09-12T10:00:00Z", "definitional", "a: defined by b")
    b = publet(KA, "2026-09-12T10:00:01Z", "definitional", "b: defined by a",
               [cid_of(a)])
    # The in-body reference can only point backwards, so the cycle is closed
    # by a relation, which is the only place one can be created (Section 6).
    rel = relation(KA, "2026-09-12T10:01:00Z", "depends", cid_of(a), cid_of(b))
    write_store(tmp_path, [a, b, rel])
    return {"dir": tmp_path, "target": cid_of(a)}


@given(parsers.parse('a "{cls}" publet'), target_fixture="store")
def classed_publet(tmp_path, cls: str):
    content = "term: a meaning" if cls == "definitional" else "an assertion"
    write_store(tmp_path, [publet(KA, "2026-09-12T10:00:00Z", cls, content)])
    return {"dir": tmp_path}


@when("I ask for the dependency closure", target_fixture="result")
def dependency_closure(runner, store):
    return runner.run("pub-closure", f"--dir={store['dir']}", store["target"])


# --- 7.3 redundancy --------------------------------------------------------

def _disputed_workspace(runner, *, resolution_outcome, cover_grounds):
    """A claim, an argued dispute, and optionally a resolution covering it."""
    def run(*args: str) -> str:
        proc = runner.run("pub", *args)
        assert proc.code == 0, proc.stderr
        return proc.stdout

    # The author's own key declares a human principal, for its verdicts and
    # reproductions to carry, and the policy trusts it.
    run("init")
    author = run("sign", "--generate-key", "--principal=human").split()[1]
    run("policy", f"--root={author}")

    def add(data: bytes) -> str:
        proc = runner.run("pub-store", "--store=.publet/objects.redb", "add", stdin=data)
        assert proc.code == 0, proc.stderr
        cid = proc.stdout.strip()
        # Section 4.4: evidence counts only when its author signed it.
        run("sign", "--purpose=authored", f"--target={cid}")
        return cid

    claim = publet(author, "2026-09-12T10:00:00Z", "empirical", "the claim")
    grounds = publet(author, "2026-09-12T11:00:00Z", "empirical", "the grounds")
    add(claim)
    add(grounds)
    add(relation(author, "2026-09-12T11:00:01Z", "disputes",
                 cid_of(grounds), cid_of(claim)))
    add(obj("claim.annotation", author, "2026-09-12T11:30:00Z", [
        ("kind", text("verdict")),
        ("target", text(cid_of(claim))),
        ("value", cbor_map([("finding", text("affirm"))])),
    ]))

    if resolution_outcome is not None:
        covered = [text(cid_of(grounds))] if cover_grounds else []
        add(obj("claim.annotation", author, "2026-09-12T12:00:00Z", [
            ("kind", text("resolution")),
            ("target", text(cid_of(claim))),
            ("value", cbor_map([
                ("outcome", text(resolution_outcome)),
                ("grounds", arr(covered)),
            ])),
        ]))

    return {"claim": cid_of(claim)}


@given("a claim disputed on grounds a sustained resolution already covers",
       target_fixture="ws")
def dispute_redundant(runner):
    return _disputed_workspace(runner,
                               resolution_outcome="sustained", cover_grounds=True)


@given("a claim disputed on grounds no resolution covers", target_fixture="ws")
def dispute_novel(runner):
    return _disputed_workspace(runner,
                               resolution_outcome=None, cover_grounds=False)


@given("a claim whose dispute is covered only by a no-consensus resolution",
       target_fixture="ws")
def dispute_no_consensus(runner):
    return _disputed_workspace(runner,
                               resolution_outcome="no-consensus",
                               cover_grounds=True)


# --- 7.2 and 10.1 ----------------------------------------------------------

def _reproduced_workspace(runner, principal: str):
    ws = _disputed_workspace(runner,
                             resolution_outcome=None, cover_grounds=False)
    config = (runner.cwd / ".publet/config").read_text()
    author = [l.split("=", 1)[1] for l in config.splitlines()
              if l.startswith("author=")][0]

    def add(data: bytes):
        runner.run("pub-store", "--store=.publet/objects.redb", "add", stdin=data)

    # Two reproducers, each with their own key declaring the principal
    # under test. Section 11.4 defines independence between signers, so a
    # single key filing twice would be one party, not two -- which is what
    # this fixture used to do, and why it agreed with an implementation
    # that counted the same person twice.
    for i in range(2):
        reproducer = Key(f"reproducer-{principal}-{i}", principal)
        add(reproducer.object)
        filed = obj("claim.annotation", reproducer.cid, f"2026-09-12T13:0{i}:00Z", [
            ("kind", text("settled")),
            ("target", text(ws["claim"])),
            ("value", cbor_map([("outcome", text("consistent"))])),
        ])
        add(filed)
        add(reproducer.sign(filed))
    return ws


def _one_signer_twice(runner):
    """One human filing the same reproduction twice."""
    ws = _disputed_workspace(runner,
                             resolution_outcome=None, cover_grounds=False)

    def add(data: bytes):
        runner.run("pub-store", "--store=.publet/objects.redb", "add", stdin=data)

    reproducer = Key("lone-reproducer")
    add(reproducer.object)
    for i in range(2):
        filed = obj("claim.annotation", reproducer.cid, f"2026-09-12T14:0{i}:00Z", [
            ("kind", text("settled")),
            ("target", text(ws["claim"])),
            ("value", cbor_map([("outcome", text("consistent"))])),
        ])
        add(filed)
        add(reproducer.sign(filed))
    return ws


@given("a claim with two reproductions from human principals",
       target_fixture="ws")
def reproductions_human(runner):
    return _reproduced_workspace(runner, "human")


@given("a claim reproduced twice by one person", target_fixture="ws")
def reproduced_twice_by_one(runner):
    return _one_signer_twice(runner)


@given("a claim with two reproductions from an organization",
       target_fixture="ws")
def reproductions_organization(runner):
    return _reproduced_workspace(runner, "organization")


@given("a key object declaring no principal", target_fixture="store")
def key_without_principal(tmp_path):
    # A key that declines to say what it is cannot have the rules that turn
    # on that applied to it. The object itself is structurally valid, so it
    # loads; the refusal belongs to the typed view, exercised in the library
    # tests.
    write_store(tmp_path, [key_object("anonymous", None)])
    return {"dir": tmp_path}


@when("I ask why", target_fixture="result")
def ask_why_ws(runner, ws):
    return runner.act("pub", "why", ws["claim"])


def _out(result) -> str:
    return result.stdout + result.stderr


@then("the divergence factor is above zero")
def delta_above_zero(result):
    body = _out(result)
    line = [l for l in body.splitlines() if "delta" in l]
    assert line, body
    assert float(line[0].split()[-1]) > 0, line


@then(parsers.parse("the independent consistent count is {n:d}"))
def independent_count(result, n: int):
    body = _out(result)
    line = [l for l in body.splitlines() if "independent consistent" in l]
    assert line, body
    assert int(line[0].split()[2]) == n, line
