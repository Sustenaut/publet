"""Steps for checking generation records' signatures (Section 14.1.1)."""

from __future__ import annotations

from pytest_bdd import given, parsers, scenarios, then, when

from support.objects import cid_of, head, obj, text, uint
from support.signing import CREATED, Key

scenarios("../features/conformance/record_signatures.feature")


def arr(items: list[bytes]) -> bytes:
    return head(4, len(items)) + b"".join(items)


def _root(runner, members: list[str]) -> str:
    out = runner.run("pub-merkle", stdin=("\n".join(sorted(members)) + "\n").encode())
    assert out.code == 0, out.stderr
    return out.stdout.strip()


def _write(where, data: bytes) -> None:
    (where / (cid_of(data).replace(":", "_") + ".cbor")).write_bytes(data)


@given("a domain at generation 0 with one member, and its publisher's key", target_fixture="domain")
def domain(tmp_path):
    publisher = Key("the publisher")
    _write(tmp_path, publisher.object)
    return {"dir": tmp_path, "members": [cid_of(b"the first member")], "publisher": publisher,
            "other": Key("someone else"), "domain": cid_of(b"the domain"), "parent": cid_of(b"g0")}


def _records(runner, domain, authors: list[Key]) -> list[bytes]:
    out = []
    members = list(domain["members"])
    parent = domain["parent"]
    for index, author in enumerate(authors, start=1):
        added = cid_of(f"member {index}".encode())
        members.append(added)
        record = obj("generation", author.cid, CREATED, [
            ("domain", text(domain["domain"])), ("index", uint(index)),
            ("parent", text(parent)), ("snapshot", text(_root(runner, members))),
            ("added", arr([text(added)])), ("removed", arr([])),
        ])
        parent = cid_of(record)
        out.append(record)
    return out


def _place(domain, records: list[bytes], signatures: list[bytes | None]) -> None:
    for record, signature in zip(records, signatures):
        _write(domain["dir"], record)
        if signature is not None:
            _write(domain["dir"], signature)


@given("two records, both signed by the publisher")
def both_signed(runner, domain):
    k = domain["publisher"]
    records = _records(runner, domain, [k, k])
    _place(domain, records, [k.sign(r) for r in records])


@given("two records, neither signed")
def neither_signed(runner, domain):
    k = domain["publisher"]
    _place(domain, _records(runner, domain, [k, k]), [None, None])


@given("two records, the first signed by the publisher and the second unsigned")
def second_unsigned(runner, domain):
    k = domain["publisher"]
    records = _records(runner, domain, [k, k])
    _place(domain, records, [k.sign(records[0]), None])


@given("two records, the second signed by another key")
def second_wrong_key(runner, domain):
    k, other = domain["publisher"], domain["other"]
    records = _records(runner, domain, [k, k])
    _write(domain["dir"], other.object)
    _place(domain, records, [k.sign(records[0]), other.sign(records[1])])


@given("two records, the second with its signature altered")
def second_altered_signature(runner, domain):
    k = domain["publisher"]
    records = _records(runner, domain, [k, k])
    good = k.private.sign(b"pub/v1/sig\x00authored\x00" + records[1])
    _place(domain, records, [k.sign(records[0]), k.sign(records[1], value=bytes([good[0] ^ 1]) + good[1:])])


@given("two records, both signed, and the second altered after signing")
def second_altered_record(runner, domain):
    k = domain["publisher"]
    records = _records(runner, domain, [k, k])
    signatures = [k.sign(r) for r in records]
    # Same index and parent; one more member, so the bytes and the CID differ.
    altered = obj("generation", k.cid, "2026-11-03T00:00:01Z", [
        ("domain", text(domain["domain"])), ("index", uint(2)),
        ("parent", text(cid_of(records[0]))),
        ("snapshot", text(_root(runner, [*domain["members"], cid_of(b"member 1"),
                                         cid_of(b"member 2")]))),
        ("added", arr([text(cid_of(b"member 2"))])), ("removed", arr([])),
    ])
    _place(domain, [records[0], altered], [signatures[0], None])
    _write(domain["dir"], signatures[1])


@given("two records, the second written and signed by another key")
def second_other_publisher(runner, domain):
    k, other = domain["publisher"], domain["other"]
    records = _records(runner, domain, [k, other])
    _write(domain["dir"], other.object)
    _place(domain, records, [k.sign(records[0]), other.sign(records[1])])


@when("I apply the records", target_fixture="result")
def apply_records(runner, domain):
    return runner.run("pub-delta", f"--dir={domain['dir']}", "--from=0",
                      *(f"--member={m}" for m in domain["members"]))


@then("it succeeds")
def it_succeeds(result):
    assert result.code == 0, result.stderr


@then("it fails")
def it_fails(result):
    assert result.code == 1, (result.code, result.stdout, result.stderr)


@then(parsers.parse('stderr does not mention "{fragment}"'))
def stderr_lacks(result, fragment: str):
    assert fragment not in result.stderr, result.stderr
