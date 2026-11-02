"""The small PDC the family scenarios use, and the vectors built from it.

Five families and an edition: the top family, the common auxiliaries under
`-`, the main tables under `----` and `6`, and a special auxiliary's family
under `62-1/-9`. The vectors in `vectors/families/` are written from this,
without the code under test: `python tests/support/family_vectors.py`
rewrites them, and a scenario checks the committed files are what this makes.
Each case is a directory, because what makes an edition wrong is usually
another object.
"""

from __future__ import annotations

import copy
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from support.objects import (  # noqa: E402
    author_key, cbor_map, cid_of, head, obj, publet, text, uint,
)

VECTORS = Path(__file__).resolve().parents[2] / "vectors" / "families"
STEWARD = author_key("the PDC steward")
CREATED = "2026-11-02T12:00:00Z"


def _klass(pdc: str, name: str, children: bool = False) -> dict:
    return {"pdc": pdc, "name": name, **({"children": True} if children else {})}


# Parent code (None for the top family) -> its `defines`, in the order a
# family's parent is defined before it.
FAMILIES: dict[str | None, dict] = {
    None: {"sort": "family", "grouping": 1, "members": [
        _klass("-", "AUXILIARY TABLES", True), _klass("----", "MAIN TABLES", True)]},
    "-": {"sort": "family", "parent": "-", "grouping": 1, "members": [_klass("(1/9)", "Place")]},
    "----": {"sort": "family", "parent": "----", "grouping": 1, "members": [
        _klass("6", "Applied sciences", True)]},
    "6": {"sort": "family", "parent": "6", "grouping": 2, "members": [_klass("63", "Agriculture")],
          "auxiliaries": [_klass("62-1/-9", "Engineering properties", True)]},
    "62-1/-9": {"sort": "family", "parent": "62-1/-9", "grouping": 2, "members": [
        _klass("62-1", "Features of machines")]},
}
SECTION_OF = {"-": "common-auxiliaries", "----": "main", "6": "main",
              "62-1/-9": "special-auxiliaries"}


def families() -> dict[str | None, dict]:
    """A copy to break."""
    return copy.deepcopy(FAMILIES)


def edition_of(cids: dict[str | None, str]) -> dict:
    """The edition's `defines`, given each family's CID by parent code."""
    sections: dict[str, dict] = {"main": {}, "common-auxiliaries": {}, "special-auxiliaries": {}}
    for parent, section in SECTION_OF.items():
        if parent in cids:
            sections[section][parent] = cids[parent]
    return {
        "sort": "edition",
        "top": cids[None],
        "sections": sections,
        "groups": [{"number": 1, "heads": ["(1/9)", "\"...\""]}, {"number": 2, "heads": ["62-1/-9"]}],
        # Grouping 3 is defined and no family uses it: dropping it breaks only the
        # grow-only rule.
        "groupings": [{"number": 1, "groups": [1]}, {"number": 2, "groups": [1, 2]},
                      {"number": 3, "groups": [2]}],
        "counts": {
            "main": {"families": 2, "classes": 2, "auxiliaries": 1},
            "common-auxiliaries": {"families": 1, "classes": 1, "auxiliaries": 0},
            "special-auxiliaries": {"families": 1, "classes": 1, "auxiliaries": 0},
            "total": {"families": 5, "classes": 6, "auxiliaries": 1},
            "groups": 2,
            "groupings": 3,
        },
    }


def content_of(parent: str | None) -> str:
    return f"The PDC classes directly under {parent}." if parent else "The roots of the PDC."


def encode(value) -> bytes:
    if isinstance(value, bool):
        return bytes([0xF5 if value else 0xF4])
    if isinstance(value, int):
        return uint(value)
    if isinstance(value, str):
        return text(value)
    if isinstance(value, list):
        return head(4, len(value)) + b"".join(encode(v) for v in value)
    return cbor_map([(k, encode(v)) for k, v in value.items()])


def claim(content: str, defines: dict, depends: tuple[str, ...] = ()) -> bytes:
    return obj("claim.prose", STEWARD, CREATED, [
        ("class", text("definitional")),
        ("lang", text("en")),
        ("content", text(content)),
        ("scope", encode({"domain": "unconditional", "conditions": []})),
        ("depends", encode(list(depends))),
        ("evidence", encode([])),
        ("defines", encode(defines)),
    ])


