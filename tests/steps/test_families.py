"""Steps for families, editions, and signed generation records (Section 5.9.1,
Section 14.1.1).

Objects are composed through `pub`, as an author would, or built here with no
help from the code under test where the point is what a loader refuses.
"""

from __future__ import annotations

import copy
import json
import subprocess

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pytest_bdd import given, parsers, scenarios, then, when

from support import family_vectors as fv
from support.objects import author_key, cid_of, obj, publet, relation, text, uint, write_store, head

scenarios("../features/conformance/families.feature")
scenarios("../features/porcelain/families.feature")

KIND = {"sort": "kind", "name": "area", "dimension": {"m": 2}, "units": ["m2"]}
BOUNDARY = {"includes": ["Floor inside the walls"], "excludes": ["Fittings"]}
CREATED = "2026-11-02T12:00:00Z"


def _write(runner, name: str, content) -> str:
    path = runner.cwd / name
    path.write_text(json.dumps(content))
    return str(path)


def _define(runner, content: str, defines, *extra: str, cls: str = "definitional"):
    path = _write(runner, "defines.json", defines)
    return runner.run("pub", "compose", f"--class={cls}", f"--content={content}",
                      "--scope=unconditional", f"--defines={path}", *extra)


def _first(out) -> str:
    assert out.code == 0, out.stderr
    return out.stdout.split()[0]


def _family(runner, ctx, parent, fams=None):
    fams = fv.FAMILIES if fams is None else fams
    out = _define(runner, fv.content_of(parent), fams[parent])
    if out.code == 0:
        ctx.setdefault("family", {})[parent] = out.stdout.split()[0]
    return out


def _release(runner, ctx, fams=None, edit=None):
    fams = fv.FAMILIES if fams is None else fams
    for parent in fams:
        assert _family(runner, ctx, parent, fams).code == 0
    defines = fv.edition_of(ctx["family"])
    if edit:
        edit(defines, ctx)
    ctx["defines"] = defines
    out = _define(runner, "The PDC, edition 1.", defines)
    if out.code == 0:
        ctx["edition"] = out.stdout.split()[0]
    return out


def _bundle(runner, *parts: str) -> dict:
    path = runner.cwd.joinpath("bundles", *parts)
    assert path.is_file(), f"no bundle at {path}"
    return json.loads(path.read_text())


def _family_bundle(runner, ctx, parent: str) -> dict:
    return _bundle(runner, "o", f"{ctx['family'][parent]}.json")


def _class(bundle: dict, code: str) -> dict:
    return next(c for c in bundle["family"]["classes"] if c["pdc"] == code)


@pytest.fixture
def ctx():
    return {}


# --- common ------------------------------------------------------------------


@given("a workspace")
def workspace(runner):
    assert runner.run("pub", "init").code == 0


@given("a kind")
def a_kind(runner, ctx):
    ctx["kind"] = _first(_define(runner, "area: the size of a surface.", KIND))


@then("it succeeds")
def it_succeeds(result):
    assert result.code == 0, result.stderr


@then("it fails")
def it_fails(result):
    assert result.code != 0, f"expected failure, got {result.stdout!r}"


@then(parsers.parse('reading it shows "{line}"'))
def reading_shows(runner, result, line: str):
    cid = result.stdout.split()[0]
    out = runner.run("pub", "read", cid)
    assert out.code == 0, out.stderr
    assert line in out.stdout, out.stdout


# --- families ----------------------------------------------------------------


@when(parsers.parse('I compose the family under "{parent}"'), target_fixture="result")
def compose_family(runner, ctx, parent: str):
    return _family(runner, ctx, parent)


@when("I compose a family defining", target_fixture="result")
def compose_family_defining(runner, docstring: str):
    return _define(runner, "The PDC classes directly under 63.", json.loads(docstring))


@when("I compose a normative claim carrying a family", target_fixture="result")
def normative_family(runner):
    return _define(runner, "The PDC classes directly under 6.", fv.FAMILIES["6"], cls="normative")


def _quantity(pdc: str, ctx, boundary=True) -> dict:
    out = {"pdc": pdc, "name": f"quantity {pdc}", "kind": ctx["kind"]}
    return {**out, "boundary": BOUNDARY} if boundary else out


@when("I compose a family whose member narrows the kind", target_fixture="result")
def family_with_kind(runner, ctx):
    out = _define(runner, "The PDC classes directly under 69.",
                  {"sort": "family", "parent": "69", "grouping": 1,
                   "members": [_quantity("69~1", ctx)]})
    ctx["with_kind"] = out.stdout.split()[0] if out.code == 0 else None
    return out


@then("the family presupposes the kind")
def presupposes_kind(runner, ctx):
    out = runner.run("pub", "read", ctx["with_kind"])
    assert ctx["kind"] in out.stdout.split("presupposes:", 1)[1], out.stdout


@when("I compose a family whose member narrows the kind with no boundary", target_fixture="result")
def family_no_boundary(runner, ctx):
    return _define(runner, "The PDC classes directly under 69.",
                   {"sort": "family", "parent": "69", "grouping": 1,
                    "members": [_quantity("69~1", ctx, boundary=False)]})


