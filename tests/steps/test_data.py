"""Steps for data payloads, sources, blobs, views, `pub doc`, and `pub revise`.

Gathering and rendering are separate acts. What is gathered -- values,
where they were read from, why they were assembled that way -- is signed
and stored; how they are shown is a view in the document that shows them,
and the showing itself is never stored. These scenarios drive the porcelain
a gather step would drive, and read results back the way a reader would.
"""

from __future__ import annotations

import json

from pytest_bdd import given, parsers, scenarios, then, when

from support.objects import author_key, cbor_map, cid_of, head, obj, text, uint, write_store

scenarios("../features/conformance/data.feature")
scenarios("../features/conformance/sources.feature")
scenarios("../features/conformance/quantities.feature")
scenarios("../features/conformance/blobs.feature")
scenarios("../features/porcelain/doc.feature")
scenarios("../features/porcelain/revise.feature")
scenarios("../features/porcelain/bundle.feature")

CONTENT = "Planned P0 spend by item, Oct 2026 to Mar 2027."
SCOPE = "Sustenaut P0 plan as approved for the first phase"
BUDGET = {
    "columns": [{"name": "item"}, {"name": "spend", "unit": "EUR"}],
    "rows": [["seed trays", "120.00"], ["grow lights", "480.00"]],
}
REPO = "https://github.com/schryer/business-plan"


def _held(runner) -> set[str]:
    out = runner.run("pub-store", "--store=.publet/objects.redb", "list")
    assert out.code == 0, out.stderr
    return set(out.stdout.split())


def _write(runner, name: str, content) -> str:
    path = runner.cwd / name
    if isinstance(content, (dict, list)):
        content = json.dumps(content)
    path.write_text(content)
    return str(path)


def _compose_budget(runner, ctx, data, *extra: str):
    ctx.setdefault("before", _held(runner))
    args = ["compose", "--class=normative", f"--content={CONTENT}", f"--scope={SCOPE}"]
    if data is not None:
        args.append(f"--data={_write(runner, 'data.json', data)}")
    result = runner.run("pub", *args, *extra)
    if result.code == 0:
        ctx["claim"] = result.stdout.split()[0]
    return result


def _read(runner, cid: str) -> str:
    out = runner.run("pub", "read", cid)
    assert out.code == 0, out.stderr
    return out.stdout


# --- givens ------------------------------------------------------------------


@given("a workspace", target_fixture="ctx")
def workspace(runner):
    assert runner.run("pub", "init").code == 0
    return {}


@given("a workspace with a budget claim", target_fixture="ctx")
def workspace_with_budget(runner):
    assert runner.run("pub", "init").code == 0
    ctx: dict = {}
    out = _compose_budget(runner, ctx, BUDGET, f"--source={REPO}",
                          "--source-revision=abc123",
                          "--source-locator=bizplan/plan/p0.py")
    assert out.code == 0, out.stderr
    ctx["budget"] = ctx.pop("claim")
    ctx.pop("before")
    return ctx


@given("a workspace with a normative claim about grouping", target_fixture="ctx")
def workspace_with_reason(runner):
    assert runner.run("pub", "init").code == 0
    out = runner.run(
        "pub", "compose", "--class=normative", "--scope=unconditional",
        "--content=Budgets are grouped by phase because each phase is approved separately.",
    )
    assert out.code == 0, out.stderr
    return {"reason": out.stdout.strip()}


@given(parsers.parse('a file "{name}" containing "{content}"'))
def a_file(runner, name: str, content: str):
    _write(runner, name, content)


@given(parsers.parse('a claim whose data is the file "{name}" as "{media}"'))
def claim_with_file(runner, ctx, name: str, media: str):
    out = _compose_budget(runner, ctx, {"media": media, "file": name})
    assert out.code == 0, out.stderr
    ctx.pop("before")


def _prose(author: str, depends: list[str], evidence: list[bytes]) -> bytes:
    return obj("claim.prose", author, "2026-09-12T10:00:00Z", [
        ("class", text("normative")),
        ("lang", text("en")),
        ("content", text(CONTENT)),
        ("scope", cbor_map([("domain", text("unconditional")),
                            ("conditions", head(4, 0))])),
        ("depends", head(4, len(depends)) + b"".join(text(d) for d in depends)),
        ("evidence", head(4, len(evidence)) + b"".join(evidence)),
    ])


