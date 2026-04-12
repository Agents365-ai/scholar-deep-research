#!/usr/bin/env python3
"""check_update.py — check for and apply skill updates.

Runs as Phase 0 Step 0 before the research workflow starts. Fast-forwards
the skill's git checkout against its upstream remote when an update is
available, and surfaces what happened through the standard JSON envelope
so SKILL.md can tell the user in one line.

Design constraints (see CLAUDE.md, "The CLI contract"):
  - Never fails the workflow. Any error (offline, no remote, dirty tree,
    non-git install) becomes a structured envelope with exit 0.
  - Respects SCHOLAR_SKIP_UPDATE_CHECK=1 as an opt-out escape hatch for
    users who want to pin a version.
  - Honors --ff-only semantics: local modifications are never clobbered.
    When the working tree is dirty the update is skipped and the user is
    informed, so they know auto-update did not run.
  - Does not pip-install. Detects requirements.txt drift and surfaces a
    hint; the host environment (which venv, which python) is the user's
    to manage, not this script's.
  - The only script in this repo allowed to touch the skill's own files.

Action values:
  up_to_date        local HEAD == upstream HEAD
  updated           fast-forward pull succeeded
  update_available  --dry-run only; pull would succeed
  skipped_dirty     working tree has uncommitted changes
  skipped_disabled  SCHOLAR_SKIP_UPDATE_CHECK is set
  not_a_git_repo    installed without .git (tarball, package manager)
  check_failed      git/network error; `reason` field explains
"""
from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

from _common import maybe_emit_schema, ok

SKILL_ROOT = Path(__file__).resolve().parent.parent


def run_git(*args: str) -> tuple[int, str, str]:
    """Run a git command in the skill root. Returns (rc, stdout, stderr)."""
    try:
        p = subprocess.run(
            ["git", *args],
            cwd=str(SKILL_ROOT),
            capture_output=True,
            text=True,
            timeout=20,
        )
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return 128, "", str(e)


def is_git_repo() -> bool:
    return (SKILL_ROOT / ".git").exists()


def local_head() -> str | None:
    rc, out, _ = run_git("rev-parse", "HEAD")
    return out if rc == 0 and out else None


def upstream_head() -> str | None:
    """HEAD of the upstream tracking branch after fetch."""
    rc, out, _ = run_git("rev-parse", "@{u}")
    return out if rc == 0 and out else None


def fetch() -> tuple[bool, str]:
    rc, _, stderr = run_git("fetch", "--quiet", "origin")
    return rc == 0, stderr


def dirty_files() -> list[str]:
    rc, out, _ = run_git("status", "--porcelain")
    if rc != 0:
        return []
    return [line[3:] for line in out.splitlines() if line]


def commits_behind(local: str, upstream: str) -> int | None:
    rc, out, _ = run_git("rev-list", "--count", f"{local}..{upstream}")
    return int(out) if rc == 0 and out.isdigit() else None


def requirements_changed(old: str, new: str) -> bool:
    rc, out, _ = run_git("diff", "--name-only", old, new,
                         "--", "requirements.txt")
    return rc == 0 and bool(out.strip())


def fast_forward() -> tuple[bool, str]:
    rc, _, stderr = run_git("pull", "--ff-only", "--quiet")
    return rc == 0, stderr


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Check for and apply updates to the scholar-deep-research "
            "skill. Always exits 0; the action field describes what "
            "happened."
        )
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Check for updates but do not pull")
    maybe_emit_schema(parser, "check_update")
    args = parser.parse_args()

    # Opt-out escape hatch — the user pinned a version on purpose.
    if os.environ.get("SCHOLAR_SKIP_UPDATE_CHECK"):
        ok({"action": "skipped_disabled",
            "reason": "SCHOLAR_SKIP_UPDATE_CHECK is set"})
        return

    # Non-git install (ClawHub tarball, SkillsMP package, vendored copy).
    # The package manager owns updates for this install — we should not.
    if not is_git_repo():
        ok({"action": "not_a_git_repo",
            "reason": ("No .git directory — skill is managed by a package "
                       "manager. Use its own update command."),
            "skill_root": str(SKILL_ROOT)})
        return

    local = local_head()
    if not local:
        ok({"action": "check_failed",
            "reason": "Could not read local HEAD"})
        return

    # One network call: fetch objects so we can diff locally afterwards.
    fetched, fetch_err = fetch()
    if not fetched:
        ok({"action": "check_failed",
            "reason": (f"git fetch failed: "
                       f"{fetch_err.splitlines()[0] if fetch_err else 'unknown error'}"),
            "local_head": local[:12]})
        return

    upstream = upstream_head()
    if not upstream:
        ok({"action": "check_failed",
            "reason": ("No upstream tracking branch configured "
                       "(e.g. 'git branch --set-upstream-to=origin/main')"),
            "local_head": local[:12]})
        return

    if local == upstream:
        ok({"action": "up_to_date", "head": local[:12]})
        return

    behind = commits_behind(local, upstream)
    reqs_changed = requirements_changed(local, upstream)

    # Protect local modifications. --ff-only would already refuse, but we
    # catch it earlier so the user gets a structured reason instead of a
    # raw git error.
    dirty = dirty_files()
    if dirty:
        ok({"action": "skipped_dirty",
            "reason": ("Local modifications present — auto-update will "
                       "not clobber your work"),
            "dirty_files": dirty[:5],
            "dirty_count": len(dirty),
            "local_head": local[:12],
            "remote_head": upstream[:12],
            "commits_behind": behind,
            "requirements_changed": reqs_changed,
            "hint": f"Review: cd {SKILL_ROOT} && git status"})
        return

    if args.dry_run:
        ok({"action": "update_available",
            "dry_run": True,
            "from": local[:12],
            "to": upstream[:12],
            "commits_behind": behind,
            "requirements_changed": reqs_changed})
        return

    success, stderr = fast_forward()
    if not success:
        ok({"action": "check_failed",
            "reason": (f"git pull --ff-only failed: "
                       f"{stderr.splitlines()[0] if stderr else 'unknown'}"),
            "local_head": local[:12],
            "remote_head": upstream[:12]})
        return

    data: dict = {
        "action": "updated",
        "from": local[:12],
        "to": upstream[:12],
        "commits_behind": behind,
        "requirements_changed": reqs_changed,
    }
    if reqs_changed:
        data["hint"] = ("Python dependencies changed — run "
                        "`pip install -r requirements.txt` before the "
                        "next invocation")
    ok(data)


if __name__ == "__main__":
    main()
