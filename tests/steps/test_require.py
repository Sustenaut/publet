"""Steps for a project's pub version requirement (pub require)."""

from __future__ import annotations

from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/porcelain/require.feature")


@given("an empty directory")
def empty_directory(runner):
    assert not any(runner.cwd.iterdir())


@given(parsers.parse('the directory needs pub "{requirement}"'))
def needs(runner, requirement: str):
    (runner.cwd / "pub-version.txt").write_text(f"# the pub these scripts need\n{requirement}\n")


@given(parsers.parse('a workspace that needs pub "{requirement}"'))
def workspace_needs(runner, requirement: str):
    assert runner.run("pub", "init").code == 0
    config = runner.cwd / ".publet" / "config"
    config.write_text(config.read_text() + f"pub={requirement}\n")


@when(parsers.parse('I run pub with "{args}"'), target_fixture="result")
def run_pub(runner, args: str):
    return runner.run("pub", *args.split())


@when(parsers.parse('I run pub with "{args}" and PUB_IGNORE_VERSION=1'), target_fixture="result")
def run_pub_ignoring(runner, args: str):
    return runner.run("pub", *args.split(), env={"PUB_IGNORE_VERSION": "1"})


@when(parsers.parse('I run pub with "{args}" from a directory inside it'), target_fixture="result")
def run_pub_inside(runner, args: str):
    inner = runner.cwd / "notes" / "drafts"
    inner.mkdir(parents=True)
    runner.cwd = inner
    return runner.run("pub", *args.split())


@then("it exits 2")
def exits_2(result):
    assert result.code == 2, (result.code, result.stderr)


@then("no workspace was created")
def no_workspace(runner):
    assert not (runner.cwd / ".publet").exists()


@then("stderr is empty")
def stderr_empty(result):
    assert result.stderr == "", result.stderr
