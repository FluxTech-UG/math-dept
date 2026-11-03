"""File the comment issues of the private tracker into the private inbox, one file each.

Run from the private repo:

    python -m mdept.comments
    python -m mdept.comments --repo FluxTech-UG/math-dept-private --into inbox/comments
    python -m mdept.comments --from-json issues.json

Every entry page of the reading site carries a link that opens a new issue in the
private repo, titled `MD_####: <title>` and labelled `comment` (`site.toml` holds the
repo and the label). This command lists those issues with
`gh issue list --label comment --state all --json number,title,body,author,createdAt,url`
and writes each one it has not filed before as `inbox/comments/<YYYY-MM-DD>-MD_####-<n>.md`
(the creation date, the entry the title names, the issue number): front matter for the
issue, then its body verbatim. `inbox/comments/.seen` lists the filed issue numbers, one
per line, and only ever grows; a filed comment is never rewritten.

An issue whose title names no `MD_####`, or names an ID that is in neither ledger, is
refused: it is reported, left unfiled and unseen, and the run exits non-zero, so the
title can be fixed on GitHub and the next run files it. A listing that comes back as
long as `--limit` is refused whole, because the oldest unfiled comment may be past it.

A comment is someone's words, recorded as written: `mdept.check` reads this folder as
quoted text (`QUOTED_SURFACES` there), outside the em-dash rule and the I12 resolution
of the IDs it mentions. `--from-json` reads a saved listing instead of calling `gh`,
which is how the tests run and how a listing fetched elsewhere is filed.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml

from . import CheckError, ConfigError, MDeptError
from . import config, schema, site
from . import family as family_mod

COMMENTS_DIR = "inbox/comments"
SEEN_FILE = ".seen"
GH_FIELDS = ("number", "title", "body", "author", "createdAt", "url")
LIMIT = 200


def list_issues(repo: str, label: str, limit: int) -> list[dict]:
    """The labelled issues, open and closed, as `gh` reports them."""
    command = ["gh", "issue", "list", "--repo", repo, "--label", label, "--state", "all",
               "--json", ",".join(GH_FIELDS), "--limit", str(limit)]
    try:
        run = subprocess.run(command, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise ConfigError("gh is not on PATH; install the GitHub CLI or pass --from-json") from exc
    if run.returncode != 0:
        raise ConfigError(f"{' '.join(command)} failed (exit {run.returncode}): {run.stderr.strip()}")
    return json.loads(run.stdout)


def read_seen(into: Path) -> set[int]:
    seen_path = into / SEEN_FILE
    if not seen_path.is_file():
        filed = sorted(p.name for p in into.glob("*.md")) if into.is_dir() else []
        if filed:
            raise CheckError(f"comments: {seen_path}: field '<seen>': missing while {len(filed)} comment "
                             f"files are filed (first {filed[0]}); restore it from git before filing more")
        return set()
    numbers = set()
    for line in seen_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            if not line.strip().isdigit():
                raise CheckError(f"comments: {seen_path}: field '<seen>': {line!r} is not an issue number")
            numbers.add(int(line))
    return numbers


def _issue_fields(issue: dict) -> tuple[int, str, str, str, str, str]:
    missing = [k for k in GH_FIELDS if k not in issue]
    if missing:
        raise ConfigError(f"an issue in the listing lacks {missing}: {json.dumps(issue)[:200]}")
    created = str(issue["createdAt"])
    if not schema.ISO_DATE_RE.match(created[:10]):
        raise ConfigError(f"issue #{issue['number']}: createdAt {created!r} does not start with YYYY-MM-DD")
    author = issue["author"]["login"] if isinstance(issue["author"], dict) else str(issue["author"])
    return int(issue["number"]), str(issue["title"]), str(issue["body"] or ""), author, created, str(issue["url"])


def file_comments(issues: list[dict], into: Path, resolve) -> tuple[list[Path], list[str]]:
    """Write every unseen issue; return (files written, refusals). `resolve(ID)` finds an entry."""
    into = Path(into)
    seen = read_seen(into)
    written: list[Path] = []
    refused: list[str] = []
    for issue in sorted(issues, key=lambda i: int(i["number"])):
        number, title, body, author, created, url = _issue_fields(issue)
        if number in seen:
            continue
        match = schema.ID_TOKEN_RE.search(title)
        if match is None:
            refused.append(f"#{number} {title!r} names no MD_#### in its title; retitle it 'MD_####: ...'")
            continue
        entry_id = match.group(0)
        if resolve(entry_id) is None:
            refused.append(f"#{number} {title!r} names {entry_id}, which is in neither ledger")
            continue
        path = into / f"{created[:10]}-{entry_id}-{number}.md"
        if path.exists():
            raise CheckError(f"comments: {path}: field '<file>': exists although issue #{number} is not in "
                             f"{SEEN_FILE}; filed comments are never rewritten")
        front = {"issue": number, "entry": entry_id, "title": title, "author": author,
                 "created": created, "url": url}
        into.mkdir(parents=True, exist_ok=True)
        path.write_text("---\n" + yaml.safe_dump(front, sort_keys=False, allow_unicode=True) + "---\n\n"
                        + body.rstrip("\n") + "\n", encoding="utf-8")
        with (into / SEEN_FILE).open("a", encoding="utf-8") as seen_file:
            seen_file.write(f"{number}\n")
        written.append(path)
    return written, refused


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m mdept.comments", description=__doc__.splitlines()[0])
    parser.add_argument("--repo", default=None,
                        help="the tracker as owner/name (default: the private repo named in site.toml)")
    parser.add_argument("--into", default=None,
                        help=f"the folder to file into (default: {COMMENTS_DIR} of the repo around the cwd)")
    parser.add_argument("--from-json", default=None, help="read this saved `gh issue list --json` output")
    parser.add_argument("--limit", type=int, default=LIMIT, help=f"issues to list (default {LIMIT})")
    parser.add_argument("--config", default=None, help="the site settings file (default: site.toml)")
    args = parser.parse_args(argv)
    try:
        cfg = site.load_config(args.config)
        root = config.find_repo_root(Path(args.into) if args.into else None)
        if not config.is_private(root):
            raise ConfigError(f"{root} is the public repo; comments are filed into the private inbox")
        into = Path(args.into) if args.into else root / COMMENTS_DIR
        if args.from_json:
            issues = json.loads(Path(args.from_json).read_text(encoding="utf-8"))
        else:
            issues = list_issues(args.repo or cfg.issue_repo, cfg.comment_label, args.limit)
        if len(issues) >= args.limit:
            raise ConfigError(f"the listing returned {len(issues)} issues, the --limit; the oldest unfiled "
                              "comment may lie past it, so rerun with a larger --limit")
        family = family_mod.load_family(root)
        by_id = family.by_id()
        written, refused = file_comments(issues, into, by_id.get)
    except (MDeptError, json.JSONDecodeError) as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    for path in written:
        print(f"filed {path}")
    for line in refused:
        print(f"REFUSED {line}", file=sys.stderr)
    print(f"{len(written)} filed, {len(refused)} refused, of {len(issues)} listed")
    return 1 if refused else 0


if __name__ == "__main__":
    from mdept.comments import main as _main

    raise SystemExit(_main())
