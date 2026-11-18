"""Steps for the porcelain features.

These drive `pub` from a real working directory, because a workspace is a
directory and the commands resolve it from where they are run. Nothing here
reaches into the store; what a user would see is what is asserted.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from support.objects import author_key, cbor_map, cid_of, head, obj, publet, text, uint

scenarios("../features/porcelain/init.feature")
scenarios("../features/porcelain/read.feature")
scenarios("../features/porcelain/why.feature")
scenarios("../features/porcelain/compose.feature")
scenarios("../features/scenarios/stale_basis.feature")
scenarios("../features/scenarios/privacy_modes.feature")
scenarios("../features/conformance/disclosure.feature")
scenarios("../features/conformance/counts.feature")

COHORT = (
    "In the 2031 cohort (n=4,182), daily supplementation with compound X "
    "reduced 12-month relapse incidence from 18.4% to 11.9%."
)


class Pub:
    """Run `pub` in a working directory, as a user would."""

    def __init__(self, runner):
        self.runner = runner
        self.cwd = runner.cwd

    def run(self, *args: str):
        return self.runner.run("pub", *args)

    def add(self, data: bytes) -> str:
        proc = self.runner.run("pub-store", "--store=.publet/objects.redb", "add", stdin=data)
        assert proc.code == 0, proc.stderr
        return proc.stdout.strip()


def text_of(proc) -> str:
    return proc.stdout + proc.stderr


@given("an empty directory", target_fixture="pub")
def empty_dir(runner):
    return Pub(runner)


@given("a workspace", target_fixture="pub")
def workspace(runner):
    p = Pub(runner)
    assert p.run("init").returncode == 0
    return p


@given("a workspace containing the cohort claim", target_fixture="pub")
def workspace_with_claim(runner):
    p = Pub(runner)
    assert p.run("init").returncode == 0
    # A key the policy trusts, so the affirmations below can be signed and
    # count (Section 4.4).
    key = p.run("sign", "--generate-key", "--principal=human").stdout.split()[1]
    assert p.run("policy", f"--root={key}").returncode == 0
    out = p.run(
        "compose", "--class=empirical", f"--content={COHORT}",
        "--scope=adults 40-65, single-centre, unblinded",
        f"--method={cid_of(b'the trial protocol')}",
    )
    assert out.returncode == 0, text_of(out)
    p.claim = out.stdout.strip()
    return p


@given("fifty trusted keys affirming the claim")
def fifty_affirmations(pub):
    # The author's own key is the only trust root a fresh workspace has, so
    # the affirmations come from it: the point is that weight alone, however
    # large, does not reach `accepted` without replication.
    author = (Path(pub.cwd) / ".publet/config").read_text()
    author_cid = [l.split("=", 1)[1] for l in author.splitlines()
                  if l.startswith("author=")][0]
    value = cbor_map([("finding", text("affirm"))])
    for i in range(50):
        ann = obj("claim.annotation", author_cid, f"2026-09-12T12:{i:02d}:00Z", [
            ("kind", text("verdict")),
            ("target", text(pub.claim)),
            ("value", value),
        ])
        pub.add(ann)
        # Section 4.4: an affirmation counts only when its author signed it.
        signed = pub.run("sign", "--purpose=authored", f"--target={cid_of(ann)}")
        assert signed.returncode == 0, text_of(signed)


def _author_of(pub) -> str:
    config = (Path(pub.cwd) / ".publet/config").read_text()
    return [l.split("=", 1)[1] for l in config.splitlines()
            if l.startswith("author=")][0]


def _arr(items):
    return head(4, len(items)) + b"".join(items)


def _publet(author, created, cls, content, depends=()):
    body = [
        ("class", text(cls)),
        ("lang", text("en")),
        ("content", text(content)),
        ("scope", cbor_map([("domain", text("unconditional"))])),
        ("depends", _arr([text(d) for d in depends])),
    ]
    # Section 5.5: an empirical claim must name a method others can execute.
    if cls == "empirical":
        body.append(("evidence", _arr([cbor_map([
            ("kind", text("claim")),
            ("role", text("method")),
            ("ref", text(cid_of(b"a protocol"))),
        ])])))
    return obj("claim.prose", author, created, body)


def _relation(author, created, kind, frm, to):
    return obj("claim.relation", author, created, [
        ("kind", text(kind)), ("from", text(frm)), ("to", text(to)),
    ])


@given("a workspace where a claim has been superseded twice",
       target_fixture="pub")
def superseded_twice(runner):
    # Two authors each supersede the same claim. The lineage branches, which
    # is permitted; the proposal should say so rather than refuse.
    p = Pub(runner)
    assert p.run("init").returncode == 0
    a = _author_of(p)

    original = _publet(a, "2026-09-12T10:00:00Z", "empirical", "the original claim")
    first = _publet(a, "2026-09-12T11:00:00Z", "empirical", "the first successor")
    second = _publet(a, "2026-09-12T12:00:00Z", "empirical", "the second successor")
    for data in (original, first, second):
        p.add(data)
    p.add(_relation(a, "2026-09-12T11:00:01Z", "supersedes",
                    cid_of(first), cid_of(original)))
    p.add(_relation(a, "2026-09-12T12:00:01Z", "supersedes",
                    cid_of(second), cid_of(original)))
    p.target = cid_of(second)
    return p


@given("a workspace where a claim depends on an outdated definition",
       target_fixture="pub")
def depends_on_outdated(runner):
    p = Pub(runner)
    assert p.run("init").returncode == 0
    a = _author_of(p)

    old = _publet(a, "2026-09-12T08:00:00Z", "definitional",
                  "relapse: a return of symptoms")
    new = _publet(a, "2026-09-12T09:00:00Z", "definitional",
                  "relapse: a return of symptoms meeting the stated threshold")
    claim = _publet(a, "2026-09-12T10:00:00Z", "empirical",
                    "relapse fell", [cid_of(old)])
    for data in (old, new, claim):
        p.add(data)
    p.add(_relation(a, "2026-09-12T09:00:01Z", "supersedes",
                    cid_of(new), cid_of(old)))
    p.target = cid_of(claim)
    return p


@given("a workspace where a dispute targets a resolved question",
       target_fixture="pub")
def dispute_already_resolved(runner):
    p = Pub(runner)
    assert p.run("init").returncode == 0
    a = _author_of(p)

    claim = _publet(a, "2026-09-12T10:00:00Z", "empirical", "the claim")
    grounds = _publet(a, "2026-09-12T11:00:00Z", "empirical", "the grounds")
    for data in (claim, grounds):
        p.add(data)
    p.add(_relation(a, "2026-09-12T11:00:01Z", "disputes",
                    cid_of(grounds), cid_of(claim)))
    p.add(obj("claim.annotation", a, "2026-09-12T11:30:00Z", [
        ("kind", text("resolution")),
        ("target", text(cid_of(claim))),
        ("value", cbor_map([("outcome", text("sustained"))])),
    ]))
    p.target = cid_of(grounds)
    return p


@when("I propose the second successor", target_fixture="result")
@when("I propose that claim", target_fixture="result")
@when("I propose the dispute", target_fixture="result")
def propose_target(pub):
    return pub.run("propose", pub.target)


@when(parsers.parse('I run "{command}" on any identifier'), target_fixture="result")
def run_on_identifier(pub, command: str):
    return pub.run(*command.split()[1:], cid_of(b"anything"))


@when("I read the claim", target_fixture="result")
def read_claim(pub):
    return pub.run("read", pub.claim)


@given("a workspace with two claims and a relation between them", target_fixture="pub")
def workspace_with_relation(runner):
    p = Pub(runner)
    assert p.run("init").returncode == 0
    a = p.run("compose", "--class=definitional", "--scope=unconditional",
             "--content=alpha: the first thing").stdout.strip()
    b = p.run("compose", "--class=definitional", "--scope=unconditional",
             "--content=beta: the second thing").stdout.strip()
    rel = p.run("relate", "--scope=unconditional", "--kind=depends", f"--from={a}", f"--to={b}",
               "--aspect=construction")
    assert rel.returncode == 0, text_of(rel)
    p.relation = rel.stdout.strip()
    return p


@when("I read the relation", target_fixture="result")
def read_relation(pub):
    return pub.run("read", pub.relation)


@given("a workspace with a claim and a usage annotation on it", target_fixture="pub")
def workspace_with_annotation(runner):
    p = Pub(runner)
    assert p.run("init").returncode == 0
    a = p.run("compose", "--class=definitional", "--scope=unconditional",
             "--content=gamma: the third thing").stdout.strip()
    ann = p.run("annotate", "--scope=unconditional", "--kind=usage", f"--target={a}",
               "--source=an external reference", "--locator=section 2")
    assert ann.returncode == 0, text_of(ann)
    p.annotation = ann.stdout.strip()
    return p


@given("a workspace with an attributive claim and a provenance verdict on it", target_fixture="pub")
def workspace_with_verdict(runner):
    p = Pub(runner)
    assert p.run("init").returncode == 0
    a = p.run("compose", "--class=attributive", "--scope=unconditional",
             "--content=Smith (2020) reports that the pump uses 26.4 kWh a day.").stdout.strip()
    ann = p.run("annotate", "--scope=unconditional", "--kind=verdict", f"--target={a}",
               "--finding=affirm", "--aspect=provenance")
    assert ann.returncode == 0, text_of(ann)
    p.annotation = ann.stdout.strip()
    return p


@when("I read the annotation", target_fixture="result")
def read_annotation(pub):
    return pub.run("read", pub.annotation)


@when("I ask why", target_fixture="result")
def ask_why(pub):
    return pub.run("why", pub.claim)


@when("I compose a claim with no scope", target_fixture="result")
def compose_no_scope(pub):
    return pub.run("compose", "--class=empirical", "--content=a claim",
                   f"--method={cid_of(b'a protocol')}")


@when("I compose a claim with no class", target_fixture="result")
def compose_no_class(pub):
    return pub.run("compose", "--content=a claim", "--scope=unconditional")


@when("I compose an empirical claim", target_fixture="result")
def compose_empirical(pub):
    return pub.run(
        "compose", "--class=empirical", "--content=the rate fell",
        "--scope=unconditional", f"--method={cid_of(b'a protocol')}",
    )


@when("I compose a claim joining two assertions", target_fixture="result")
def compose_compound(pub):
    return pub.run(
        "compose", "--class=empirical",
        "--content=the rate fell and the cohort was unblinded",
        "--scope=unconditional", f"--method={cid_of(b'a protocol')}",
    )


@then("it exits 2 and lists the commands, with pub --version")
def usage_listed(result):
    body = text_of(result)
    assert result.returncode == 2, body
    assert "usage: pub <command> [options], or pub --version" in body, body
    for command in ("corpus init|status|upgrade|map|renderings", "propose CID...", "witness DOMAIN"):
        assert command in body, body


@then("a workspace exists")
def workspace_exists(pub):
    assert (Path(pub.cwd) / ".publet" / "objects.redb").exists()


@then(parsers.parse('it says to run "{command}"'))
def says_to_run(result, command: str):
    assert command in text_of(result)


@then("the scope is shown")
def scope_shown(result):
    body = text_of(result)
    assert "asserted under" in body
    assert "single-centre, unblinded" in body


@then("its kind, endpoints, and aspect are shown")
def relation_fields_shown(result):
    body = text_of(result)
    assert "kind      depends" in body, body
    assert "from      " in body, body
    assert "to        " in body, body
    assert "aspect    construction" in body, body


@then("its kind and aspect are shown, and the finding in its value")
def verdict_fields_shown(result):
    body = text_of(result)
    assert "kind      verdict" in body, body
    assert "aspect    provenance" in body, body
    assert "finding" in body and "affirm" in body, body


@then("its kind, target, and value fields are shown")
def annotation_fields_shown(result):
    body = text_of(result)
    assert "kind      usage" in body, body
    assert "target    " in body, body
    assert "value:" in body, body
    assert "an external reference" in body, body
    assert "section 2" in body, body


@then(parsers.parse('the mode is reported as "{mode}"'))
def mode_reported(result, mode: str):
    assert f"[{mode}]" in text_of(result)


@then("the affirm, deny, abstain and active weights are shown")
def weights_shown(result):
    body = text_of(result)
    for field in ("affirm", "deny", "abstain", "active"):
        assert field in body, field


@then("the reproduction counts and the replication floor are shown")
def reproductions_shown(result):
    body = text_of(result)
    assert "independent consistent" in body
    assert "floor" in body


@then("no raw count of annotations appears")
def no_raw_counts(result):
    """Fifty affirmations were added; the tally must not be the signal.

    Identifiers are stripped first: a base32 digest will contain the digits
    of any number, and matching inside one would fail for a reason that has
    nothing to do with the rule.
    """
    import re
    body = re.sub(r"pub:sha2-256:[a-z2-7]+", "", text_of(result))
    assert not re.search(r"\b50\b", body), body
    assert "affirm" in body


@then("the affirming weight is shown instead")
def weight_shown_instead(result):
    body = text_of(result)
    line = [l for l in body.splitlines() if l.strip().startswith("affirm")]
    assert line, body
    assert "." in line[0], line


# --- reading an object file ---------------------------------------------------


@given(parsers.parse("an object file holding the cohort claim, named for {naming}"))
def object_file(pub, naming: str):
    data = publet(author_key("K_a"), "2026-09-12T10:00:00Z", "empirical", COHORT)
    pub.file_cid = cid_of(data)
    named = pub.file_cid if naming == "its identifier" else cid_of(b"something else")
    pub.object_file = pub.cwd / "files" / (named.replace(":", "_") + ".cbor")
    pub.object_file.parent.mkdir()
    pub.object_file.write_bytes(data)


@when("I read the object file from a directory with no workspace", target_fixture="result")
def read_object_file(pub):
    elsewhere = pub.cwd / "elsewhere"
    elsewhere.mkdir()
    return pub.runner.act("pub", "read", str(pub.object_file), cwd=elsewhere)


@then("the identifier shown is the one its bytes hash to")
def identifier_computed(pub, result):
    assert result.stdout.splitlines()[0] == pub.file_cid


@then("no mode is reported")
def no_mode(result):
    out = text_of(result)
    assert "[local]" not in out and "[query]" not in out, out


@when("I read the claim as JSON", target_fixture="result")
def read_claim_json(pub):
    return pub.run("read", "--json", pub.claim)


@then(parsers.parse('the JSON names the claim\'s identifier and the mode "{mode}"'))
def json_identity(pub, result, mode: str):
    import json
    doc = json.loads(result.stdout)
    assert doc["cid"] == pub.claim
    assert doc["mode"] == mode


@then("the JSON object holds every header field and the claim's scope")
def json_fields(result):
    import json
    obj = json.loads(result.stdout)["object"]
    assert {"pub", "type", "created", "author", "body"} <= set(obj)
    assert obj["type"] == "claim.prose"
    assert "2031 cohort" in obj["body"]["content"]
    assert obj["body"]["scope"]["domain"] == "adults 40-65, single-centre, unblinded"