def _relation_family(ctx, binds: str) -> dict:
    relation_member = {
        "pdc": "69~3", "name": "output per input",
        "relation": {
            "statement": "Output is input times a factor.",
            "slots": [{"role": "output", "concept": "69~1"}, {"role": "input", "concept": binds}],
            "form": "explicit",
        },
    }
    return {"sort": "family", "parent": "69", "grouping": 1,
            "members": [_quantity("69~1", ctx), _quantity("69~2", ctx), relation_member]}


@when("I compose a family of two quantities and a relation between them", target_fixture="result")
def relation_siblings(runner, ctx):
    return _define(runner, "The PDC classes directly under 69.", _relation_family(ctx, "69~2"))


@when(parsers.parse('I compose a family whose relation binds the code "{code}"'),
      target_fixture="result")
def relation_unbound(runner, ctx, code: str):
    return _define(runner, "The PDC classes directly under 69.", _relation_family(ctx, code))


@when(parsers.parse('I compose a singular of class "{code}" depending on the family'),
      target_fixture="result")
def singular_in_family(runner, ctx, code: str):
    return _define(runner, "field: a field.", {"sort": "singular", "name": "field", "class": code},
                   f"--depends={ctx['family']['6']}")


@when(parsers.parse('I compose a singular of class "{code}" depending on nothing'),
      target_fixture="result")
def singular_alone(runner, code: str):
    return _define(runner, "field: a field.", {"sort": "singular", "name": "field", "class": code})


@when(parsers.parse('I compose a concept at "{code}"'), target_fixture="result")
def concept_at(runner, ctx, code: str):
    out = _define(runner, f"{code}: a rival.", {"sort": "concept", "pdc": code, "name": "a rival"})
    ctx["concept"] = out.stdout.split()[0] if out.code == 0 else None
    return out


# --- comparing ---------------------------------------------------------------


def _resting(defn: bytes, content: str) -> bytes:
    return publet(fv.STEWARD, CREATED, "empirical", content, [cid_of(defn)])


def _member(code: str) -> dict:
    return {"pdc": code, "name": f"class {code}"}


def _compare_store(tmp_path, left: bytes, right: bytes, extra: tuple[bytes, ...] = ()) -> dict:
    p, q = _resting(left, "It holds."), _resting(right, "It does not hold.")
    write_store(tmp_path, [left, right, p, q, *extra])
    return {"dir": tmp_path, "cids": [cid_of(p), cid_of(q)]}


@given("a store where two rival families share one code", target_fixture="store")
def rival_families(tmp_path):
    left = fv.claim("The PDC classes directly under 6.",
                    {"sort": "family", "parent": "6", "grouping": 1,
                     "members": [_member("63"), _member("64")]})
    right = fv.claim("Another view of what is under 6.",
                     {"sort": "family", "parent": "6", "grouping": 1,
                      "members": [_member("63"), _member("65")]})
    return _compare_store(tmp_path, left, right)


@given("a store where a concept and a family share one code", target_fixture="store")
def concept_and_family(tmp_path):
    left = fv.claim("The PDC classes directly under 6.",
                    {"sort": "family", "parent": "6", "grouping": 1,
                     "members": [_member("63"), _member("64")]})
    right = fv.claim("63: agriculture.", {"sort": "concept", "pdc": "63", "name": "agriculture"})
    return _compare_store(tmp_path, left, right)


@given("a store where a family is revised and a claim rests on each version",
       target_fixture="store")
def revised_family(tmp_path):
    left = fv.claim("The PDC classes directly under 6.",
                    {"sort": "family", "parent": "6", "grouping": 1, "members": [_member("63")]})
    right = fv.claim("The PDC classes directly under 6, revised.",
                     {"sort": "family", "parent": "6", "grouping": 1,
                      "members": [_member("63"), _member("64")]})
    return _compare_store(tmp_path, left, right, (fv.supersedes(cid_of(right), cid_of(left)),))


@when("I compare the claims resting on each", target_fixture="result")
def compare_claims(runner, store):
    return runner.run("pub-divergence", f"--dir={store['dir']}", *store["cids"])


def _rows(result) -> list[dict]:
    return [json.loads(line) for line in result.stdout.splitlines() if line.strip()]


@then(parsers.parse('the divergence names the code "{code}" and no other'))
def divergence_names(result, code: str):
    rows = _rows(result)
    assert [r["term"] for r in rows] == [code], rows
    assert rows[0]["finding"] == "divergent", rows


@then(parsers.parse('the code "{code}" is stale rather than divergent'))
def code_is_stale(result, code: str):
    rows = _rows(result)
    assert [(r["term"], r["finding"]) for r in rows] == [(code, "stale")], rows


# --- citing a class ----------------------------------------------------------


def _a_claim(runner, ctx) -> str:
    ctx["claim"] = _first(runner.run("pub", "compose", "--class=normative",
                                     "--content=Grow it here.", "--scope=unconditional"))
    return ctx["claim"]


@when(parsers.parse('I classify a claim under the family with aspect "{aspect}"'),
      target_fixture="result")
