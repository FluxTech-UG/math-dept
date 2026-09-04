"""Guard: the Lake package builds.

Skips loudly when `lake` is absent, which is the normal state on a machine that
has not installed the toolchain. `MATHDEPT_REQUIRE_LEAN=1` turns that skip into
a failure; CI and `python -m mdept.release` both set it, so a green run there
means Lean really compiled.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BUILD_TIMEOUT_SECONDS = 3600


def require_lean(reason: str) -> None:
    """Skip, or fail when the environment says Lean must be present."""
    if os.environ.get("MATHDEPT_REQUIRE_LEAN") == "1":
        pytest.fail(f"MATHDEPT_REQUIRE_LEAN=1 but {reason}")
    pytest.skip(f"{reason}; set MATHDEPT_REQUIRE_LEAN=1 to make this a failure")


@pytest.fixture(scope="session")
def lake_build():
    if shutil.which("lake") is None:
        require_lean("`lake` is not on PATH")
    result = subprocess.run(
        ["lake", "build"], cwd=REPO_ROOT, capture_output=True, text=True, timeout=BUILD_TIMEOUT_SECONDS
    )
    return result


def test_lake_build_succeeds(lake_build):
    assert lake_build.returncode == 0, (
        "`lake build` failed.\n" + lake_build.stdout[-4000:] + lake_build.stderr[-4000:]
    )


def test_mathlib_cache_was_applied(lake_build):
    assert "Building Mathlib." not in lake_build.stdout, (
        "the build started compiling Mathlib from source, so the cache did not apply. "
        "Stop and run `lake exe cache get`."
    )
