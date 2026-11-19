"""Steps for scripts.feature: the maintainer scripts in tools/ and spec/,
each loaded as a module and run in-process, as pubtest's `attempt`, so that
pubtest's steps read what each returned, raised and printed."""

from __future__ import annotations

import bz2
import importlib.util
import json
import runpy
import shlex
import sys
import urllib.request
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("scripts.feature")

ROOT = Path(__file__).resolve().parent.parent.parent


def load(relative: str):
    """The script at `relative` (from the repository root), as a module."""
    path = ROOT / relative
    name = path.stem.replace("-", "_")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


audit = load("spec/audit.py")
must_coverage = load("tools/must-coverage.py")
wiki_seed = load("tools/wiki-seed.py")
vectors = load("tools/vectors/generate.py")

SCRIPTS = {"spec/audit.py": audit, "tools/must-coverage.py": must_coverage, "tools/wiki-seed.py": wiki_seed}


# --- running a script --------------------------------------------------------

def _argv(monkeypatch, name: str, arguments: str) -> None:
    monkeypatch.setattr(sys, "argv", [name, *shlex.split(arguments)])


@when(parsers.parse('the script "{script}" runs'))
def script_runs(ctx, monkeypatch, script):
    _argv(monkeypatch, SCRIPTS[script].__name__, "")
    ctx.attempt(SCRIPTS[script].main)


@when(parsers.parse('the script "{script}" runs with "{arguments}"'))
def script_runs_with(ctx, monkeypatch, script, arguments):
    _argv(monkeypatch, SCRIPTS[script].__name__, arguments)
    ctx.attempt(SCRIPTS[script].main)


@when(parsers.parse('the program "{script}" runs with "{arguments}"'))
def program_runs_with(ctx, monkeypatch, script, arguments):
    """The script run as `python SCRIPT`, its `__main__` block too."""
    _argv(monkeypatch, Path(script).name, arguments)
    ctx.attempt(lambda: runpy.run_path(str(ROOT / script), run_name="__main__"))


# --- confined: the same rule in each script ----------------------------------

@when(parsers.parse('the script {script} confines "{path}"'))
def confines(ctx, script, path):
    ctx.attempt(lambda: SCRIPTS[script].confined(path, "--x"))


@when(parsers.parse("the script {script} confines a file in a temporary directory"))
def confines_temporary(ctx, tmp_path, script):
    # From the repository root, so that only the temporary-directory rule
    # can admit it.
    ctx.attempt(lambda: SCRIPTS[script].confined(str(tmp_path / "file"), "--x"))


@then(parsers.parse('it admits the path "{path}" in the scratch directory'))
def admits_working_directory(ctx, path):
    assert ctx.refused is None, ctx.refused.message
    assert ctx.result == (ctx.directory / path).resolve(), ctx.result


@then("it admits that file")
def admits_temporary(ctx, tmp_path):
    assert ctx.refused is None, ctx.refused.message
    assert ctx.result == (tmp_path / "file").resolve(), ctx.result


# --- tools/wiki-seed.py ------------------------------------------------------

@given("downloads are recorded instead of made", target_fixture="fetched")
def no_downloads(monkeypatch):
    fetched = []
    monkeypatch.setattr(urllib.request, "urlretrieve",
                        lambda url, target: fetched.append((url, Path(target))))
    return fetched


@then(parsers.parse('it downloaded the enwiki index to "{path}"'))
def downloaded(ctx, fetched, path):
    assert fetched == [(wiki_seed.urls("enwiki")[1], (ctx.directory / path).resolve())], fetched


@given(parsers.parse('a multistream index "{path}" listing:'))
def multistream_index(ctx, path, docstring):
    with bz2.open(ctx.directory / path, "wt", encoding="utf-8") as handle:
        handle.write("".join(line + "\n" for line in docstring.splitlines()))


@given("the dump's stream holds nothing", target_fixture="stream")
def empty_stream(monkeypatch):
    return _stream(monkeypatch)


@given(parsers.parse('the dump\'s stream holds a page "{title}", revision "{revision}", reading "{body}"'),
       target_fixture="stream")
def stream_page(request, monkeypatch, title, revision, body):
    try:
        stream = request.getfixturevalue("stream")
    except pytest.FixtureLookupError:  # the first page makes the stream
        stream = _stream(monkeypatch)
    stream["pages"][title] = (revision, body)
    return stream


def _stream(monkeypatch) -> dict:
    """The dump, which the scenario never downloads: each stream asked for
    holds the pages given, and each request is recorded."""
    stream = {"pages": {}, "requests": []}

    def articles(dump, start, end):
        stream["requests"].append((start, end))
        return stream["pages"]

    monkeypatch.setattr(wiki_seed, "articles_in_stream", articles)
    return stream


@then(parsers.parse("the dump was read once, from byte {start:d} to byte {end:d}"))
def read_once(stream, start, end):
    assert stream["requests"] == [(start, end)], stream["requests"]


# --- vectors: the H3 cells come from the H3 library, the same on every run ---

@when(parsers.parse('the vector generator draws a number below {n:d} from "{label}"'))
def draws(ctx, n, label):
    ctx.attempt(lambda: vectors.drawn(label, n))


@when(parsers.parse('the vector generator draws a number below {n:d} from each of "x {first:d}" to "x {last:d}"'))
def draws_each(ctx, n, first, last):
    """The distinct numbers drawn, in order."""
    ctx.attempt(lambda: sorted({vectors.drawn(f"x {i}", n) for i in range(first, last + 1)}))


@given("files the vector generator writes are recorded instead of written", target_fixture="written")
def no_writes(monkeypatch):
    written = {}
    monkeypatch.setattr(vectors, "write", lambda path, data: written.update({path: data}))
    return written


@when("the vector generator makes the H3 cell vectors")
def h3_cells(ctx):
    ctx.attempt(vectors.h3_cells)


@then(parsers.parse('what it wrote to "{path}" is what is committed there'))
def committed(ctx, written, path):
    assert ctx.refused is None, ctx.refused.message
    assert written[path] == json.loads((ROOT / path).read_text())