def classify_with_aspect(runner, ctx, aspect: str):
    return runner.run("pub", "annotate", "--kind=classifies", f"--target={_a_claim(runner, ctx)}",
                      f"--subject={ctx['family']['6']}", f"--aspect={aspect}",
                      "--scope=unconditional")


@when("I classify a claim under the family with no aspect", target_fixture="result")
def classify_no_aspect(runner, ctx):
    return runner.run("pub", "annotate", "--kind=classifies", f"--target={_a_claim(runner, ctx)}",
                      f"--subject={ctx['family']['6']}", "--scope=unconditional")


def _file(runner, ctx, kind: str, target: str, *aspect: str):
    if kind in ("disputes", "supports", "retracts"):
        return runner.run("pub", "relate", f"--kind={kind}", f"--from={_a_claim(runner, ctx)}",
                          f"--to={target}", "--scope=unconditional", *aspect)
    value = {"assessment": ["--verdict=refuted", "--grounds=It should be otherwise."], "tagged": ["--tag=PUB-FAMILY-11-2026"],
             "verdict": ["--finding=deny"],
             "timestamped": [f"--at={CREATED}", "--service=https://example.org/ts",
                             "--proof=a proof"]}[kind]
    return runner.run("pub", "annotate", f"--kind={kind}", f"--target={target}",
                      "--scope=unconditional", *value, *aspect)


@when(parsers.parse('I file a "{kind}" on the family with aspect "{aspect}"'),
      target_fixture="result")
def file_with_aspect(runner, ctx, kind: str, aspect: str):
    return _file(runner, ctx, kind, ctx["family"]["6"], f"--aspect={aspect}")


@when(parsers.parse('I file a "{kind}" on the family with no aspect'), target_fixture="result")
def file_no_aspect(runner, ctx, kind: str):
    return _file(runner, ctx, kind, ctx["family"]["6"])


@when(parsers.parse('I file a "{kind}" on the edition'), target_fixture="result")
def file_on_edition(runner, ctx, kind: str):
    return _file(runner, ctx, kind, ctx["edition"])


@when(parsers.parse('I file a "{kind}" on the concept'), target_fixture="result")
def file_on_concept(runner, ctx, kind: str):
    return _file(runner, ctx, kind, ctx["concept"])


def _as_key(runner, ctx, who: str):
    """Make `who` this workspace's key, generating it the first time."""
    secret = runner.cwd / ".publet" / "signing.key"
    config = runner.cwd / ".publet" / "config"
    keys = ctx.setdefault("keys", {})
    current = ctx.get("as")
    if current:
        keys[current] = secret.read_text(), _author(config)
        secret.unlink()
    ctx["as"] = who
    if who in keys:
        text_, author = keys[who]
        secret.write_text(text_)
        config.write_text("".join(f"author={author}\n" if line.startswith("author=") else line + "\n"
                                  for line in config.read_text().splitlines()))
    else:
        out = runner.run("pub", "sign", "--generate-key", "--principal=human", f"--label={who}")
        assert out.code == 0, out.stderr


def _author(config) -> str:
    return next(l for l in config.read_text().splitlines()
                if l.startswith("author=")).split("=", 1)[1]


def _proposed(ctx) -> dict:
    return ctx["proposal"]


@given("a steward's family")
def stewards_family(runner, ctx):
    workspace(runner)
    _as_key(runner, ctx, "steward")
    assert _family(runner, ctx, "6").code == 0


@when("a second key proposes a new family superseding it")
def second_key_proposes(runner, ctx):
    _as_key(runner, ctx, "proposer")
    grown = copy.deepcopy(fv.FAMILIES["6"])
    grown["members"].append({"pdc": "64", "name": "Home economics"})
    proposed = _first(_define(runner, "The PDC classes directly under 6, as proposed.", grown))
    edge = _first(runner.run("pub", "relate", "--kind=supersedes", f"--from={proposed}",
                             f"--to={ctx['family']['6']}", "--scope=unconditional"))
    ctx["proposal"] = {"family": proposed, "edge": edge}


def _grounds(runner, content: str) -> str:
    return _first(runner.run("pub", "compose", "--class=normative", f"--content={content}",
                             "--scope=unconditional"))


@when("the second key files an argument supporting the proposal's relation",
      target_fixture="result")
def argument_supports_relation(runner, ctx):
    argument = _grounds(runner, "Class 64 belongs under 6.")
    return runner.run("pub", "relate", "--kind=supports", f"--from={argument}",
                      f"--to={_proposed(ctx)['edge']}", "--scope=unconditional")


@when("a third claim disputes the proposal's relation", target_fixture="result")
def claim_disputes_relation(runner, ctx):
    grounds = _grounds(runner, "Class 64 belongs under 7.")
    return runner.run("pub", "relate", "--kind=disputes", f"--from={grounds}",
                      f"--to={_proposed(ctx)['edge']}", "--scope=unconditional")


@when(parsers.parse('the second key files a "{kind}" on the {which} family'),
      target_fixture="result")
def argue_with_a_family(runner, ctx, kind: str, which: str):
    target = ctx["family"]["6"] if which == "current" else _proposed(ctx)["family"]
    return _file(runner, ctx, kind, target)