def _store_with_source(tmp_path, listed: bool):
    ka = author_key("K_a")
    reason = obj("claim.prose", ka, "2026-09-12T09:00:00Z", [
        ("class", text("normative")),
        ("lang", text("en")),
        ("content", text("Budgets are grouped by phase.")),
        ("scope", cbor_map([("domain", text("unconditional")),
                            ("conditions", head(4, 0))])),
        ("depends", head(4, 0)),
    ])
    source = cbor_map([
        ("kind", text("claim")),
        ("role", text("source")),
        ("ref", text(cid_of(reason))),
    ])
    budget = _prose(ka, [cid_of(reason)] if listed else [], [source])
    write_store(tmp_path, [reason, budget])
    return {"dir": tmp_path}


@given("a store holding a claim whose source claim is not in depends",
       target_fixture="store")
def store_source_unlisted(tmp_path):
    return _store_with_source(tmp_path, listed=False)


@given("a store holding a claim whose source claim is in depends",
       target_fixture="store")
def store_source_listed(tmp_path):
    return _store_with_source(tmp_path, listed=True)


def _manifest(budget: str, view=None, item_extra=None) -> dict:
    item = {"ref": budget, "role": "assert",
            "gloss": "Planned spend for the first phase."}
    if view is not None:
        item["view"] = view
    if item_extra:
        item.update(item_extra)
    return {"title": "Sustenaut Business Plan",
            "sections": [{"heading": "Budget", "items": [item]}]}


def _build_doc(runner, ctx, manifest: dict, name: str = "doc.json"):
    ctx.setdefault("before", _held(runner))
    result = runner.run("pub", "doc", _write(runner, name, manifest))
    if result.code == 0:
        ctx.setdefault("docs", []).append(result.stdout.strip())
    return result


@given(parsers.parse('a document viewing the budget as "{renderer}"'))
def a_document(runner, ctx, renderer: str):
    out = _build_doc(runner, ctx, _manifest(ctx["budget"], {"renderer": renderer}))
    assert out.code == 0, out.stderr
    ctx["doc"] = out.stdout.strip()
    ctx.pop("before")


# --- whens -------------------------------------------------------------------


@when("I compose a budget claim with the data", target_fixture="result")
def compose_with_data(runner, ctx, docstring: str):
    return _compose_budget(runner, ctx, docstring)


@when(parsers.parse('I compose a budget claim read from "{ref}" at revision '
                    '"{revision}" in "{locator}"'), target_fixture="result")
def compose_from_file(runner, ctx, ref: str, revision: str, locator: str):
    return _compose_budget(runner, ctx, BUDGET, f"--source={ref}",
                           f"--source-revision={revision}",
                           f"--source-locator={locator}")


@when(parsers.parse('I compose a budget claim read from table "{table}" by '
                    'query "{query}"'), target_fixture="result")
def compose_from_table(runner, ctx, table: str, query: str):
    return _compose_budget(runner, ctx, BUDGET, f"--source={table}",
                           f"--source-query={query}")


@when("I compose a budget claim read from that claim", target_fixture="result")
def compose_from_claim(runner, ctx):
    return _compose_budget(runner, ctx, BUDGET, f"--source={ctx['reason']}")


@when("I compose a budget claim read from an identifier nothing here holds",
      target_fixture="result")
def compose_from_nothing(runner, ctx):
    return _compose_budget(runner, ctx, BUDGET, f"--source={cid_of(b'elsewhere')}")


@when(parsers.parse('I compose a claim whose data is the file "{name}" as "{media}"'),
      target_fixture="result")
def compose_with_file(runner, ctx, name: str, media: str):
    ctx["blob"] = cid_of((runner.cwd / name).read_bytes())
    return _compose_budget(runner, ctx, {"media": media, "file": name})


@when("I compose a claim whose data cites a blob nothing here holds",
      target_fixture="result")
def compose_with_missing_blob(runner, ctx):
    return _compose_budget(runner, ctx, {"media": "application/pdf",
                                         "ref": cid_of(b"elsewhere"), "size": 9})


@when(parsers.parse("I compose a claim citing that blob with size {size:d}"),
      target_fixture="result")
def compose_with_wrong_size(runner, ctx, size: int):
    blob = cid_of((runner.cwd / "plan.pdf").read_bytes())
    return _compose_budget(runner, ctx, {"media": "application/pdf",
                                         "ref": blob, "size": size})


@when(parsers.parse('I build a document from a manifest viewing the budget as '
                    '"{renderer}"'), target_fixture="result")
def build_doc(runner, ctx, renderer: str):
    return _build_doc(runner, ctx, _manifest(ctx["budget"], {"renderer": renderer}),
                      name=f"{renderer}.json")