def supersedes(new: str, old: str) -> bytes:
    return obj("claim.relation", STEWARD, CREATED, [
        ("kind", text("supersedes")),
        ("from", text(new)),
        ("to", text(old)),
        ("scope", encode({"domain": "unconditional", "conditions": []})),
    ])


def release(fams: dict[str | None, dict] | None = None, edit=None) -> tuple[list[bytes], bytes]:
    """The families' objects and an edition of them, after `edit(edition)`."""
    fams = FAMILIES if fams is None else fams
    objects = {parent: claim(content_of(parent), d) for parent, d in fams.items()}
    defines = edition_of({parent: cid_of(o) for parent, o in objects.items()})
    if edit:
        edit(defines)
    return list(objects.values()), claim("The PDC, edition 1.", defines)


def _with(parent, change) -> dict:
    fams = families()
    change(fams[parent])
    return fams


def _set(*path):
    """Set the value at a path, its last argument, in an edition."""
    def apply(edition):
        at = edition
        for key in path[:-2]:
            at = at[key]
        at[path[-2]] = path[-1]
    return apply


def _bad_family(defines: dict) -> list[bytes]:
    return [claim("The PDC classes directly under 63.", defines)]


_FAMILY = {"sort": "family", "parent": "63", "grouping": 1}
_MEMBER = {"pdc": "631", "name": "Horticulture"}


def _superseding(edit) -> list[bytes]:
    """A release, and a second edition of it superseding the first."""
    objects, first = release()
    _, second = release(edit=edit)
    if second == first:
        raise ValueError("the edit changed nothing")
    return [*objects, first, second, supersedes(cid_of(second), cid_of(first))]


def _grow(edition):
    edition["groups"][0]["heads"].append("(4)")
    edition["groups"].append({"number": 3, "heads": ["(5)"]})
    edition["groupings"].append({"number": 4, "groups": [3]})
    edition["counts"]["groups"] = 3
    edition["counts"]["groupings"] = 4


def _lost_a_head(edition):
    edition["groups"][0]["heads"] = ["(1/9)"]


def _one_fewer_heads(edition):
    edition["groupings"][1]["groups"] = [2]


def _drop_grouping(edition):
    edition["groupings"].pop()
    edition["counts"]["groupings"] = 2


def _pair(families_objects, edition):
    return [*families_objects, edition]


GROUNDS = publet(STEWARD, CREATED, "normative", "It should be otherwise.")
_SCOPE = {"domain": "unconditional", "conditions": []}
_ANNOTATIONS = {
    "assessment": {"verdict": "refuted"},
    "verdict": {"finding": "deny"},
    "critique": {"defect": "other"},
}


def annotation(kind: str, target: str, value: dict, aspect: str | None = None) -> bytes:
    fields = [("kind", text(kind)), ("target", text(target)), ("scope", encode(_SCOPE)),
              ("value", encode(value))]
    if aspect:
        fields.append(("aspect", text(aspect)))
    return obj("claim.annotation", STEWARD, CREATED, fields)


def argued(kind: str, target: str, aspect: str | None = None) -> bytes:
    fields = [("kind", text(kind)), ("from", text(cid_of(GROUNDS))), ("to", text(target)),
              ("scope", encode(_SCOPE))]
    if aspect:
        fields.append(("aspect", text(aspect)))
    return obj("claim.relation", STEWARD, CREATED, fields)


def _debates(name: str, target: bytes, aspect: str | None) -> dict:
    """One case per kind of argument or judgement against `target`."""
    out = {}
    for kind in ("disputes", "supports"):
        out[f"drop-{name}-{kind}"] = (
            [target, GROUNDS, argued(kind, cid_of(target), aspect)],
            f"a `{kind}` cannot target")
    for kind, value in _ANNOTATIONS.items():
        # Section 5.2 refuses a verdict on any definitional claim, first.
        rule = "definitional" if kind == "verdict" else f"a `{kind}` cannot target"
        out[f"drop-{name}-{kind}"] = (
            [target, annotation(kind, cid_of(target), value, aspect)], rule)
    return out


