"""Steps for counting only signed evidence (Section 4.4)."""

from __future__ import annotations

import re

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pytest_bdd import given, parsers, scenarios, then, when

from support.objects import cid_of, obj, text
from support.signing import CREATED, Key, bstr

scenarios("../features/conformance/evaluation_signatures.feature")


def _ok(out):
    assert out.code == 0, out.stderr
    return out.stdout.decode() if isinstance(out.stdout, bytes) else out.stdout


@given("a workspace whose trusted key affirms an empirical claim", target_fixture="ws")
def workspace(runner):
    _ok(runner.run("pub", "init"))
    key = _ok(runner.run("pub", "sign", "--generate-key", "--principal=human")).split()[1]
    _ok(runner.run("pub", "policy", f"--root={key}"))
    claim = _ok(runner.run("pub", "compose", "--class=empirical", "--scope=unconditional",
                           "--content=The rate fell.", f"--method={cid_of(b'a protocol')}")).split()[0]
    affirmation = _ok(runner.run("pub", "annotate", "--scope=unconditional", "--kind=verdict",
                                 f"--target={claim}", "--finding=affirm")).split()[0]
    return {"key": key, "claim": claim, "affirmation": affirmation}


def _add(runner, data: bytes) -> None:
    out = runner.run("pub-store", "--store=.publet/objects.redb", "add", stdin=data)
    assert out.code == 0, out.stderr


def _bytes_of(runner, cid: str) -> bytes:
    out = runner.run("pub-cat", "--store=.publet/objects.redb", cid)
    assert out.code == 0, out.stderr
    return out.out


@when("the affirmation is signed by its author")
def signed_by_author(runner, ws):
    _ok(runner.run("pub", "sign", "--purpose=authored", f"--target={ws['affirmation']}"))


@when("the affirmation is left unsigned")
def left_unsigned(ws):
    pass


@when("the affirmation is signed by another key")
def signed_by_other(runner, ws):
    other = Key("someone else")
    _add(runner, other.object)
    _add(runner, other.sign(_bytes_of(runner, ws["affirmation"])))


@when("the affirmation is signed with an altered signature")
def signed_altered(runner, ws):
    # The workspace's own secret, read as `pub sign` keeps it, signing other
    # bytes than the affirmation's: a signature by the right key that does
    # not verify for this object.
    seed = bytes.fromhex((runner.cwd / ".publet" / "signing.key").read_text().strip())
    private = Ed25519PrivateKey.from_private_bytes(seed)
    value = private.sign(b"pub/v1/sig\x00authored\x00" + b"other bytes")
    _add(runner, obj("sig", ws["key"], CREATED, [
        ("target", text(ws["affirmation"])), ("alg", text("ed25519")),
        ("value", bstr(value)), ("purpose", text("authored")),
    ]))


@when("I ask why the claim stands as it does", target_fixture="result")
def ask_why(runner, ws):
    return runner.run("pub", "why", ws["claim"])


def _affirm(result) -> str:
    assert result.code == 0, result.stderr
    match = re.search(r"^\s*affirm\s+(\S+)", result.stdout, re.M)
    assert match, result.stdout
    return match.group(1)


@then("the affirmation weighs on the claim")
def weighs(result):
    assert _affirm(result) != "0.000000", result.stdout


@then("the affirmation does not weigh on the claim")
def does_not_weigh(result):
    assert _affirm(result) == "0.000000", result.stdout


@then("no evidence is reported as not counted")
def none_reported(result):
    assert "not counted" not in result.stderr, result.stderr


@then("the affirmation is reported as not counted")
def reported(result, ws):
    assert f"not counted: {ws['affirmation']}" in result.stderr, result.stderr