@when("I build a document from a manifest whose view has no renderer",
      target_fixture="result")
def build_doc_no_renderer(runner, ctx):
    return _build_doc(runner, ctx, _manifest(ctx["budget"],
                                             {"options": {"totals": True}}))


@when(parsers.parse('I build a document from a manifest with an item key "{key}"'),
      target_fixture="result")
def build_doc_bad_key(runner, ctx, key: str):
    return _build_doc(runner, ctx, _manifest(ctx["budget"], item_extra={key: "x"}))


@when("I revise the budget claim with the data", target_fixture="result")
def revise_with_data(runner, ctx, docstring: str):
    ctx["before"] = _held(runner)
    return runner.run("pub", "revise", ctx["budget"],
                      f"--data={_write(runner, 'next.json', docstring)}")


@when("I revise the budget claim with its own data again", target_fixture="result")
def revise_same(runner, ctx):
    ctx["before"] = _held(runner)
    return runner.run("pub", "revise", ctx["budget"],
                      f"--data={_write(runner, 'same.json', BUDGET)}")


@when(parsers.parse('I revise the budget claim read from revision "{revision}"'),
      target_fixture="result")
def revise_sources(runner, ctx, revision: str):
    return runner.run("pub", "revise", ctx["budget"], f"--source={REPO}",
                      f"--source-revision={revision}",
                      "--source-locator=bizplan/plan/p0.py")


@when(parsers.parse('I revise the document from a manifest viewing the budget as '
                    '"{renderer}"'), target_fixture="result")
def revise_doc(runner, ctx, renderer: str):
    path = _write(runner, "next-doc.json",
                  _manifest(ctx["budget"], {"renderer": renderer}))
    return runner.run("pub", "revise", ctx["doc"], f"--manifest={path}")


@when("I revise the document with no manifest", target_fixture="result")
def revise_doc_bare(runner, ctx):
    return runner.run("pub", "revise", ctx["doc"])


# --- thens -------------------------------------------------------------------


@then(parsers.parse('reading it shows "{fragment}"'))
def reading_shows(runner, ctx, fragment: str):
    shown = _read(runner, ctx["claim"])
    assert fragment in shown, shown


@then("nothing new is stored")
def nothing_stored(runner, ctx):
    assert _held(runner) == ctx["before"], "a refused object was stored anyway"


@then("the claim presupposes that claim")
def presupposes(runner, ctx):
    shown = _read(runner, ctx["claim"])
    after = shown.split("presupposes:", 1)
    assert len(after) == 2 and ctx["reason"] in after[1], shown


@then("the store holds that blob and no object for it")
def blob_held(runner, ctx):
    assert ctx["blob"] not in _held(runner)
    # The blob is fetched by the porcelain that cited it; reading the claim
    # names it, and the store's own object listing must not.
    assert ctx["blob"] in _read(runner, ctx["claim"])


@then(parsers.parse('reading the document shows "{fragment}"'))
def reading_doc_shows(runner, ctx, fragment: str):
    shown = _read(runner, ctx["docs"][-1])
    assert fragment in shown, shown


@then("the two documents are different objects citing the same claim")
def two_docs(runner, ctx):
    first, second = ctx["docs"]
    assert first != second
    assert ctx["budget"] in _read(runner, first)
    assert ctx["budget"] in _read(runner, second)


@then("it prints the new version and the supersedes relation")
def prints_two(result, ctx):
    lines = result.stdout.split()
    assert len(lines) == 2, result.stdout
    ctx["new"], ctx["relation"] = lines


@then("it prints only the budget claim")
def prints_old(result, ctx):
    assert result.stdout.split() == [ctx["budget"]], result.stdout


@then("the relation says the new version supersedes the budget claim")
def relation_supersedes(runner, ctx):
    shown = _read(runner, ctx["relation"])
    assert "kind      supersedes" in shown, shown
    assert f"from      {ctx['new']}" in shown, shown
    assert f"to        {ctx['budget']}" in shown, shown


@then("the new version keeps the budget claim's content and scope")
def keeps_content(runner, ctx):
    shown = _read(runner, ctx["new"])
    assert CONTENT in shown and SCOPE in shown, shown
    assert "revision abc123" in shown, shown


def _new_version(result, ctx) -> str:
    return ctx.get("new") or result.stdout.split()[0]