@then("everything held loads with nothing left out")
def nothing_left_out(runner):
    _export(runner)
    out = runner.run("pub-ls", "--dir=exported")
    assert out.code == 0 and "warning" not in out.stderr, out.stderr


def _export(runner):
    where = runner.cwd / "exported"
    where.mkdir(exist_ok=True)
    held = runner.run("pub", "bundle", f"--out={where}-bundle-{len(list(runner.cwd.iterdir()))}")
    assert held.code == 0, held.stderr
    bundle = sorted(p for p in runner.cwd.iterdir() if p.name.startswith("exported-bundle-"))[-1]
    for obj_path in (bundle / "pub" / "v1" / "object").iterdir():
        (where / (obj_path.name.replace(":", "_") + ".cbor")).write_bytes(obj_path.read_bytes())
    return where


@when("the steward publishes the proposal")
def steward_publishes(runner, ctx):
    _as_key(runner, ctx, "steward")
    _first(runner.run("pub", "relate", "--kind=supersedes", f"--from={_proposed(ctx)['family']}",
                      f"--to={ctx['family']['6']}", "--scope=unconditional"))


def _proposal_lineage(runner, ctx, mode: str) -> list[str]:
    _export(runner)
    out = runner.run("pub-lineage", "--dir=exported", mode, ctx["family"]["6"])
    assert out.code == 0, out.stderr
    return out.stdout.split()


@then("the proposal is in the family's full lineage and not its authoritative one")
def proposal_is_proposal(runner, ctx):
    assert _proposed(ctx)["family"] in _proposal_lineage(runner, ctx, "--full")
    assert _proposed(ctx)["family"] not in _proposal_lineage(runner, ctx, "--authoritative")


@then("the proposal is in the family's authoritative lineage")
def proposal_published(runner, ctx):
    assert _proposed(ctx)["family"] in _proposal_lineage(runner, ctx, "--authoritative")


@given(parsers.parse('a workspace holding a family vector "{case}" as a directory'))
def vector_as_domain_dir(runner, ctx, case: str):
    assert runner.run("pub", "init").code == 0
    where = runner.cwd / "domain"
    where.mkdir()
    for path in (fv.VECTORS / case).iterdir():
        (where / path.name).write_bytes(path.read_bytes())
    ctx["domain"] = where
    ctx["members"] = {p.stem.replace("_", ":") for p in where.glob("*.cbor")}


@then("every object in the directory is a member of its generation")
def all_are_members(runner, ctx, result):
    line = next(l for l in result.stdout.splitlines() if l.startswith("generation"))
    read = _bundles_of(runner, ctx["domain"])
    assert set(read(line.split()[1])["object"]["body"]["added"]) == ctx["members"]


@when("I dispute a claim resting on the family", target_fixture="result")
def dispute_resting_claim(runner, ctx):
    resting = _first(runner.run("pub", "compose", "--class=normative", "--content=Grow it there.",
                                "--scope=unconditional", f"--depends={ctx['family']['6']}"))
    return runner.run("pub", "relate", "--kind=disputes", f"--from={_a_claim(runner, ctx)}",
                      f"--to={resting}", "--scope=unconditional")


@when(parsers.parse('I file usage on the family with aspect "{aspect}"'), target_fixture="result")
def usage_on_family(runner, ctx, aspect: str):
    return runner.run("pub", "annotate", "--scope=unconditional", "--kind=usage",
                      f"--target={ctx['family']['6']}", f"--aspect={aspect}",
                      "--source=https://example.org/udc", "--locator=p. 63")


@when(parsers.parse('I file a verdict on the family with aspect "{aspect}"'),
      target_fixture="result")
def verdict_on_family(runner, ctx, aspect: str):
    return runner.run("pub", "annotate", "--scope=unconditional", "--kind=verdict",
                      f"--target={ctx['family']['6']}", f"--aspect={aspect}", "--finding=affirm")


# --- editions ----------------------------------------------------------------


@when("I compose a release", target_fixture="result")
def compose_release(runner, ctx):
    return _release(runner, ctx)


@given("a composed release")
def composed_release(runner, ctx):
    assert _release(runner, ctx).code == 0


@when("I compose an edition of families this workspace does not hold", target_fixture="result")
def edition_unheld(runner):
    objects = {parent: fv.claim(fv.content_of(parent), d) for parent, d in fv.FAMILIES.items()}
    return _define(runner, "The PDC, edition 1.",
                   fv.edition_of({p: cid_of(o) for p, o in objects.items()}))


def _with(parent, change):
    fams = copy.deepcopy(fv.FAMILIES)
    change(fams[parent])
    return fams


def _code_twice(family):
    family["members"].append({"pdc": "(1/9)", "name": "Place, again"})


def _orphan_edit(defines, ctx):
    # A real family, under a code no listed family defines.
    defines["sections"]["main"]["7"] = ctx["orphan"]
    defines["counts"]["main"] = {"families": 3, "classes": 3, "auxiliaries": 1}
    defines["counts"]["total"] = {"families": 6, "classes": 7, "auxiliaries": 1}


def _set(*path):
    """Set the value at a path, its last argument, in an edition."""
    def apply(defines, _ctx=None):
        at = defines
        for key in path[:-2]:
            at = at[key]
        at[path[-2]] = path[-1]
    return apply


