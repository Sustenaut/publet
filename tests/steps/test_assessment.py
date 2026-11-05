"""Steps for assessments (Section 5.2).

An assessment carries the partial correctness a weight cannot: a claim
sound where its scope says and misleading outside it. The protocol has no
number for that, and naming the conditions says more than one would.
"""

from __future__ import annotations

from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/conformance/assessment.feature")

CONTENT = "hash function: a function mapping data of arbitrary size to fixed-size values"
GROUNDS = "omits collision resistance, so it misleads in a security context"


def _keyed(runner) -> None:
    """Give the workspace a key its policy trusts, as `pub sign` makes one."""
    out = runner.run("pub", "sign", "--generate-key", "--principal=human")
    assert out.code == 0, out.stderr
    key = out.stdout.split()[1]
    assert runner.run("pub", "policy", f"--root={key}").code == 0


def _annotate(runner, *args: str):
    """`pub annotate`, then sign what it made: an annotation counts only when
    its author signed it (Section 4.4)."""
    out = runner.run("pub", "annotate", *args)
    if out.code == 0:
        signed = runner.run("pub", "sign", "--purpose=authored",
                            f"--target={out.stdout.split()[0]}")
        assert signed.code == 0, signed.stderr
    return out


@given("a workspace with a scoped definition", target_fixture="defn")
def scoped_definition(runner, tmp_path):
    assert runner.run("pub", "init").code == 0
    _keyed(runner)
    out = runner.run("pub", "compose", "--class=definitional",
                     "--scope=non-cryptographic contexts", f"--content={CONTENT}")
    assert out.code == 0, out.stderr
    cid = out.stdout.strip()
    before = runner.run("pub", "why", cid)
    assert before.code == 0, before.stderr
    return {"cid": cid, "weights": _weights(before.stdout)}


def _weights(body: str) -> list[str]:
    block = body.split("weight", 1)[1].split("evidence", 1)[0]
    return [line.strip() for line in block.splitlines() if line.strip()]


@when(parsers.parse('I assess it as "{verdict}"'), target_fixture="result")
def assess(runner, defn, verdict: str):
    return _annotate(runner, "--scope=unconditional", "--kind=assessment",
                      f"--target={defn['cid']}", f"--verdict={verdict}",
                      f"--grounds={GROUNDS}")


@when("I assess it with no grounds", target_fixture="result")
def assess_no_basis(runner, defn):
    return _annotate(runner, "--scope=unconditional", "--kind=assessment",
                      f"--target={defn['cid']}", "--verdict=sound-in-scope")


@then("asking why shows the judgement")
def shows_judgement(runner, defn):
    body = runner.run("pub", "why", defn["cid"]).stdout
    assert "sound-in-scope" in body, body
    assert GROUNDS in body, body


@then("asking why still reports the class not truth-apt")
def still_not_truth_apt(runner, defn):
    # The judgement is displayed and decides nothing. If filing one could
    # move the result, it would be a verdict wearing another name.
    body = runner.run("pub", "why", defn["cid"]).stdout
    assert "not-truth-apt" in body, body


@then("the weights are unchanged")
def weights_unchanged(runner, defn):
    body = runner.run("pub", "why", defn["cid"]).stdout
    assert _weights(body) == defn["weights"], body