@then(parsers.parse('reading the new version shows "{fragment}"'))
def new_version_shows(runner, result, ctx, fragment: str):
    shown = _read(runner, _new_version(result, ctx))
    assert fragment in shown, shown


@then(parsers.parse('reading the new version does not show "{fragment}"'))
def new_version_hides(runner, result, ctx, fragment: str):
    shown = _read(runner, _new_version(result, ctx))
    assert fragment not in shown, shown


# --- quantities (Section 5.9) -----------------------------------------------

UCUM = {"sort": "system", "name": "UCUM", "version": "2.2"}
TRAY = {"sort": "dimension", "symbol": "{tray}"}
THREE_POINT = {
    "sort": "measure", "name": "three-point estimate", "describes": "uncertainty",
    "parameters": [
        {"name": "low", "type": "quantity", "meaning": "the least it plausibly is"},
        {"name": "likely", "type": "quantity", "meaning": "the most likely value"},
        {"name": "high", "type": "quantity", "meaning": "the most it plausibly is"},
    ],
}


def _define(runner, name: str, content: str, defines, *depends: str, cls="definitional"):
    args = ["compose", f"--class={cls}", f"--content={content}",
            "--scope=unconditional",
            f"--defines={_write(runner, name + '.json', defines)}"]
    args += [f"--depends={d}" for d in depends]
    return runner.run("pub", *args)


def _defined(runner, name: str, content: str, defines, *depends: str) -> str:
    out = _define(runner, name, content, defines, *depends)
    assert out.code == 0, out.stderr
    return out.stdout.split()[0]


@given("a workspace with the quantity definitions of publication 0", target_fixture="ctx")
def workspace_with_quantities(runner):
    assert runner.run("pub", "init").code == 0
    q = {}
    q["ucum"] = _defined(runner, "ucum", "UCUM: the Unified Code for Units of Measure, version 2.2.", UCUM)
    q["tray"] = _defined(runner, "tray", "tray: one 25 by 50 cm growing tray.", TRAY, q["ucum"])
    q["kind"] = _defined(runner, "kind",
                         "electrical energy per tray: electricity one tray uses from sowing to harvest.",
                         {"sort": "kind", "name": "electrical energy per tray",
                          "dimension": {"m": 2, "s": -2, "g": 1, "{tray}": -1},
                          "units": ["W.h/{tray}", "kW.h/{tray}"]},
                         q["ucum"], q["tray"])
    q["measure"] = _defined(runner, "measure",
                            "three-point estimate: a value as its least, likeliest and greatest plausible size.",
                            THREE_POINT)
    out = runner.run("pub", "compose", "--class=procedural", "--scope=unconditional",
                     "--content=Multiply the two inputs' bounds pairwise and keep the least and greatest products, rounding half to even to two places.")
    assert out.code == 0, out.stderr
    q["multiply"] = out.stdout.split()[0]
    out = runner.run("pub", "compose", "--class=procedural", "--scope=unconditional",
                     "--content=Log a tray's electricity with a plug meter from sowing to harvest.")
    assert out.code == 0, out.stderr
    q["method"] = out.stdout.split()[0]
    return {"q": q}


def _energy(ctx, cell) -> dict:
    q = ctx["q"]
    return {"columns": [{"name": "setup"},
                        {"name": "energy", "unit": "kW.h/{tray}",
                         "unit_defs": {"{tray}": q["tray"]},
                         "kind": q["kind"], "measure": q["measure"]}],
            "rows": [["LED, 12 h/day", cell]]}


ESTIMATE = {"low": "0.8", "likely": "1.1", "high": "1.4"}


@then(parsers.parse('reading the tray dimension shows "{fragment}"'))
def reading_tray(runner, ctx, fragment: str):
    shown = _read(runner, ctx["q"]["tray"])
    assert fragment in shown, shown


@when("I compose a normative claim defining", target_fixture="result")
def compose_normative_defining(runner, ctx, docstring: str):
    return _define(runner, "bad", "tray: a growing tray.", json.loads(docstring),
                   cls="normative")


@when("I compose a definitional claim defining", target_fixture="result")
def compose_definitional_defining(runner, ctx, docstring: str):
    return _define(runner, "bad", "x: something.", json.loads(docstring), ctx["q"]["ucum"])


@when("I compose a budget claim with energy per tray as three-point estimates",
      target_fixture="result")
def compose_estimates(runner, ctx):
    return _compose_budget(runner, ctx, _energy(ctx, ESTIMATE), f"--depends={ctx['q']['ucum']}")