DISAGREEMENTS = {
    "classes miscounted in a section": {"edit": _set("counts", "main", "classes", 9)},
    "auxiliaries miscounted in total": {"edit": _set("counts", "total", "auxiliaries", 9)},
    "a child not flagged": {"fams": _with("----", lambda f: f["members"][0].pop("children"))},
    "a flag with no family under it": {
        "fams": _with("6", lambda f: f["members"][0].update(children=True))},
    "an undefined grouping": {"fams": _with("6", lambda f: f.update(grouping=7))},
    "a parent not its key": {"fams": _with("6", lambda f: f.update(parent="7"))},
    "a top family with a parent": {"fams": _with(None, lambda f: f.update(parent="0"))},
    "a code in two families": {"fams": _with("6", _code_twice)},
}


@when(parsers.parse("I compose a release with {change}"), target_fixture="result")
def release_with(runner, ctx, change: str):
    if change.startswith("its edition changed by "):
        return _release(runner, ctx, edit=SHAPES[change.removeprefix("its edition changed by ")])
    if change == "a parent nothing defines":
        ctx["orphan"] = _first(_define(
            runner, "The PDC classes directly under 7.",
            {"sort": "family", "parent": "7", "grouping": 1, "members": [_member("71")]}))
        return _release(runner, ctx, edit=_orphan_edit)
    if change == "a concept listed as a family":
        rival = _first(_define(runner, "63: a rival.",
                               {"sort": "concept", "pdc": "63", "name": "a rival"}))
        return _release(runner, ctx, edit=_set("sections", "main", "6", rival))
    return _release(runner, ctx, **DISAGREEMENTS[change])


def _twice_listed(defines, _ctx=None):
    defines["sections"]["main"]["6"] = defines["sections"]["main"]["----"]


def _parent_in_two(defines, _ctx=None):
    defines["sections"]["special-auxiliaries"]["6"] = defines["sections"]["main"]["6"]
    defines["counts"]["special-auxiliaries"]["families"] = 2
    defines["counts"]["total"]["families"] = 6


SHAPES = {
    "no top family": lambda d, _c=None: d.pop("top"),
    "no main section": lambda d, _c=None: d["sections"].pop("main"),
    "one family listed twice": _twice_listed,
    "one parent in two sections": _parent_in_two,
    "a group number used twice": _set("groups", 1, "number", 1),
    "a group with no heads": _set("groups", 0, "heads", []),
    "a head named twice": _set("groups", 1, "heads", ["62-1/-9", "62-1/-9"]),
    "a grouping of no such group": _set("groupings", 0, "groups", [9]),
    "no counts": lambda d, _c=None: d.pop("counts"),
    "groups miscounted": _set("counts", "groups", 9),
    "groupings miscounted": _set("counts", "groupings", 9),
    "a section's families miscounted": _set("counts", "main", "families", 9),
    "total families miscounted": _set("counts", "total", "families", 9),
}


def _drop(defines, key: str, number: int):
    defines[key] = [e for e in defines[key] if e["number"] != number]
    defines["counts"][key] = len(defines[key])


def _revise(runner, ctx, change):
    defines = copy.deepcopy(ctx["defines"])
    change(defines)
    path = _write(runner, "next.json", defines)
    return runner.run("pub", "revise", ctx["edition"], f"--defines={path}",
                      "--content=The PDC, edition 2.")


def _gain(d):
    d["groups"][0]["heads"].append("(4)")
    d["groups"].append({"number": 3, "heads": ["(5)"]})
    d["groupings"][0]["groups"].append(3)
    d["groupings"].append({"number": 4, "groups": [3]})
    d["counts"]["groups"], d["counts"]["groupings"] = 3, 4


REVISIONS = {
    "a group and a grouping gain members and new numbers appear": _gain,
    "a group loses a head": lambda d: d["groups"][0].update(heads=["(1/9)"]),
    "a grouping loses a group": lambda d: d["groupings"][1].update(groups=[2]),
    "a group number is dropped": lambda d: (
        d["groupings"][1].update(groups=[1]), d["groupings"][2].update(groups=[1]),
        _drop(d, "groups", 2)),
    "a grouping number is dropped": lambda d: _drop(d, "groupings", 3),
    "a group number means another": lambda d: d["groups"][1].update(heads=["(4)"]),
    "a grouping number means another": lambda d: d["groupings"][0].update(groups=[2]),
}


@when(parsers.parse("I revise the edition so that {change}"), target_fixture="result")
def revise_edition(runner, ctx, change: str):
    return _revise(runner, ctx, REVISIONS[change])


@given("a store where another key files a supersedes from an edition to one it shrinks against",
       target_fixture="store")
def third_party_supersedes(tmp_path):
    objects, edition = fv.release()
    other = author_key("someone else")
    bigger = fv.edition_of({p: cid_of(fv.claim(fv.content_of(p), d))
                            for p, d in fv.FAMILIES.items()})
    bigger["groups"].append({"number": 3, "heads": ["(4)"]})
    bigger["counts"]["groups"] = 3
    theirs = obj("claim.prose", other, CREATED, [
        ("class", text("definitional")), ("lang", text("en")),
        ("content", text("Their PDC.")),
        ("depends", head(4, 0)), ("defines", fv.encode(bigger)),
    ])
    write_store(tmp_path, [*objects, edition, theirs,
                           relation(other, CREATED, "supersedes", cid_of(edition), cid_of(theirs))])
    return {"dir": tmp_path}


