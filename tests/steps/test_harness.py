"""Step definitions for the harness self-check."""

from __future__ import annotations

import os
from pathlib import Path

from pytest_bdd import scenarios, then

scenarios("../features/harness.feature")


@then("the program it ran is the one in the directory PUBLET_BIN_DIR names")
def ran_from_bin_dir(result) -> None:
    ran = Path(result.argv[0])
    assert ran.parent.resolve() == Path(os.environ["PUBLET_BIN_DIR"]).resolve(), ran