@when(parsers.parse('I compose a budget claim with a measured column holding "{value}"'),
      target_fixture="result")
def compose_plain_in_measured(runner, ctx, value: str):
    return _compose_budget(runner, ctx, _energy(ctx, value))


@then("the claim presupposes the tray dimension, the kind and the measure")
def presupposes_quantities(runner, ctx):
    shown = _read(runner, ctx["claim"]).split("presupposes:", 1)
    assert len(shown) == 2, shown
    for name in ("tray", "kind", "measure"):
        assert ctx["q"][name] in shown[1], (name, shown[1])


@given("a store holding a claim whose column cites a unit claim not in depends",
       target_fixture="store")
def store_unit_unlisted(tmp_path):
    ka = author_key("K_a")
    tray = obj("claim.prose", ka, "2026-09-12T09:00:00Z", [
        ("class", text("definitional")),
        ("lang", text("en")),
        ("content", text("tray: one growing tray.")),
        ("scope", cbor_map([("domain", text("unconditional")),
                            ("conditions", head(4, 0))])),
        ("depends", head(4, 0)),
        ("defines", cbor_map([("sort", text("dimension")), ("symbol", text("{tray}"))])),
    ])
    data = cbor_map([
        ("columns", head(4, 1) + cbor_map([
            ("name", text("trays")),
            ("unit", text("{tray}")),
            ("unit_defs", cbor_map([("{tray}", text(cid_of(tray)))])),
        ])),
        ("rows", head(4, 0)),
    ])
    budget = obj("claim.prose", ka, "2026-09-12T10:00:00Z", [
        ("class", text("normative")),
        ("lang", text("en")),
        ("content", text(CONTENT)),
        ("scope", cbor_map([("domain", text("unconditional")),
                            ("conditions", head(4, 0))])),
        ("depends", head(4, 0)),
        ("data", data),
    ])
    write_store(tmp_path, [tray, budget])
    return {"dir": tmp_path}


def _concept(pdc: str, kind: str) -> dict:
    return {"sort": "concept", "pdc": pdc, "name": "LED shelf electricity per tray",
            "kind": kind,
            "boundary": {"includes": ["Indoor shelves lit only by LEDs"],
                         "excludes": ["Daylight greenhouses"]}}


@when(parsers.parse('I compose a concept at PDC code "{pdc}" narrowing the kind'),
      target_fixture="result")
def compose_concept(runner, ctx, pdc: str):
    out = _define(runner, "concept",
                  "LED shelf electricity per tray: electricity a tray on an LED-lit shelf uses.",
                  _concept(pdc, ctx["q"]["kind"]))
    if out.code == 0:
        ctx["concept"] = out.stdout.split()[0]
    return out


@then("the concept presupposes the kind")
def concept_presupposes_kind(runner, ctx):
    shown = _read(runner, ctx["concept"]).split("presupposes:", 1)
    assert len(shown) == 2, shown
    assert ctx["q"]["kind"] in shown[1], shown[1]


@given("a store holding a concept whose kind is not in depends", target_fixture="store")
def store_concept_kind_unlisted(tmp_path):
    ka = author_key("K_a")
    kind = obj("claim.prose", ka, "2026-09-12T09:00:00Z", [
        ("class", text("definitional")),
        ("lang", text("en")),
        ("content", text("count of trays: how many trays.")),
        ("scope", cbor_map([("domain", text("unconditional")),
                            ("conditions", head(4, 0))])),
        ("depends", head(4, 0)),
        ("defines", cbor_map([("sort", text("kind")), ("name", text("count of trays")),
                              ("dimension", cbor_map([("{tray}", uint(1))]))])),
    ])
    concept = obj("claim.prose", ka, "2026-09-12T10:00:00Z", [
        ("class", text("definitional")),
        ("lang", text("en")),
        ("content", text("trays on LED shelves: trays grown under LEDs only.")),
        ("scope", cbor_map([("domain", text("unconditional")),
                            ("conditions", head(4, 0))])),
        ("depends", head(4, 0)),
        ("defines", cbor_map([
            ("sort", text("concept")), ("pdc", text("631.544")),
            ("name", text("trays on LED shelves")), ("kind", text(cid_of(kind))),
            ("boundary", cbor_map([("includes", head(4, 0)), ("excludes", head(4, 0))])),
        ])),
    ])
    write_store(tmp_path, [kind, concept])
    return {"dir": tmp_path}


@given(parsers.parse('a concept at PDC code "{pdc}" narrowing the kind'))
def given_concept(runner, ctx, pdc: str):
    out = compose_concept(runner, ctx, pdc)
    assert out.code == 0, out.stderr