def _allowed_uses() -> list[bytes]:
    """Everything a family still admits, on one family."""
    family = claim(content_of("6"), FAMILIES["6"])
    at = cid_of(family)
    placed = publet(STEWARD, CREATED, "normative", "Grow it here.")
    citing = obj("claim.prose", STEWARD, CREATED, [
        ("class", text("empirical")), ("lang", text("en")),
        ("content", text("The yield rose.")),
        ("scope", encode(_SCOPE)),
        ("depends", encode([at])),
        ("evidence", encode([{"kind": "claim", "role": "method", "ref": at}])),
    ])
    return [
        family, placed, citing, GROUNDS,
        annotation("classifies", cid_of(placed), {"subject": at}, "63"),
        annotation("usage", at, {"source": "https://example.org/udc", "locator": "p. 63"}, "63"),
        annotation("tagged", at, {"tag": "PUB-FAMILY-11-2026"}),
        annotation("timestamped", at, {"at": CREATED, "service": "https://example.org/ts",
                                       "proof": "a proof"}),
        obj("claim.relation", STEWARD, CREATED, [
            ("kind", text("retracts")), ("from", text(cid_of(GROUNDS))), ("to", text(at)),
            ("scope", encode(_SCOPE))]),
    ]


OTHER_KEY = author_key("someone else")


def revision(author: str) -> list[bytes]:
    """A family, and a next version of it by `author`."""
    family = claim(content_of("6"), FAMILIES["6"])
    grown = copy.deepcopy(FAMILIES["6"])
    grown["members"].append(_klass("64", "Home economics"))
    newer = obj("claim.prose", author, CREATED, [
        ("class", text("definitional")), ("lang", text("en")),
        ("content", text(content_of("6"))), ("scope", encode(_SCOPE)),
        ("depends", encode([])), ("evidence", encode([])), ("defines", encode(grown)),
    ])
    edge = obj("claim.relation", author, CREATED, [
        ("kind", text("supersedes")), ("from", text(cid_of(newer))), ("to", text(cid_of(family))),
        ("scope", encode(_SCOPE))])
    return [family, newer, edge]


def _argued_proposal() -> list[bytes]:
    """A proposal, with an argument for it and a reply on its relation."""
    objects = revision(OTHER_KEY)
    edge = cid_of(objects[-1])
    return [*objects, GROUNDS, argued("supports", edge), argued("disputes", edge)]


def _delegated_revision() -> list[bytes]:
    return [*revision(OTHER_KEY), obj("claim.relation", STEWARD, CREATED, [
        ("kind", text("delegates")), ("from", text(STEWARD)), ("to", text(OTHER_KEY)),
        ("aspect", text("lineage")), ("effective", text("immediate")),
        ("scope", encode(_SCOPE))])]


