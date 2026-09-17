"""Resolve the repo root and the sibling repo, with no silent defaults.

Two repos share this package. The public repo (`math-dept`) holds released
entries and the `MathDept` Lean library. The private sibling
(`math-dept-private`) holds extracts, the request inbox, triage records,
unreleased entries, and the `MathDeptPrivate` Lean library. Direction is
one way: the private repo requires the public one.

A repo root is the nearest ancestor directory containing a `ledger/` directory.
That marker is what makes a test fixture a repo too, which is how the invariant
suite gets exercised.
"""

from __future__ import annotations

import os
from pathlib import Path

from . import ConfigError

PUBLIC_REPO_DIRNAME = "math-dept"
PRIVATE_REPO_DIRNAME = "math-dept-private"
PRIVATE_ENV = "MATHDEPT_PRIVATE"
PUBLIC_ENV = "MATHDEPT_PUBLIC"
REQUIRE_LEAN_ENV = "MATHDEPT_REQUIRE_LEAN"


def find_repo_root(start: Path | str | None = None) -> Path:
    """Nearest ancestor of `start` (default: cwd) that contains `ledger/`."""
    origin = Path(start).resolve() if start is not None else Path.cwd().resolve()
    for candidate in (origin, *origin.parents):
        if (candidate / "ledger").is_dir():
            return candidate
    raise ConfigError(
        f"no math-dept repo root at or above {origin}: "
        "a repo root is a directory containing 'ledger/'"
    )


def package_root() -> Path:
    """The public repo this package was installed from (editable install)."""
    return Path(__file__).resolve().parent.parent


def repo_kind(root: Path) -> str:
    """'private' if this root carries the private-only surfaces, else 'public'."""
    root = Path(root)
    if (root / "inbox").is_dir() or (root / "MathDeptPrivate").is_dir():
        return "private"
    return "public"


def is_private(root: Path) -> bool:
    return repo_kind(root) == "private"


def lean_lib(root: Path) -> str:
    """The Lake library name this repo owns."""
    return "MathDeptPrivate" if is_private(root) else "MathDept"


def gen_root_script() -> Path:
    """The one copy of `scripts/gen_root.py`, in the public checkout beside this package.

    The private repo carries no copy and regenerates its root through this one, so a
    caller that needs it asks here and never looks under its own root.
    """
    script = package_root() / "scripts" / "gen_root.py"
    if not script.is_file():
        raise ConfigError(f"{script} is missing; the Lean root generator ships with the public checkout")
    return script


def _require_repo(path: Path, why: str) -> Path:
    """The path, once it is a math repo. A directory that is not one is an error.

    "Absent" and "present but not a repo" are different findings and get
    different treatment: a missing sibling means this machine has no copy, which
    every command tolerates, while a path that was pointed AT and holds no
    `ledger/` is a misconfiguration. Reporting the second as absent would send
    the reader looking for a checkout they already have, and reporting it later,
    when an entry scan finds no ledger directory, blames I1 for an environment
    variable.
    """
    if not (path / "ledger").is_dir():
        raise ConfigError(f"{why} is not a math repo (no ledger/)")
    return path


def private_root(root: Path | None = None) -> Path | None:
    """The private sibling, or None when this machine has no copy of it.

    Resolution order: the MATHDEPT_PRIVATE environment variable (which must
    point at a real math repo, otherwise the misconfiguration is an error, not
    a fallback), then `../math-dept-private` beside the given root.
    """
    override = os.environ.get(PRIVATE_ENV)
    if override:
        path = Path(override).expanduser().resolve()
        if not path.is_dir():
            raise ConfigError(f"{PRIVATE_ENV}={override} is not a directory")
        return _require_repo(path, f"{PRIVATE_ENV}={override}")
    if root is None:
        return None
    sibling = Path(root).resolve().parent / PRIVATE_REPO_DIRNAME
    if not sibling.is_dir():
        return None
    return _require_repo(sibling, str(sibling))


def public_root(root: Path | None = None) -> Path | None:
    """The public sibling seen from a private repo, or the root itself when public."""
    if root is not None and not is_private(Path(root)):
        return Path(root).resolve()
    override = os.environ.get(PUBLIC_ENV)
    if override:
        path = Path(override).expanduser().resolve()
        if not path.is_dir():
            raise ConfigError(f"{PUBLIC_ENV}={override} is not a directory")
        return _require_repo(path, f"{PUBLIC_ENV}={override}")
    if root is None:
        return None
    root = Path(root).resolve()
    declared = _declared_public_sibling(root)
    if declared is not None:
        return declared
    sibling = root.parent / PUBLIC_REPO_DIRNAME
    if not sibling.is_dir():
        return None
    return _require_repo(sibling, str(sibling))


def _declared_public_sibling(root: Path) -> Path | None:
    """The `public_sibling` line of repos.yaml, resolved against the repo root."""
    repos_yaml = root / "repos.yaml"
    if not repos_yaml.is_file():
        return None
    import yaml

    declared = (yaml.safe_load(repos_yaml.read_text(encoding="utf-8")) or {}).get("public_sibling")
    if not declared:
        return None
    path = Path(str(declared)).expanduser()
    path = path if path.is_absolute() else (root / path)
    if not path.is_dir():
        raise ConfigError(f"repos.yaml public_sibling points at {path}, which is not a directory")
    return _require_repo(path.resolve(), f"repos.yaml public_sibling {path}")


def require_lean() -> bool:
    """True when a missing Lean toolchain must fail rather than skip."""
    return os.environ.get(REQUIRE_LEAN_ENV, "") == "1"


def lean_roots(root: Path) -> list[Path]:
    """Every Lean library directory present in this repo, sorted."""
    root = Path(root)
    return sorted(p for p in root.glob("MathDept*") if p.is_dir())