# --- vectors -----------------------------------------------------------------


@given(parsers.parse('the family vector "{case}"'), target_fixture="vector")
def family_vector(case: str):
    return case


@when("I load the vector", target_fixture="result")
def load_vector(runner, vector: str):
    return runner.run("pub-ls", f"--dir={fv.VECTORS / vector}")


@when("I list the vector's terms", target_fixture="result")
def vector_terms(runner, vector: str):
    return runner.run("pub-term", f"--dir={fv.VECTORS / vector}", "--list")


@then("the vector's outcome is what its table says")
def vector_outcome(result, vector: str):
    table = dict(line.split("\t", 1) for line in
                 (fv.VECTORS / "EXPECTED.tsv").read_text().splitlines())
    rule = table[vector]
    if vector.startswith("accept-"):
        assert rule == "accepted", rule
        assert result.code == 0 and "warning" not in result.stderr, result.stderr
    elif vector.startswith("drop-"):
        # One object left out and reported, by its CID, and the rest loaded.
        assert result.code == 0, result.stderr
        assert rule in result.stderr, result.stderr
        files = {p.stem.replace("_", ":") for p in (fv.VECTORS / vector).glob("*.cbor")}
        listed = set(result.stdout.split())
        assert listed < files and len(files - listed) == 1, (files, listed)
        assert f"warning: dropped {next(iter(files - listed))}" in result.stderr, result.stderr
    else:
        assert result.code == 1, result.stdout
        assert rule in result.stderr, result.stderr


def _lineage(runner, vector: str, *mode: str) -> list[str]:
    family = cid_of(fv.claim(fv.content_of("6"), fv.FAMILIES["6"]))
    out = runner.run("pub-lineage", f"--dir={fv.VECTORS / vector}", *mode, family)
    assert out.code == 0, out.stderr
    return out.stdout.split()


def _next_version(vector: str) -> str:
    author = fv.STEWARD if vector.endswith("steward") else fv.OTHER_KEY
    return cid_of(fv.revision(author)[1])


@then("the next version is in the family's authoritative lineage")
def next_version_authoritative(runner, vector: str):
    assert _next_version(vector) in _lineage(runner, vector, "--authoritative")


@then("the next version is in the family's full lineage and not its authoritative one")
def next_version_proposed(runner, vector: str):
    newer = _next_version(vector)
    assert newer in _lineage(runner, vector, "--full")
    assert newer not in _lineage(runner, vector, "--authoritative")


@then("the terms name each class and nothing for the edition")
def terms_are_classes(result):
    assert result.code == 0, result.stderr
    terms = {json.loads(line)["term"] for line in result.stdout.splitlines()}
    codes = {m["pdc"].lower() for f in fv.FAMILIES.values()
             for m in f["members"] + f.get("auxiliaries", [])}
    assert terms == codes, terms


@then("every family vector is what the generator makes")
def vectors_current():
    cases = fv.cases()
    table = (fv.VECTORS / "EXPECTED.tsv").read_text()
    assert table == "".join(f"{n}\t{r or 'accepted'}\n" for n, (_, r) in sorted(cases.items()))
    for name, (objects, _) in cases.items():
        on_disk = {p.name: p.read_bytes() for p in (fv.VECTORS / name).iterdir()}
        made = {cid_of(o).replace(":", "_") + ".cbor": o for o in objects}
        assert on_disk == made, f"{name}: run python tests/support/family_vectors.py"


# --- bundles -----------------------------------------------------------------


@when("I write the family bundles", target_fixture="result")
def write_bundles(runner):
    return runner.run("pub", "bundle", "--out=bundles", "--base=https://pub.example")


@given(parsers.parse('a directory holding a release and an anchor over the family under "{parent}"'))
def release_with_anchor(runner, ctx, parent: str):
    objects, edition = fv.release()
    cids = {p: cid_of(fv.claim(fv.content_of(p), d)) for p, d in fv.FAMILIES.items()}
    anchor = obj("anchor", fv.STEWARD, CREATED, [
        ("lineage", text(cids[parent])), ("current", text(cids[parent])),
        ("stewards", head(4, 1) + text(fv.STEWARD)), ("threshold", uint(1)),
    ])
    where = runner.cwd / "objects"
    where.mkdir()
    write_store(where, [*objects, edition, anchor])
    ctx["family"] = cids
    ctx["anchor"] = cid_of(anchor)


@when("I write the family bundles from the directory", target_fixture="result")
def write_bundles_from_dir(runner):
    return runner.run("pub", "bundle", "--dir=objects", "--out=bundles")


@then(parsers.parse('the name "{code}" has a bundle pointing at the family under "{parent}" '
                    'and the code "{same}"'))
