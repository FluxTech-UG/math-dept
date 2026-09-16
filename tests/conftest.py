"""Test-wide isolation: the suite never sees the machine's real math repos.

`MATHDEPT_PRIVATE` and `MATHDEPT_PUBLIC` are how an operator points the package
at a checkout somewhere other than the sibling directory, and they take priority
over every other resolution rule. Left set, they reach into the fixture repos:
`new.allocate_id` allocates across both ledgers, so with the real private repo
in the environment a fixture that should hand out MD_0005 hands out the next ID
after the real ledger's highest, and the test fails for a reason that has
nothing to do with the code under test. Clearing them once, for the session, is
what makes a fixture pair the whole family.
"""

import pytest


@pytest.fixture(autouse=True, scope="session")
def _no_machine_repos():
    import os

    saved = {name: os.environ.pop(name, None)
             for name in ("MATHDEPT_PRIVATE", "MATHDEPT_PUBLIC")}
    yield
    for name, value in saved.items():
        if value is not None:
            os.environ[name] = value
