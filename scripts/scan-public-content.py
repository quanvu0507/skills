#!/usr/bin/env python3
"""Reject private or internal material before it is published in the public fork.

The public fork must stay publishable: no private repository names, no internal
hostnames or endpoints, no credentials and no current incident detail. Project
identity belongs in the private overlay.

Exit codes:
    0  clean
    1  forbidden content found
    2  invalid configuration / unreadable target
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Paths that are scanned. Upstream-owned skill text is excluded because it is
# immutable here; the on-prem policy checker handles its Cloud content instead.
DEFAULT_TARGETS = (
    "skills/onprem-observability",
    "skills/onprem-observability-adapters",
    "catalog",
    "docs",
    "scripts",
    "fork-config",
    "tests",
)

SKIP_DIR_NAMES = {".git", "__pycache__", ".pytest_cache", ".venv", "node_modules"}

# Files that legitimately contain the patterns because they define or test them.
SELF_REFERENTIAL = {
    "scripts/scan-public-content.py",
    "scripts/check-onprem-boundary.py",
    "tests/test_public_content.py",
    "tests/test_onprem_boundary.py",
    "tests/test_public_workflows.py",
    "fork-config/workflows/security.yml",
    "catalog/onprem-policy.yaml",
}

TEXT_SUFFIXES = {
    ".md",
    ".py",
    ".sh",
    ".yaml",
    ".yml",
    ".json",
    ".txt",
    ".toml",
    ".cfg",
    ".ini",
}

# Private project identifiers must never appear in the public fork.
PRIVATE_PROJECT_PATTERNS = (
    (r"waylens[-_a-z0-9]*", "private project identifier"),
    (r"\bfms-noti-sns\b", "private project identifier"),
    (r"\bfms-gps\b", "private project identifier"),
    (r"\bfms-core\b", "private project identifier"),
)

CREDENTIAL_PATTERNS = (
    (r"BEGIN (?:RSA|OPENSSH|EC|DSA|PGP) PRIVATE KEY", "private key material"),
    (r"\bglc_[A-Za-z0-9_\-]{8,}", "Grafana Cloud access token"),
    (r"\bgh[pousr]_[A-Za-z0-9]{20,}", "GitHub token"),
    (r"\bAKIA[0-9A-Z]{16}\b", "AWS access key id"),
    (r"(?i)\b(?:password|passwd|secret|api[_-]?key)\s*[:=]\s*['\"][^'\"\s]{6,}['\"]",
     "hardcoded credential"),
)

# Internal topology: RFC1918 literals and internal-only DNS suffixes.
TOPOLOGY_PATTERNS = (
    (r"\b10\.(?:\d{1,3}\.){2}\d{1,3}\b", "internal IP address"),
    (r"\b192\.168\.(?:\d{1,3})\.\d{1,3}\b", "internal IP address"),
    (r"\b172\.(?:1[6-9]|2\d|3[01])\.(?:\d{1,3})\.\d{1,3}\b", "internal IP address"),
    (r"[A-Za-z0-9\-]+\.(?:internal|intranet|corp|lan)\b", "internal hostname"),
)

# Operational state that goes stale and must not be frozen into public text.
INCIDENT_PATTERNS = (
    (r"(?i)\bINC-\d{3,}\b", "incident identifier"),
    (r"(?i)\bcurrently (?:broken|down|failing|degraded)\b", "current incident detail"),
)

ALL_PATTERNS = (
    PRIVATE_PROJECT_PATTERNS
    + CREDENTIAL_PATTERNS
    + TOPOLOGY_PATTERNS
    + INCIDENT_PATTERNS
)

COMPILED = [(re.compile(pattern), label) for pattern, label in ALL_PATTERNS]


def iter_files(root: Path, targets: tuple[str, ...]):
    for target in targets:
        base = root / target
        if not base.exists():
            continue
        if base.is_file():
            yield base
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            if any(part in SKIP_DIR_NAMES for part in path.parts):
                continue
            if path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            yield path


def scan(root: Path, targets: tuple[str, ...]) -> list[str]:
    findings: list[str] = []
    for path in iter_files(root, targets):
        rel = path.relative_to(root).as_posix()
        if rel in SELF_REFERENTIAL:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for regex, label in COMPILED:
                match = regex.search(line)
                if match:
                    findings.append(
                        f"{rel}:{lineno}: {label}: {match.group(0)[:60]}"
                    )
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="repository root to scan")
    parser.add_argument(
        "--target",
        action="append",
        dest="targets",
        help="path to scan (repeatable); defaults to the public delta paths",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"error: root is not a directory: {root}", file=sys.stderr)
        return 2

    targets = tuple(args.targets) if args.targets else DEFAULT_TARGETS
    findings = scan(root, targets)
    if findings:
        print("Private or internal content detected in the public fork:")
        for finding in findings:
            print(f"  {finding}")
        return 1

    print(f"scan-public-content: clean ({len(targets)} target paths)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
