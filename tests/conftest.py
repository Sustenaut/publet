"""Fixtures for the functional suite.

Every test here runs the shipped binaries as a subprocess. Nothing in this
tree imports, links, or otherwise reaches into the Rust implementation --
that is the boundary described in section 6.2 of the implementation plan,
and it is what lets the same scenarios run against any implementation.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest
from pubtest.core import Completed, Result, bin_var, program
from pubtest.plugin import run_program

# The suite imports its own helpers from `support/`; it never imports the
# implementation. Adding the suite root to the path keeps that explicit.
sys.path.insert(0, str(Path(__file__).parent))

BIN_VAR = "PUBLET_BIN_DIR"


# pub dates the keys and signatures it makes now, unless $PUB_CREATED pins
# them: the suite pins it, so the objects it makes, and their identifiers,
# are the same on every run. A scenario about the default unsets it.
os.environ.setdefault("PUB_CREATED", "2026-09-16T00:00:00Z")


def pytest_configure(config):
    """Serve every built binary to pubtest's `Given the program under test
    is "NAME"`, which reads NAME's own `<NAME>_BIN_DIR`, from the one
    variable a second implementation sets. A variable already set wins."""
    raw = os.environ.get(BIN_VAR)
    if raw and Path(raw).is_dir():
        for path in Path(raw).iterdir():
            if path.name.startswith("pub") and path.is_file() and os.access(path, os.X_OK):
                os.environ.setdefault(bin_var(path.stem), raw)


@pytest.fixture(scope="session")
def bin_dir() -> Path:
    """Directory holding the binaries under test.

    Resolved only from PUBLET_BIN_DIR so that a second implementation, in
    any language, runs this suite by setting one environment variable.
    """
    raw = os.environ.get(BIN_VAR)
    if not raw:
        pytest.fail(
            "PUBLET_BIN_DIR is not set. Run the suite through `make functional`, "
            "or set it to the directory holding the publet binaries."
        )
    path = Path(raw)
    if not path.is_dir():
        pytest.fail(f"PUBLET_BIN_DIR does not exist: {path}")
    return path


@pytest.fixture(autouse=True)
def scratch(pubtest_ctx, tmp_path: Path) -> Path:
    """The scenario's scratch directory is its tmp_path, for the suite's own
    steps and pubtest's alike: pubtest's `I run` runs there, its file steps
    read and write there, and `nothing was written` watches it."""
    pubtest_ctx.directory = tmp_path
    return tmp_path


class Ran(Completed):
    """pubtest's record of a run, read by the suite's older steps as a
    `subprocess.CompletedProcess` too."""

    @property
    def returncode(self) -> int:
        return self.code


@dataclass
class Runner:
    """Runs binaries from the directory under test, in the scratch directory."""

    bin_dir: Path
    cwd: Path
    ctx: object = None

    def path_to(self, name: str) -> Path:
        # A binary this build does not ship is a layer it omits, such as
        # settlement (Section 12.1): what needs it does not apply.
        if not (self.bin_dir / name).exists():
            pytest.skip(f"{name} is not built yet")
        return program(name, BIN_VAR)

    def run(self, name: str, *args: str, stdin: bytes | None = None,
            env: dict[str, str] | None = None, cwd: Path | None = None) -> Ran:
        """Run a binary under test, in the scratch directory unless `cwd`
        names another; `env` is merged over the environment."""
        done = run_program([str(self.path_to(name)), *map(str, args)], stdin, cwd or self.cwd, env, 120)
        return Ran(done.argv, done.code, done.out, done.err)

    def act(self, name: str, *args: str, stdin: bytes | None = None,
            env: dict[str, str] | None = None, cwd: Path | None = None) -> Result:
        """Run a binary as the scenario's action: what it did is pubtest's
        result, which pubtest's Thens read."""
        self.ctx.acting()
        done = self.run(name, *args, stdin=stdin, env=env, cwd=cwd)
        return self.ctx.ran(Result(code=done.code, stdout=done.stdout, stderr=done.stderr, argv=done.argv))

    def pipeline(self, stages: list[str], stdin: bytes | None = None) -> Completed:
        """Run shell stages joined by pipes.

        Composition over CID lines is a contract of the design, so it is
        tested as behaviour rather than assumed.
        """
        script = " | ".join(stages)
        env = {"PATH": f"{self.bin_dir}:{os.environ['PATH']}"}
        return run_program(["bash", "-o", "pipefail", "-c", script], stdin, self.cwd, env, 120)


@pytest.fixture
def runner(bin_dir: Path, scratch: Path, pubtest_ctx) -> Runner:
    """A runner rooted in the scenario's scratch directory."""
    return Runner(bin_dir=bin_dir, cwd=scratch, ctx=pubtest_ctx)


# --- steps shared across feature files -------------------------------------
#
# pytest-bdd resolves step definitions per module, so anything used by more
# than one feature lives here rather than being duplicated or imported.

from pytest_bdd import parsers, then  # noqa: E402


# --- fixtures and steps shared across feature files -------------------------

from pytest_bdd import given, when  # noqa: E402

from support.objects import (  # noqa: E402
    author_key, cid_of, publet, relation, write_store,
)

_KA = author_key("K_a")
_KB = author_key("K_b")

# Only these commands read a store directory; the rest are stdin filters.
DIR_AWARE = {
    "pub-ls", "pub-edges", "pub-lineage", "pub-closure",
    "pub-divergence", "pub-lint", "pub-delta",
}


@given("a store containing the Appendix A fixture", target_fixture="store")
def appendix_a(tmp_path):
    """P1 superseded by P4 by its own author; P2 a third-party proposal."""
    p1 = publet(_KA, "2026-09-12T10:00:00Z", "empirical", "relapse incidence fell")
    p4 = publet(_KA, "2026-09-12T11:00:00Z", "empirical", "effect holds in a subgroup")
    p2 = publet(_KB, "2026-09-12T10:30:00Z", "empirical", "the design cannot support it")
    objects = [
        p1, p4, p2,
        relation(_KA, "2026-09-12T11:00:01Z", "supersedes", cid_of(p4), cid_of(p1)),
        relation(_KB, "2026-09-12T10:30:01Z", "supersedes", cid_of(p2), cid_of(p1)),
        relation(_KB, "2026-09-12T10:30:02Z", "disputes", cid_of(p2), cid_of(p1)),
    ]
    write_store(tmp_path, objects)
    return {"dir": tmp_path, "P1": cid_of(p1), "P4": cid_of(p4), "P2": cid_of(p2)}




@when(parsers.parse('I run the pipeline "{pipeline}"'), target_fixture="result")
def run_pipeline(runner, store, pipeline: str):
    stages = []
    for stage in pipeline.split("|"):
        stage = stage.strip()
        if stage.split()[0] in DIR_AWARE:
            stage += f" --dir={store['dir']}"
        stages.append(stage)
    return runner.pipeline(stages)


@when("I load the store", target_fixture="result")
def load_store(runner, store):
    return runner.act("pub-ls", f"--dir={store['dir']}")


@then("the load leaves out one object and reports it")
def load_drops_one(result, store):
    # Section 5.2: one inadmissible object does not stop the rest loading.
    assert result.code == 0, result.stderr
    held = len(list(store["dir"].glob("*.cbor")))
    assert len(result.stdout.split()) == held - 1, result.stdout
    assert "warning: dropped" in result.stderr, result.stderr


def _code(result) -> int:
    """Exit status from either result shape.

    Scenarios that run a plumbing command get a `Completed`; those that run
    `pub` in a working directory get a `subprocess.CompletedProcess`. One
    step phrase should serve both rather than forcing the feature files to
    know which.
    """
    return getattr(result, "returncode", None) or getattr(result, "code", 0)


@then("both runs produce identical output")
def runs_identical(two_results) -> None:
    first, second = two_results
    assert _code(first) == _code(second) == 0
    assert first.stdout == second.stdout