def name_points_at_family(runner, ctx, code: str, parent: str, same: str):
    name = _bundle(runner, "def", code.replace("/", "_") + ".json")
    assert name["classes"] == [{"family": ctx["family"][parent], "code": same}], name
    assert name["definitions"] == [ctx["family"][parent]], name


@then(parsers.parse('the family under "{parent}" has no name of its own'))
def family_has_no_name(runner, ctx, parent: str):
    bundle = _family_bundle(runner, ctx, parent)
    assert bundle["summary"]["name"] is None and bundle["address"] is None, bundle["summary"]


@then(parsers.parse('the bundle of the family under "{parent}" names its parent "{code}" '
                    'and its grouping {grouping:d}'))
def family_bundle_head(runner, ctx, parent: str, code: str, grouping: int):
    family = _family_bundle(runner, ctx, parent)["family"]
    assert (family["parent"], family["grouping"]) == (code, grouping), family


@then(parsers.parse('the bundle of the family under "{parent}" lists "{member}" as a member and '
                    '"{aux}" as an auxiliary heading a family'))
def family_bundle_classes(runner, ctx, parent: str, member: str, aux: str):
    bundle = _family_bundle(runner, ctx, parent)
    assert not _class(bundle, member)["auxiliary"]
    klass = _class(bundle, aux)
    assert klass["auxiliary"] and klass["children"], klass
    assert klass["narrower"] == [ctx["family"][aux]], klass


@then(parsers.parse('the bundle of the family under "{parent}" says the family under "{above}" '
                    'is broader'))
def family_bundle_broader(runner, ctx, parent: str, above: str):
    assert _family_bundle(runner, ctx, parent)["family"]["broader"] == [ctx["family"][above]]


@then(parsers.parse('the edition\'s bundle is sorted "{sort}"'))
def edition_bundle(runner, ctx, sort: str):
    assert _bundle(runner, "o", f"{ctx['edition']}.json")["summary"]["sort"] == sort


@then(parsers.parse('the family under "{parent}" says it is listed in the edition'))
def listed_in_edition(runner, ctx, parent: str):
    used = _family_bundle(runner, ctx, parent)["used_by"]
    assert {"cid": ctx["edition"], "how": "listed in edition"} in used, used


@then(parsers.parse('the name "{code}" lists the family and the concept'))
def name_lists_both(runner, ctx, code: str):
    name = _bundle(runner, "def", f"{code}.json")
    assert sorted(name["definitions"]) == sorted([ctx["family"]["6"], ctx["concept"]]), name
    assert name["classes"] == [{"family": ctx["family"]["6"], "code": code}], name


@then(parsers.parse('the bundle of the family under "{parent}" shows the concept competing '
                    'for "{code}"'))
def family_shows_rival(runner, ctx, parent: str, code: str):
    assert _class(_family_bundle(runner, ctx, parent), code)["competing"] == [ctx["concept"]]


@then("the concept's bundle shows the family competing for its code")
def concept_shows_rival(runner, ctx):
    bundle = _bundle(runner, "o", f"{ctx['concept']}.json")
    assert bundle["concept"]["competing"] == [ctx["family"]["6"]], bundle["concept"]


@then(parsers.parse('the bundle of the family under "{parent}" lists the claim as a member '
                    'of "{code}"'))
def family_lists_member(runner, ctx, parent: str, code: str):
    members = _class(_family_bundle(runner, ctx, parent), code)["members"]
    assert [m["cid"] for m in members] == [ctx["claim"]], members


@then(parsers.parse('the claim\'s bundle says it is classified under the code "{code}"'))
def claim_classified(runner, ctx, code: str):
    under = _bundle(runner, "o", f"{ctx['claim']}.json")["classified_under"]
    assert [(u["concept"], u["code"]) for u in under] == [(ctx["family"]["6"], code)], under


@then(parsers.parse('the bundle of the family under "{parent}" names the anchor'))
def family_names_anchor(runner, ctx, parent: str):
    anchors = _family_bundle(runner, ctx, parent)["family"]["anchors"]
    assert [a["cid"] for a in anchors] == [ctx["anchor"]], anchors


@then(parsers.parse('the bundle of the family under "{parent}" names no anchor'))
def family_no_anchor(runner, ctx, parent: str):
    assert _family_bundle(runner, ctx, parent)["family"]["anchors"] == []


# --- signed generation records ----------------------------------------------


def _pub(runner, where, *args):
    return subprocess.run([str(runner.path_to("pub")), *args], capture_output=True, text=True,
                          cwd=where, check=False)


def _publet(where, content: str):
    path = where / "publets" / "note" / "publet.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "slug": "note", "tag": "PUB-NOTENO-11-2026", "title": "A note",
        "claims": {"it": {"class": "normative", "scope": "the test", "content": content}},
        "sections": [{"heading": "It", "items": [{"ref": "#it"}]}],
    }))


def _published(runner, where):
    built = _pub(runner, where, "build")
    assert built.returncode == 0, built.stdout + built.stderr
    out = _pub(runner, where, "publish", "--all", "--no-rendering")
    assert out.returncode == 0, out.stdout + out.stderr
    return out


