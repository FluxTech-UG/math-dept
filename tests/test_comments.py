"""`python -m mdept.comments`: tracker issues filed into the private inbox, once each.

The listing is a saved `gh issue list --json` payload (`--from-json`), so the suite never
calls GitHub. The cases are about the filing contract: one file per unseen issue, the
seen list that makes a rerun file nothing, the refusals that leave an issue for the next
run, and the check reading the filed text as a quote.
"""

import json
import shutil
from pathlib import Path

import pytest

from mdept import CheckError, check, comments

FIXTURES = Path(__file__).resolve().parent / "fixtures"
BASES = ("good_public", "good_private")


@pytest.fixture
def private(tmp_path):
    for base in BASES:
        shutil.copytree(FIXTURES / base, tmp_path / base, ignore=shutil.ignore_patterns("__pycache__"))
    return tmp_path / "good_private"


def issue(number, title, body="A note.", created="2026-11-03T09:15:00Z"):
    return {"number": number, "title": title, "body": body, "author": {"login": "john"},
            "createdAt": created, "url": f"https://github.com/o/r/issues/{number}"}


def listing(tmp_path, issues) -> str:
    path = tmp_path / "issues.json"
    path.write_text(json.dumps(issues), encoding="utf-8")
    return str(path)


def run(private, payload, *args) -> int:
    return comments.main(["--into", str(private / comments.COMMENTS_DIR), "--from-json", payload, *args])


def test_each_unseen_issue_is_filed_once(private, tmp_path, capsys):
    payload = listing(tmp_path, [issue(12, "MD_0005: the bound looks loose"),
                                 issue(14, "Comment on MD_0001", created="2026-11-04T10:00:00Z")])
    assert run(private, payload) == 0
    folder = private / comments.COMMENTS_DIR
    assert sorted(p.name for p in folder.glob("*.md")) == ["2026-11-03-MD_0005-12.md", "2026-11-04-MD_0001-14.md"]
    text = (folder / "2026-11-03-MD_0005-12.md").read_text(encoding="utf-8")
    assert "issue: 12" in text and "entry: MD_0005" in text and text.rstrip().endswith("A note.")
    assert (folder / comments.SEEN_FILE).read_text(encoding="utf-8").split() == ["12", "14"]
    assert run(private, payload) == 0
    assert "0 filed" in capsys.readouterr().out
    assert len(list(folder.glob("*.md"))) == 2


def test_a_title_without_an_id_is_refused_and_left_unseen(private, tmp_path, capsys):
    payload = listing(tmp_path, [issue(3, "a general remark"), issue(4, "MD_0006: typo")])
    assert run(private, payload) == 1
    err = capsys.readouterr().err
    assert "#3" in err and "names no MD_####" in err
    folder = private / comments.COMMENTS_DIR
    assert [p.name for p in folder.glob("*.md")] == ["2026-11-03-MD_0006-4.md"]
    assert (folder / comments.SEEN_FILE).read_text(encoding="utf-8").split() == ["4"]


def test_an_id_in_neither_ledger_is_refused(private, tmp_path, capsys):
    assert run(private, listing(tmp_path, [issue(5, "MD_0999: where is this?")])) == 1
    assert "in neither ledger" in capsys.readouterr().err
    assert not list((private / comments.COMMENTS_DIR).glob("*.md"))


def test_a_listing_as_long_as_the_limit_is_refused_whole(private, tmp_path, capsys):
    payload = listing(tmp_path, [issue(n, f"MD_0005: note {n}") for n in (1, 2)])
    assert run(private, payload, "--limit", "2") == 1
    assert "--limit" in capsys.readouterr().err
    assert not (private / comments.COMMENTS_DIR).exists()


def test_a_missing_seen_list_beside_filed_comments_fails(private):
    folder = private / comments.COMMENTS_DIR
    folder.mkdir(parents=True)
    (folder / "2026-11-03-MD_0005-1.md").write_text("---\nissue: 1\n---\n", encoding="utf-8")
    with pytest.raises(CheckError, match="missing while 1 comment files are filed"):
        comments.read_seen(folder)


def test_the_public_repo_takes_no_comments(private, tmp_path, capsys):
    public = private.parent / "good_public"
    code = comments.main(["--into", str(public / comments.COMMENTS_DIR),
                          "--from-json", listing(tmp_path, [issue(1, "MD_0001: x")])])
    assert code == 1
    assert "public repo" in capsys.readouterr().err


def test_gh_is_asked_for_every_labelled_issue(monkeypatch):
    seen = {}

    class Done:
        returncode = 0
        stdout = "[]"
        stderr = ""

    def fake_run(command, **kwargs):
        seen["command"] = command
        return Done()

    monkeypatch.setattr(comments.subprocess, "run", fake_run)
    assert comments.list_issues("FluxTech-UG/math-dept-private", "comment", 200) == []
    assert seen["command"] == ["gh", "issue", "list", "--repo", "FluxTech-UG/math-dept-private",
                               "--label", "comment", "--state", "all",
                               "--json", "number,title,body,author,createdAt,url", "--limit", "200"]


def test_check_reads_a_filed_comment_as_a_quote(private, tmp_path):
    """Someone's words are recorded as written: an em dash or an unknown ID in a comment
    fails neither I17 nor I12."""
    body = f"This contradicts MD_0999 {chr(0x2014)} or does it?"  # an em dash, written as its code
    assert run(private, listing(tmp_path, [issue(7, "MD_0005: remark", body=body)])) == 0
    check.run(private)