def _relation(runner, ctx, pdc: str):
    q = ctx["q"]
    deps = [ctx["concept"]] if "concept" in ctx else []
    relation = {"sort": "concept", "pdc": "631.544.9", "name": "LED share of tray energy",
                "relation": {
                    "statement": "the LED shelf energy is a share of a tray's energy",
                    "slots": [{"role": "led", "concept": pdc},
                              {"role": "energy", "kind": q["kind"]},
                              {"role": "share", "kind": q["kind"]}],
                    "form": {"product": {"coefficient": "1",
                                         "exponents": {"led": 1, "energy": -1, "share": -1}}}}}
    out = _define(runner, "relation", "LED share: LED shelf energy over a tray's energy.",
                  relation, *deps)
    if out.code == 0:
        ctx["relation"] = out.stdout.split()[0]
    return out


@when(parsers.parse('I compose a relation concept relating "{pdc}" to the kind'),
      target_fixture="result")
def compose_relation(runner, ctx, pdc: str):
    return _relation(runner, ctx, pdc)


@given(parsers.parse('a relation concept relating "{pdc}" to the kind'))
def given_relation(runner, ctx, pdc: str):
    out = _relation(runner, ctx, pdc)
    assert out.code == 0, out.stderr


@then("the relation concept presupposes the concept and the kind")
def relation_presupposes(runner, ctx):
    shown = _read(runner, ctx["relation"]).split("presupposes:", 1)
    assert len(shown) == 2, shown
    for cid in (ctx["concept"], ctx["q"]["kind"]):
        assert cid in shown[1], shown[1]


@when(parsers.parse('I compose a calculation solving the relation for "{target}" '
                    'with optional "{role}"'), target_fixture="result")
def compose_solving(runner, ctx, target: str, role: str):
    out = runner.run("pub", "compose", "--class=empirical", "--scope=unconditional",
                     f"--method={ctx['q']['method']}",
                     "--content=A tray uses no electricity beyond its LED shelf.")
    assert out.code == 0, out.stderr
    ctx["default"] = out.stdout.split()[0]
    solves = {"solves": {"concept": "631.544.9", "target": target, "requires": ["led"],
                         "optional": [{"role": role, "default": ctx["default"]}]}}
    out = runner.run("pub", "compose", "--class=procedural", "--scope=unconditional",
                     "--content=Divide the LED shelf energy by the tray's energy.",
                     f"--computes={_write(runner, 'solves.json', solves)}",
                     f"--depends={ctx['relation']}")
    if out.code == 0:
        ctx["calculation"] = out.stdout.split()[0]
    return out


@then("the calculation presupposes the relation concept and the default")
def calculation_presupposes(runner, ctx):
    shown = _read(runner, ctx["calculation"]).split("presupposes:", 1)
    assert len(shown) == 2, shown
    for cid in (ctx["relation"], ctx["default"]):
        assert cid in shown[1], shown[1]


def _empirical(runner, ctx, *evidence: str):
    q = ctx["q"]
    data = {"columns": [{"name": "setup"},
                        {"name": "climate cost", "unit": "kW.h/{tray}",
                         "unit_defs": {"{tray}": q["tray"]}, "measure": q["measure"]}],
            "rows": [["LED, 12 h/day", ESTIMATE]]}
    return runner.run(
        "pub", "compose", "--class=empirical", "--scope=home growing, Estonia",
        "--content=One tray under a 12 h/day LED uses this much electricity.",
        f"--data={_write(runner, 'derived.json', data)}", *evidence)


@when("I compose an empirical claim derived by the multiplication", target_fixture="result")
def compose_derived(runner, ctx):
    return _empirical(runner, ctx, f"--derivation={ctx['q']['multiply']}")


@when("I compose an empirical claim with both a method and a derivation",
      target_fixture="result")
def compose_both(runner, ctx):
    return _empirical(runner, ctx, f"--derivation={ctx['q']['multiply']}",
                      f"--method={ctx['q']['method']}")


def _energy_in(ctx, unit: str, cell=ESTIMATE, kind=None) -> dict:
    data = _energy(ctx, cell)
    data["columns"][1]["unit"] = unit
    if kind is not None:
        data["columns"][1]["kind"] = kind
    return data


@when("I compose a budget claim with trays per batch in the kind of energy per tray",
      target_fixture="result")