# Case name -> (the objects, what a refusal must name). `None` must load whole.
# A `reject-` case makes the load fail: an object that cannot be read. A `drop-`
# case loads with one object left out and reported (Section 5.2).
def cases() -> dict[str, tuple[list[bytes], str | None]]:
    out: dict[str, tuple[list[bytes], str | None]] = {}

    out["accept-edition"] = (_pair(*release()), None)
    out["accept-edition-that-grew"] = (_superseding(_grow), None)

    # A family alone.
    out["reject-family-code-twice"] = (
        _bad_family({**_FAMILY, "members": [_MEMBER, _MEMBER]}), "each code once")
    out["reject-family-code-in-both-lists"] = (
        _bad_family({**_FAMILY, "members": [_MEMBER], "auxiliaries": [_MEMBER]}), "each code once")
    out["reject-family-parent-is-a-member"] = (
        _bad_family({**_FAMILY, "members": [{"pdc": "63", "name": "Agriculture"}]}),
        "defines.parent")
    out["reject-family-no-classes"] = (_bad_family({**_FAMILY, "members": []}), "at least one class")
    out["reject-family-no-grouping"] = (
        _bad_family({"sort": "family", "parent": "63", "members": [_MEMBER]}), "defines.grouping")
    out["reject-family-member-with-sort"] = (
        _bad_family({**_FAMILY, "members": [{**_MEMBER, "sort": "concept"}]}), "without `sort`")
    out["reject-family-children-false"] = (
        _bad_family({**_FAMILY, "members": [{**_MEMBER, "children": False}]}),
        "defines.members.children")
    out["reject-family-kind-not-in-depends"] = (
        _bad_family({**_FAMILY, "members": [
            {**_MEMBER, "kind": cid_of(b"a kind"),
             "boundary": {"includes": ["Fruit"], "excludes": []}}]}),
        "defines.kind")

    # An edition alone.
    out["reject-edition-no-section"] = (
        _pair(*release(edit=lambda e: e["sections"].pop("main"))), "defines.sections")
    out["reject-edition-grouping-of-undefined-group"] = (
        _pair(*release(edit=_set("groupings", 0, "groups", [9]))), "defines.groupings")
    out["reject-edition-number-twice"] = (
        _pair(*release(edit=_set("groups", 1, "number", 1))), "each number once")
    out["reject-edition-empty-group"] = (
        _pair(*release(edit=_set("groups", 0, "heads", []))), "at least one head")
    out["reject-edition-count-of-groups"] = (
        _pair(*release(edit=_set("counts", "groups", 5))), "defines.counts")
    out["reject-edition-count-of-listed-families"] = (
        _pair(*release(edit=_set("counts", "main", "families", 9))), "defines.counts")

    # An edition against its families.
    out["drop-edition-count-of-classes"] = (
        _pair(*release(edit=_set("counts", "main", "classes", 9))), "its counts give `main`")
    out["drop-edition-count-of-auxiliaries-in-total"] = (
        _pair(*release(edit=_set("counts", "total", "auxiliaries", 9))), "its counts give `total`")
    out["drop-edition-child-not-flagged"] = (
        _pair(*release(_with("----", lambda f: f["members"][0].pop("children")))),
        "6 heads a family and has no `children` flag")
    out["drop-edition-flag-with-no-family"] = (
        _pair(*release(_with("6", lambda f: f["members"][0].update(children=True)))),
        "63 has a `children` flag and no family under it")
    out["drop-edition-undefined-grouping"] = (
        _pair(*release(_with("6", lambda f: f.update(grouping=7)))),
        "names the grouping 7, which the edition does not define")
    out["drop-edition-parent-disagrees"] = (
        _pair(*release(_with("6", lambda f: f.update(parent="7")))),
        "the family listed under 6 states the parent")
    out["drop-edition-top-with-parent"] = (
        _pair(*release(_with(None, lambda f: f.update(parent="0")))),
        "the top family states the parent")

    def code_twice(fam):
        fam["members"].append({"pdc": "(1/9)", "name": "Place, again"})
    out["drop-edition-code-in-two-families"] = (
        _pair(*release(_with("6", code_twice))), "define (1/9) twice")

    # An edition against the one it supersedes.
    out["drop-edition-group-lost-a-head"] = (
        _superseding(_lost_a_head),
        'group 1 lost "\\"...\\""')
    out["drop-edition-number-reused"] = (
        _superseding(_set("groups", 1, "heads", ["(4)"])),
        "group 2 is reused with a different meaning")
    out["drop-edition-grouping-lost-a-group"] = (
        _superseding(_one_fewer_heads), "grouping 2 lost 1")
    out["drop-edition-number-dropped"] = (
        _superseding(_drop_grouping), "grouping 3 of the edition it supersedes is gone")

    # A stipulation changes by a new version and is never debated.
    family = claim(content_of("6"), FAMILIES["6"])
    out.update(_debates("family", family, None))
    out.update({k + "-on-a-code": v for k, v in _debates("family", family, "63").items()})
    _, edition = release()
    out.update(_debates("edition", edition, None))
    concept = claim("63: agriculture.", {"sort": "concept", "pdc": "63", "name": "agriculture"})
    out.update(_debates("concept", concept, None))
    placed = publet(STEWARD, CREATED, "normative", "Grow it here.")
    out["drop-classifies-under-no-class"] = (
        [family, placed, annotation("classifies", cid_of(placed), {"subject": cid_of(family)}, "64")],
        "must name one of its codes")
    out["accept-family-allowed-uses"] = (_allowed_uses(), None)
    out["accept-family-revised-by-its-steward"] = (revision(STEWARD), None)
    out["accept-family-revised-by-a-delegate"] = (_delegated_revision(), None)
    out["accept-family-change-proposed-by-another-key"] = (revision(OTHER_KEY), None)
    out["accept-proposal-argued-on-its-relation"] = (_argued_proposal(), None)
    return out


def write() -> None:
    """Rewrite `vectors/families/` from the cases."""
    if VECTORS.exists():
        shutil.rmtree(VECTORS)
    rows = []
    for name, (objects, rule) in sorted(cases().items()):
        where = VECTORS / name
        where.mkdir(parents=True)
        for data in objects:
            (where / (cid_of(data).replace(":", "_") + ".cbor")).write_bytes(data)
        rows.append(f"{name}\t{rule or 'accepted'}")
    (VECTORS / "EXPECTED.tsv").write_text("\n".join(rows) + "\n")


if __name__ == "__main__":
    write()
