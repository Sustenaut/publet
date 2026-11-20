"""Steps for the date pub gives the keys and signatures it makes."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/porcelain/created.feature")


def _ok(out) -> str:
    assert out.code == 0, out.stderr
    return out.stdout


def _created(runner, cid: str) -> str:
    return json.loads(_ok(runner.run("pub", "read", cid, "--json")))["object"]["created"]


def _recent(created: str) -> None:
    then_ = datetime.strptime(created, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    assert abs((datetime.now(UTC) - then_).total_seconds()) < 60, created


@given("a workspace to sign in", target_fixture="ws")
def workspace(runner):
    _ok(runner.run("pub", "init"))
    return {}


@given("pub's dates are not pinned")
def unpinned(monkeypatch):
    monkeypatch.delenv("PUB_CREATED", raising=False)


@given(parsers.parse('pub\'s dates are pinned to "{instant}"'))
def pinned(monkeypatch, instant):
    monkeypatch.setenv("PUB_CREATED", instant)


@given("a key and an object to sign")
def key_and_object(runner, ws):
    _ok(runner.run("pub", "sign", "--generate-key", "--principal=human"))
    ws["target"] = _ok(runner.run("pub", "compose", "--class=definitional", "--scope=unconditional",
                                  "--content=A term means this.")).split()[0]


@when("I make a key", target_fixture="result")
def make_key(runner, ws):
    result = runner.act("pub", "sign", "--generate-key", "--principal=human")
    ws["key"] = result.stdout.split()[1] if result.code == 0 else None
    return result


@when(parsers.parse('I make a key with "{flag}"'), target_fixture="result")
def make_key_with(runner, ws, flag):
    result = runner.act("pub", "sign", "--generate-key", "--principal=human", flag)
    ws["key"] = result.stdout.split()[1] if result.code == 0 else None
    return result


@when("I sign the object", target_fixture="result")
def sign_object(runner, ws):
    result = runner.act("pub", "sign", "--purpose=authored", f"--target={ws['target']}")
    ws["sig"] = result.stdout.split()[0] if result.code == 0 else None
    return result


@then("the key is dated within a minute of now")
def key_now(runner, ws):
    _recent(_created(runner, ws["key"]))


@then(parsers.parse('the key is dated "{instant}"'))
def key_dated(runner, ws, instant):
    assert _created(runner, ws["key"]) == instant


@then("the signature is dated within a minute of now")
def sig_now(runner, ws):
    _recent(_created(runner, ws["sig"]))