def compose_wrong_kind(runner, ctx):
    q = ctx["q"]
    q["batch"] = _defined(runner, "batch", "batch: trays sown together.",
                          {"sort": "dimension", "symbol": "{batch}"}, q["ucum"])
    data = _energy_in(ctx, "{tray}/{batch}")
    data["columns"][1]["unit_defs"]["{batch}"] = q["batch"]
    return _compose_budget(runner, ctx, data, f"--depends={q['ucum']}")


@when(parsers.parse('I compose a budget claim whose energy column is in "{unit}"'),
      target_fixture="result")
def compose_undeclared(runner, ctx, unit: str):
    return _compose_budget(runner, ctx, _energy_in(ctx, unit), f"--depends={ctx['q']['ucum']}")


@when("I compose a budget claim with energy per tray as the quantity", target_fixture="result")
def compose_quantity(runner, ctx, docstring: str):
    return _compose_budget(runner, ctx, _energy(ctx, json.loads(docstring)),
                           f"--depends={ctx['q']['ucum']}")


@given(parsers.parse('a definition of the system "{name}" version "{version}"'))
def another_system(runner, ctx, name: str, version: str):
    ctx["q"]["other"] = _defined(runner, "other", f"{name}: a system of units, version {version}.",
                                 {"sort": "system", "name": name, "version": version})


@when("I compose a budget claim with energy per tray under that system", target_fixture="result")
def compose_under_other(runner, ctx):
    return _compose_budget(runner, ctx, _energy(ctx, ESTIMATE), f"--depends={ctx['q']['other']}")


# --- pub bundle ----------------------------------------------------------------


def _bundle(runner, *parts: str) -> dict:
    path = runner.cwd.joinpath("bundles", *parts)
    assert path.is_file(), f"no bundle at {path}"
    return json.loads(path.read_text())


def _claim_bundle(runner, ctx) -> dict:
    return _bundle(runner, "o", f"{ctx['claim']}.json")


@when("I compose a budget claim with energy per tray not yet known", target_fixture="result")
def compose_unknown(runner, ctx):
    return _compose_budget(runner, ctx, _energy(ctx, None), f"--depends={ctx['q']['ucum']}")


@when(parsers.parse('I define another dimension named "{symbol}"'))
def define_again(runner, ctx, symbol: str):
    ctx["q"]["tray2"] = _defined(runner, "tray2", f"{symbol}: one 30 by 60 cm growing tray.",
                                 {"sort": "dimension", "symbol": symbol}, ctx["q"]["ucum"])


@when("I write the bundles", target_fixture="result")
def write_bundles(runner):
    return runner.run("pub", "bundle", "--out=bundles", "--title=Publication 0",
                      "--base=https://pub.example")


@when("I export the workspace's objects to a directory")
def export_objects(runner):
    objects = runner.cwd / "objects"
    objects.mkdir()
    for cid in sorted(_held(runner)):
        out = runner.run("pub-cat", "--store=.publet/objects.redb", cid)
        assert out.code == 0, out.stderr
        (objects / (cid.replace(":", "_") + ".cbor")).write_bytes(out.out)


@when("I write the bundles from that directory", target_fixture="result")
def write_bundles_from_dir(runner):
    (runner.cwd / ".publet").rename(runner.cwd / "moved-away")
    return runner.run("pub", "bundle", "--dir=objects", "--out=bundles",
                      "--base=https://pub.example")


@given("the bundle directory already holds a file")
def bundles_not_empty(runner):
    (runner.cwd / "bundles").mkdir()
    (runner.cwd / "bundles" / "old.json").write_text("{}")


@then("the claim's bundle holds its content and scope")
def claim_bundle(runner, ctx):
    b = _claim_bundle(runner, ctx)
    assert b["bundle"] == 1, b
    body = b["object"]["body"]
    assert body["content"] == CONTENT, body
    assert body["scope"]["domain"] == SCOPE, body


@then("the claim's bytes are served at its identifier, unchanged")
def claim_bytes(runner, ctx):
    served = (runner.cwd / "bundles" / "pub" / "v1" / "object" / ctx["claim"]).read_bytes()
    stored = runner.run("pub-cat", "--store=.publet/objects.redb", ctx["claim"])
    assert stored.code == 0, stored.stderr
    assert served == stored.out
    assert _claim_bundle(runner, ctx)["bytes"]["path"] == f"pub/v1/object/{ctx['claim']}"


