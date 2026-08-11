#!/usr/bin/env python3
"""Merge upstream/main into the fork behind a validation gate.

The fork keeps the upstream tree intact and adds an allowlisted delta. Sync is a
merge, never a rebase or a squash, so the fork network keeps working. The upstream
baseline recorded in UPSTREAM_BASE advances only after validation passes, so a
failed sync can be re-run without losing the last known-good baseline.

Exit codes:
    0  sync branch created and validated
    1  validation failed (baseline unchanged)
    2  preconditions not met
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

FORK_WORKFLOW_OVERRIDES = {
    "fork-config/workflows/quality.yml": ".github/workflows/fork-quality.yml",
    "fork-config/workflows/security.yml": ".github/workflows/fork-security.yml",
}

# Upstream workflows the fork deliberately does not run. Reintroduced by an
# upstream merge, they would fail on every run for lack of a Grafana Vault role.
REMOVED_UPSTREAM_WORKFLOWS = (
    ".github/workflows/skill-review.yml",
    ".github/workflows/agent-scan.yml",
)

# (command, path that must exist for the step to apply, additional success codes)
# pytest exits 5 when it collects nothing, which is not a validation failure.
VALIDATION_STEPS = (
    (["./scripts/lint-skills.sh", "skills"], "scripts/lint-skills.sh", ()),
    ([sys.executable, "-m", "pytest", "-q"], "tests", (5,)),
    ([sys.executable, "scripts/generate-catalog.py", "--check"],
     "scripts/generate-catalog.py", ()),
    ([sys.executable, "scripts/validate-catalog.py"], "scripts/validate-catalog.py", ()),
    ([sys.executable, "scripts/check-onprem-boundary.py",
      "--policy", "catalog/onprem-policy.yaml",
      "--marketplace", ".agents-plugin/marketplace.json",
      "--scan", "skills/onprem-observability"],
     "scripts/check-onprem-boundary.py", ()),
)


class SyncError(Exception):
    """Precondition failure — exit code 2."""


def git(repo: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True
    )
    if check and result.returncode != 0:
        raise SyncError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def require_clean_worktree(repo: Path) -> None:
    if git(repo, "status", "--porcelain"):
        raise SyncError("working tree is not clean; commit or stash first")


def branch_name(repo: Path, upstream_ref: str, now: datetime) -> str:
    short = git(repo, "rev-parse", "--short=12", upstream_ref)
    return f"sync/upstream-{now.strftime('%Y%m%d')}-{short}"


def restore_fork_overrides(repo: Path) -> list[str]:
    """Re-apply fork-owned workflow files after the merge."""
    restored: list[str] = []
    for source, destination in FORK_WORKFLOW_OVERRIDES.items():
        src, dst = repo / source, repo / destination
        if not src.is_file():
            raise SyncError(f"missing canonical workflow override: {source}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.is_file() or dst.read_bytes() != src.read_bytes():
            shutil.copyfile(src, dst)
            restored.append(destination)
    for removed in REMOVED_UPSTREAM_WORKFLOWS:
        path = repo / removed
        if path.is_file():
            path.unlink()
            restored.append(f"-{removed}")
    return restored


def run_validation(repo: Path) -> tuple[bool, str]:
    log: list[str] = []
    for step, required, extra_ok in VALIDATION_STEPS:
        label = " ".join(step)
        if not (repo / required).exists():
            log.append(f"SKIP {label} ({required} not present)")
            continue
        log.append(f"RUN  {label}")
        result = subprocess.run(step, cwd=repo, capture_output=True, text=True)
        log.append(result.stdout.strip())
        log.append(result.stderr.strip())
        if result.returncode != 0 and result.returncode not in extra_ok:
            log.append(f"FAIL {label} (exit {result.returncode})")
            return False, "\n".join(filter(None, log))
    log.append("validation passed")
    return True, "\n".join(filter(None, log))


def sync(
    repo: Path,
    upstream_ref: str,
    *,
    push: bool = False,
    now: datetime | None = None,
) -> tuple[int, str]:
    require_clean_worktree(repo)

    remote = upstream_ref.split("/", 1)[0]
    git(repo, "fetch", remote, upstream_ref.split("/", 1)[-1])

    now = now or datetime.now(timezone.utc)
    branch = branch_name(repo, upstream_ref, now)
    git(repo, "checkout", "-q", "-b", branch)

    merge = subprocess.run(
        ["git", "-C", str(repo), "merge", "--no-ff", "--no-edit", upstream_ref],
        capture_output=True,
        text=True,
    )
    if merge.returncode != 0:
        return 2, (
            f"branch {branch} created, merge conflict must be resolved by hand:\n"
            f"{merge.stdout}\n{merge.stderr}"
        )

    restored = restore_fork_overrides(repo)
    if restored:
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "ci(fork): restore fork workflow overrides")

    generator = repo / "scripts" / "generate-catalog.py"
    if generator.is_file():
        subprocess.run([sys.executable, str(generator)], cwd=repo, check=False)
        if git(repo, "status", "--porcelain"):
            git(repo, "add", "-A")
            git(repo, "commit", "-qm", "chore(catalog): regenerate after upstream sync")

    ok, log = run_validation(repo)
    if not ok:
        return 1, f"branch {branch} created; validation FAILED, UPSTREAM_BASE unchanged\n{log}"

    new_base = git(repo, "rev-parse", upstream_ref)
    (repo / "UPSTREAM_BASE").write_text(f"{new_base}\n", encoding="utf-8")
    git(repo, "add", "UPSTREAM_BASE")
    git(repo, "commit", "-qm", f"chore(sync): advance upstream baseline to {new_base[:12]}")

    if push:
        git(repo, "push", "-u", "origin", branch)

    return 0, f"branch {branch} validated; UPSTREAM_BASE advanced to {new_base}\n{log}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="repository path")
    parser.add_argument("--upstream-ref", default="upstream/main")
    parser.add_argument(
        "--push", action="store_true", help="push the sync branch to origin"
    )
    parser.add_argument("--log", help="write the validation log to this file")
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    try:
        code, message = sync(repo, args.upstream_ref, push=args.push)
    except SyncError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(message)
    if args.log:
        Path(args.log).write_text(message + "\n", encoding="utf-8")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
