"""Steps for `pub sign --restore-key`: a key rebuilt from its secret alone."""

from __future__ import annotations

import shutil

from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/porcelain/sign.feature")


@given("a workspace whose key was generated, and its secret kept", target_fixture="kept")
def generated(runner, scratch):
    first = scratch / "first"
    first.mkdir()
    assert runner.run("pub", "init", cwd=first).returncode == 0
    out = runner.run("pub", "sign", "--generate-key", "--principal=human", cwd=first)
    assert out.returncode == 0, out.stderr
    key = out.stdout.split()[1]
    secret = scratch / "kept.key"
    shutil.copy(first / ".publet" / "signing.key", secret)
    return {"key": key, "secret": secret}


def _fresh(runner, scratch, name):
    where = scratch / name
    where.mkdir()
    assert runner.run("pub", "init", cwd=where).returncode == 0
    return where


@given("a fresh workspace holding only that secret", target_fixture="here")
def fresh_with_secret(runner, scratch, kept):
    where = _fresh(runner, scratch, "second")
    shutil.copy(kept["secret"], where / ".publet" / "signing.key")
    return where


@given("a fresh workspace without a secret", target_fixture="here")
def fresh_without(runner, scratch):
    return _fresh(runner, scratch, "second")


@given("a workspace with a key of its own, holding that secret instead", target_fixture="here")
def own_key(runner, scratch, kept):
    where = _fresh(runner, scratch, "second")
    assert runner.run("pub", "sign", "--generate-key", "--principal=human", cwd=where).returncode == 0
    shutil.copy(kept["secret"], where / ".publet" / "signing.key")
    return where


@when(parsers.re(r'I run pub (?P<args>(?:"[^"]*" ?)+)$'), target_fixture="result")
def run_pub(runner, here, kept, args):
    argv = [a.replace("{key}", kept["key"]) for a in args.strip().strip('"').split('" "')]
    return runner.act("pub", *argv, cwd=here)


@then(parsers.parse('it prints "key      {{key}}"'))
def prints_key(result, kept):
    assert f"key      {kept['key']}" in result.stdout, result.stdout


@then(parsers.re(r'stderr mentions "(?P<text>.*\{key\}.*)"'))
def stderr_names_key(result, kept, text):
    assert text.replace("{key}", kept["key"]) in result.stderr, result.stderr


def _author(here) -> str:
    for line in (here / ".publet" / "config").read_text().splitlines():
        if line.startswith("author="):
            return line.split("=", 1)[1]
    return ""


@then("the workspace's author is that key")
def author_is(here, kept):
    assert _author(here) == kept["key"]


@then("the workspace's author is not that key")
def author_is_not(here, kept):
    assert _author(here) != kept["key"]


@then("the workspace signs with it")
def signs(runner, here, kept):
    out = runner.run("pub", "compose", "--class=archival", "--content=Restored keys sign.",
                     "--scope=this scenario", cwd=here)
    assert out.returncode == 0, out.stderr
    claim = out.stdout.strip()
    signed = runner.run("pub", "sign", "--purpose=authored", f"--target={claim}", cwd=here)
    assert signed.returncode == 0, signed.stderr


SOURCE = """{"slug": "doc.a", "tag": "DOC-AAAAAA-11-2026", "title": "a", "created": "2026-11-19T00:00:00Z",
 "claims": {"identity": {"class": "archival", "scope": "a test", "content": "A test.",
                         "sources": [{"ref": "t", "revision": "x"}]}},
 "sections": [{"heading": "I", "items": [{"ref": "#identity"}]}]}
"""


@given(parsers.parse('a corpus whose key, labelled "{label}", signed a publish, and its secret kept'),
       target_fixture="kept")
def published_corpus(runner, scratch, label):
    corpus = scratch / "corpus"
    (corpus / "publets" / "doc.a").mkdir(parents=True)
    assert runner.run("pub", "corpus", "init", cwd=corpus).returncode == 0
    out = runner.run("pub", "sign", "--generate-key", "--principal=human", f"--label={label}", cwd=corpus)
    assert out.returncode == 0, out.stderr
    (corpus / "publets" / "doc.a" / "publet.json").write_text(SOURCE)
    assert runner.run("pub", "build", cwd=corpus).returncode == 0
    published = runner.run("pub", "publish", "doc.a", cwd=corpus)
    assert published.returncode == 0, published.stderr
    secret = scratch / "kept.key"
    shutil.copy(corpus / ".publet" / "signing.key", secret)
    return {"key": out.stdout.split()[1], "secret": secret, "corpus": corpus}


def _fresh_store(runner, corpus):
    shutil.rmtree(corpus / ".publet")
    assert runner.run("pub", "init", cwd=corpus).returncode == 0


@given("the corpus's store is gone, its secret put back", target_fixture="here")
def store_gone_secret_back(runner, kept):
    _fresh_store(runner, kept["corpus"])
    shutil.copy(kept["secret"], kept["corpus"] / ".publet" / "signing.key")
    return kept["corpus"]


@given("the corpus's store is gone, another secret in its place", target_fixture="here")
def store_gone_other_secret(runner, kept):
    _fresh_store(runner, kept["corpus"])
    (kept["corpus"] / ".publet" / "signing.key").write_text("ab" * 32 + "\n")
    return kept["corpus"]