@then("the index lists the claim with its bundle's path")
def index_lists(runner, ctx):
    index = _bundle(runner, "index.json")
    entry = next(o for o in index["objects"] if o["cid"] == ctx["claim"])
    assert entry["path"] == f"o/{ctx['claim']}.json", entry
    assert entry["class"] == "normative", entry


@then("the claim's bundle says it rests on the tray dimension as its unit, the kind and the measure")
def rests_on(runner, ctx):
    how = {e["cid"]: e["how"] for e in _claim_bundle(runner, ctx)["rests_on"]}
    q = ctx["q"]
    assert how.get(q["tray"]) == "unit", how
    assert how.get(q["kind"]) == "kind", how
    assert how.get(q["measure"]) == "measure", how


@then("the claim's bundle gives the measure's parameters as low, likely and high")
def parameters(runner, ctx):
    b = _claim_bundle(runner, ctx)
    assert b["parameters"][ctx["q"]["measure"]] == ["low", "likely", "high"], b["parameters"]


@then("the claim's bundle summarizes every object it rests on")
def related(runner, ctx):
    b = _claim_bundle(runner, ctx)
    for edge in b["rests_on"]:
        assert b["related"][edge["cid"]]["held"] is True, edge
    assert b["related"][ctx["q"]["tray"]]["label"] == "{tray}", b["related"]


@then("the tray dimension's bundle says the claim uses it as a unit")
def used_by(runner, ctx):
    b = _bundle(runner, "o", f"{ctx['q']['tray']}.json")
    assert {"cid": ctx["claim"], "how": "unit of"} in b["used_by"], b["used_by"]


@then("the claim's bundle holds a null cell")
def null_cell(runner, ctx):
    rows = _claim_bundle(runner, ctx)["object"]["body"]["data"]["rows"]
    assert rows[0][1] is None, rows


@then(parsers.parse('the name "{name}" has a bundle naming the tray dimension'))
def name_bundle(runner, ctx, name: str):
    b = _bundle(runner, "def", f"{name}.json")
    assert b["definitions"] == [ctx["q"]["tray"]], b


@when(parsers.parse('I place the concept under a subject concept at "{pdc}" and classify the '
                    'budget claim under it'))
def place_concept(runner, ctx, pdc: str):
    ctx["subject"] = _defined(runner, "subject", f"{pdc}: a subject.",
                              {"sort": "concept", "pdc": pdc, "name": "a subject"})
    out = compose_estimates(runner, ctx)
    assert out.code == 0, out.stderr
    ctx["budget"] = out.stdout.split()[0]
    for target, subject in ((ctx["concept"], ctx["subject"]), (ctx["budget"], ctx["concept"])):
        out = runner.run("pub", "annotate", "--kind=classifies", f"--target={target}",
                         f"--subject={subject}", "--scope=unconditional")
        assert out.code == 0, out.stderr


@then(parsers.parse('the concept\'s bundle says it is a quantity concept under "{pdc}" with the '
                    'budget claim as a member'))
def concept_bundle(runner, ctx, pdc: str):
    c = _bundle(runner, "o", f"{ctx['concept']}.json")["concept"]
    assert c["form"] == "quantity" and c["broader"] == [ctx["subject"]], c
    assert [m["cid"] for m in c["members"]] == [ctx["budget"]], c


@then("the budget claim's bundle says it is classified under the concept")
def classified_under(runner, ctx):
    b = _bundle(runner, "o", f"{ctx['budget']}.json")
    assert [u["concept"] for u in b["classified_under"]] == [ctx["concept"]], b


@when(parsers.parse('I define a subject concept at "{pdc}"'))
def define_subject(runner, ctx, pdc: str):
    _defined(runner, "subject", f"{pdc}: a range of subjects.",
             {"sort": "concept", "pdc": pdc, "name": "a range"})


@then(parsers.parse('the name "{name}" has its bundle at "{path}" and the address "{address}"'))
def name_path(runner, name: str, path: str, address: str):
    b = _bundle(runner, *path.split("/"))
    assert b["name"] == name and b["address"] == address, b
    assert _bundle(runner, "index.json")["name_paths"][name] == path


@then(parsers.parse('the name "{name}" has the address "{address}"'))
def name_address(runner, name: str, address: str):
    assert _bundle(runner, "def", f"{name}.json")["address"] == address


@then(parsers.parse('the name "{name}" has a bundle naming both definitions'))
def name_lists_both(runner, ctx, name: str):
    b = _bundle(runner, "def", f"{name}.json")
    assert sorted(b["definitions"]) == sorted([ctx["q"]["tray"], ctx["q"]["tray2"]]), b