@given("a corpus with a key and one publet", target_fixture="corpus")
def corpus_with_key(runner):
    where = runner.cwd / "corpus"
    where.mkdir()
    assert _pub(runner, where, "corpus", "init", "--name=test").returncode == 0
    keyed = _pub(runner, where, "sign", "--generate-key", "--principal=human", "--label=Author")
    assert keyed.returncode == 0, keyed.stderr
    _publet(where, "Grow it here.")
    return {"where": where}


@when("I publish it")
def publish_it(runner, corpus):
    _published(runner, corpus["where"])


@when("I revise the publet and publish it")
def revise_and_publish(runner, corpus):
    _publet(corpus["where"], "Grow it there.")
    _published(runner, corpus["where"])


@when("I publish it again with nothing changed", target_fixture="result")
def publish_again(runner, corpus):
    corpus["before"] = (runner.cwd / "corpus" / "corpus.lock").read_text()
    return _published(runner, corpus["where"])


@then("the generation stays as it was")
def generation_unchanged(runner, corpus, result):
    assert "generation stays as it was" in result.stdout, result.stdout
    assert (corpus["where"] / "corpus.lock").read_text() == corpus["before"]


def _bundles_of(runner, objects_dir):
    out = runner.run("pub", "bundle", f"--dir={objects_dir}", "--out=sig-bundles")
    assert out.code == 0, out.stderr
    bundles = runner.cwd / "sig-bundles"
    return lambda cid: json.loads((bundles / "o" / f"{cid}.json").read_text())


def _assert_signed(runner, objects_dir, generation: str, purpose: str):
    """The record has a signature that verifies, by the key that authored it."""
    read = _bundles_of(runner, objects_dir)
    bundle = read(generation)
    signers = [u["cid"] for u in bundle["used_by"] if u["how"] == "signature"]
    assert len(signers) == 1, bundle["used_by"]
    sig = read(signers[0])["object"]
    assert sig["author"] == bundle["object"]["author"]
    assert sig["body"]["purpose"] == purpose and sig["body"]["target"] == generation
    key = read(sig["author"])["object"]["body"]["pubkey"]["$bytes"]
    record = (objects_dir / (generation.replace(":", "_") + ".cbor")).read_bytes()
    message = runner.run("pub-sign", f"--purpose={purpose}", "--message", stdin=record)
    assert message.code == 0, message.stderr
    Ed25519PublicKey.from_public_bytes(bytes.fromhex(key)).verify(
        bytes.fromhex(sig["body"]["value"]["$bytes"]), bytes.fromhex(message.stdout.strip()))
    return signers[0]


@then(parsers.parse('the corpus\'s generation record is signed by its key with purpose "{purpose}"'))
def generation_signed(runner, corpus, purpose: str):
    lock = json.loads((corpus["where"] / "corpus.lock").read_text())
    corpus["generation"] = lock["corpus"]["generation"]["cid"]
    corpus["signature"] = _assert_signed(runner, corpus["where"] / "objects",
                                         corpus["generation"], purpose)


@then("the signature is not a member of the generation")
def signature_not_member(runner, corpus):
    read = _bundles_of_cached(runner, corpus)
    chain, at = [], corpus["generation"]
    while at:
        record = read(at)["object"]["body"]
        chain.extend(record["added"])
        at = record.get("parent")
    assert corpus["signature"] not in chain, chain


def _bundles_of_cached(runner, corpus):
    bundles = runner.cwd / "sig-bundles"
    return lambda cid: json.loads((bundles / "o" / f"{cid}.json").read_text())


@given("a directory of objects and a workspace with a key")
def domain_with_key(runner, ctx):
    workspace(runner)
    assert runner.run("pub", "sign", "--generate-key", "--principal=human").code == 0
    _domain_dir(runner, ctx)


@given("a directory of objects and a workspace with no key")
def domain_without_key(runner, ctx):
    workspace(runner)
    _domain_dir(runner, ctx)


def _domain_dir(runner, ctx):
    where = runner.cwd / "domain"
    where.mkdir()
    write_store(where, [fv.claim("63: agriculture.",
                                 {"sort": "concept", "pdc": "63", "name": "agriculture"})])
    ctx["domain"] = where


@when("I make a domain of the directory", target_fixture="result")
def make_domain(runner, ctx):
    return runner.run("pub", "domain", f"--dir={ctx['domain']}", "--label=test", "--bound=1000000")


@then(parsers.parse('its generation record is signed by the key with purpose "{purpose}"'))
def domain_generation_signed(runner, ctx, result, purpose: str):
    line = next(l for l in result.stdout.splitlines() if l.startswith("generation"))
    # `pub domain` writes what it was given and leaves the key in the workspace.
    key = next(l for l in (runner.cwd / ".publet" / "config").read_text().splitlines()
               if l.startswith("author=")).split("=", 1)[1]
    copied = runner.run("pub-cat", "--store=.publet/objects.redb", key)
    assert copied.code == 0, copied.stderr
    (ctx["domain"] / (key.replace(":", "_") + ".cbor")).write_bytes(copied.out)
    _assert_signed(runner, ctx["domain"], line.split()[1], purpose)


@then(parsers.parse('stdout mentions "{fragment}"'))
def stdout_mentions(result, fragment: str):
    assert fragment in result.stdout, result.stdout
