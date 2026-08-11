#!/usr/bin/env python3
"""Reject modifications to upstream-owned paths in this fork.

Everything under `skills/grafana-*` belongs to `grafana/skills`. Editing it in the
fork turns every upstream sync into a manual merge and makes the fork delta
impossible to audit. Generic fixes go upstream as a PR instead.

Exit codes:
    0  only allowed delta
    1  an upstream-owned path was modified
    2  invalid configuration or baseline
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
from pathlib import Path

SHA_RE = re.compile(r"^[0-9a-f]{7,64}$")

# Paths the fork may add or change. Anything outside this list that is also
# upstream-owned is a boundary violation.
ALLOWED_PATTERNS = (
    "skills/onprem-observability/**",
    "skills/onprem-observability-adapters/**",
    "catalog/**",
    "fork-config/**",
    "scripts/**",
    "tests/**",
    "docs/**",
    ".agents-plugin/marketplace.json",
    ".claude-plugin/marketplace.json",
    ".cursor-plugin/marketplace.json",
    "skill-registry.json",
    ".github/workflows/fork-quality.yml",
    ".github/workflows/fork-security.yml",
    ".github/workflows/upstream-sync.yml",
    ".github/workflows/skill-review.yml",
    ".github/workflows/agent-scan.yml",
    ".github/CODEOWNERS",
    ".gitignore",
    "UPSTREAM_BASE",
    "CHANGELOG-ONPREM.md",
)

UPSTREAM_OWNED_PREFIX = "skills/grafana-"


class BoundaryError(Exception):
    """Configuration or baseline problem — exit code 2."""


def _validate_patterns() -> None:
    """An allowlist entry must never escape the repository."""
    for pattern in ALLOWED_PATTERNS:
        if pattern.startswith("/") or ".." in Path(pattern).parts:
            raise BoundaryError(f"unsafe allowlist entry: {pattern}")


def is_allowed(path: str) -> bool:
    if path.startswith("/") or ".." in Path(path).parts:
        return False
    for pattern in ALLOWED_PATTERNS:
        if fnmatch.fnmatch(path, pattern):
            return True
        # fnmatch treats "**" as a single segment wildcard, so match prefixes too.
        if pattern.endswith("/**") and path.startswith(pattern[:-2]):
            return True
    return False


def changed_paths(repo: Path, base: str, head: str) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "diff", "--name-only", f"{base}..{head}"],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise BoundaryError(
            f"git diff {base}..{head} failed: {exc.stderr.strip()}"
        ) from exc
    return [line for line in result.stdout.splitlines() if line]


def check(repo: Path, base: str, head: str) -> list[str]:
    _validate_patterns()
    if not SHA_RE.match(base) and not base.startswith(("upstream/", "origin/")):
        raise BoundaryError(f"invalid base revision: {base!r}")
    violations = []
    for path in changed_paths(repo, base, head):
        if path.startswith(UPSTREAM_OWNED_PREFIX) and not is_allowed(path):
            violations.append(path)
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="repository path")
    parser.add_argument("--base", required=True, help="upstream baseline revision")
    parser.add_argument("--head", default="HEAD", help="revision to check")
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    if not (repo / ".git").exists():
        print(f"error: not a git repository: {repo}", file=sys.stderr)
        return 2

    try:
        violations = check(repo, args.base.strip(), args.head)
    except BoundaryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if violations:
        print("Upstream-owned paths modified in this fork:")
        for path in violations:
            print(f"  {path}")
        print(
            "\nSend the change to grafana/skills as a PR, or add an explicit "
            "allowlist entry with a test and a stated reason."
        )
        return 1

    print("check-upstream-boundary: only allowed delta")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
