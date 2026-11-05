"""Steps for showing whether an object's author signed it (Section 4.4)."""

from __future__ import annotations

import json

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pytest_bdd import given, parsers, scenarios, then, when

from support.objects import cid_of, obj, text
from support.signing import CREATED, bstr

scenarios("../features/porcelain/signature_status.feature")


def _ok(out) -> str:
    assert out.code == 0, out.stderr
    return out.stdout


def _compose(runner, content: str) -> str:
    return _ok(runner.run("pub", "compose", "--class=normative", "--scope=unconditional",
                          f"--content={content}")).split()[0]


@given("a workspace with a key and a claim it composed", target_fixture="ws")
def workspace(runner):
    _ok(runner.run("pub", "init"))
    key = _ok(runner.run("pub", "sign", "--generate-key", "--principal=human")).split()[1]
    return {"key": key, "claim": _compose(runner, "Grow it here.")}


@when("the author signs the claim")
def sign_claim(runner, ws):
    ws["sig"] = _ok(runner.run("pub", "sign", "--purpose=authored",
                               f"--target={ws['claim']}")).split()[0]


@when("a signature by the author over other bytes is filed for the claim")
def bad_signature(runner, ws):
    seed = bytes.fromhex((runner.cwd / ".publet" / "signing.key").read_text().strip())
    value = Ed25519PrivateKey.from_private_bytes(seed).sign(b"pub/v1/sig\x00authored\x00other")
    data = obj("sig", ws["key"], CREATED, [
        ("target", text(ws["claim"])), ("alg", text("ed25519")),
        ("value", bstr(value)), ("purpose", text("authored")),
    ])
    out = runner.run("pub-store", "--store=.publet/objects.redb", "add", stdin=data)
    assert out.code == 0, out.stderr


@when("I compose a second claim and leave it unsigned")
def second_claim(runner, ws):
    ws["second"] = _compose(runner, "Grow it there.")


@when("I read the claim", target_fixture="result")
def read_claim(runner, ws):
    return runner.run("pub", "read", ws["claim"])


@when("I read the claim's signature", target_fixture="result")
def read_signature(runner, ws):
    return runner.run("pub", "read", ws["sig"])


@when("I read the claim from its own file", target_fixture="result")
def read_file(runner, ws):
    data = runner.run("pub-cat", "--store=.publet/objects.redb", ws["claim"]).out
    path = runner.cwd / (cid_of(data).replace(":", "_") + ".cbor")
    path.write_bytes(data)
    return runner.run("pub", "read", str(path))


@when("I write the bundles", target_fixture="result")
def write_bundles(runner):
    return runner.run("pub", "bundle", "--out=bundles")


@then(parsers.parse('it shows "{line}"'))
def shows(result, line: str):
    assert result.code == 0, result.stderr
    assert line in result.stdout, result.stdout


@then(parsers.parse('reading it as JSON gives the signature "{status}"'))
def json_signature(runner, ws, status: str):
    out = json.loads(_ok(runner.run("pub", "read", "--json", ws["claim"])))
    assert out["signature"] == status, out["signature"]


def _summary(runner, cid: str) -> dict:
    return json.loads((runner.cwd / "bundles" / "o" / f"{cid}.json").read_text())["summary"]


@then(parsers.parse('the claim\'s bundle gives the signature "{status}"'))
def bundle_claim(runner, ws, status: str):
    assert _summary(runner, ws["claim"])["signature"] == status


@then(parsers.parse('the second claim\'s bundle gives the signature "{status}"'))
def bundle_second(runner, ws, status: str):
    assert _summary(runner, ws["second"])["signature"] == status
