#!/usr/bin/env python3
"""Block Grafana Cloud and other SaaS dependencies from on-prem distribution.

The fork keeps upstream Cloud skills in the Git tree so synchronization stays
mechanical. This checker is what stops that material from reaching a catalog, a
project selection, a consumer lock, an installed skill tree, a generated config or
evaluated agent output.

It fails closed: an unknown deployment model or an unknown source mode is a
finding, not a default-allow.

Usage:
    python scripts/check-onprem-boundary.py \\
      --policy catalog/onprem-policy.yaml \\
      --marketplace .agents-plugin/marketplace.json \\
      --scan skills/onprem-observability

Exit codes:
    0  within the on-prem boundary
    1  boundary violation
    2  policy missing or unreadable
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

TEXT_SUFFIXES = {
    ".md", ".py", ".sh", ".yaml", ".yml", ".json", ".txt", ".toml", ".env", ".conf",
    ".river", ".alloy", ".tf", ".jsonnet", ".libsonnet",
}
SKIP_DIR_NAMES = {".git", "__pycache__", ".pytest_cache", ".venv", "node_modules"}


def _iter_text_files(root: Path):
    if root.is_file():
        yield root
        return
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        if path.suffix.lower() in TEXT_SUFFIXES:
            yield path


MANAGED_MARKER = "onprem-catalog"


def _marketplace_paths(marketplace: Path) -> list[str]:
    """Skill paths that would actually be distributed on-prem.

    A generated marketplace still lists the upstream `grafana-cloud` plugin,
    because the fork keeps that tree for synchronization. Only plugins the on-prem
    catalog manages are distribution candidates, so when the marker is present the
    upstream entries are source material and are skipped. Selection files carry no
    marker, so every path in them is checked.
    """
    payload = json.loads(marketplace.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "plugins" in payload:
        plugins = payload["plugins"]
        managed = [p for p in plugins if p.get("managed_by") == MANAGED_MARKER]
        considered = managed or plugins
        return [
            str(skill).removeprefix("./")
            for plugin in considered
            for skill in plugin.get("skills", [])
        ]
    if isinstance(payload, dict) and "skills" in payload:
        return [str(skill).removeprefix("./") for skill in payload["skills"]]
    if isinstance(payload, list):
        return [str(skill).removeprefix("./") for skill in payload]
    return []


def check(
    policy: dict,
    *,
    marketplace: Path | None = None,
    scan_roots: list[Path] | None = None,
    source_mode: str | None = None,
    policy_path: Path | None = None,
) -> list[str]:
    """Return a list of findings; empty means the artifact is distributable."""
    findings: list[str] = []

    if policy.get("deployment_model") != "onprem":
        findings.append(
            f"deployment model must be exactly 'onprem', got "
            f"{policy.get('deployment_model')!r}"
        )

    allowed_modes = policy.get("allowed_source_modes") or []
    if source_mode is not None and source_mode not in allowed_modes:
        findings.append(
            f"source mode {source_mode!r} is not one of {sorted(allowed_modes)}"
        )

    forbidden_prefixes = tuple(policy.get("forbidden_skill_prefixes", ()))
    if marketplace is not None:
        for path in _marketplace_paths(marketplace):
            for prefix in forbidden_prefixes:
                if path.startswith(prefix):
                    findings.append(
                        f"{marketplace}: selected path is not distributable: {path}"
                    )

    domains = tuple(policy.get("forbidden_domains", ()))
    literals = tuple(policy.get("forbidden_literals", ()))
    # The policy file lists the forbidden strings by definition, so scanning it
    # would report itself. Same for the allowlist it produces.
    self_excluded = {Path(policy_path).resolve()} if policy_path else set()
    # Files that must name the forbidden values in order to refuse them.
    repo_root = Path(policy_path).resolve().parents[1] if policy_path else Path.cwd()
    for refusal in policy.get("documented_refusal_paths", ()):  # exact paths only
        self_excluded.add((repo_root / refusal).resolve())
    for root in scan_roots or []:
        if not Path(root).exists():
            continue
        for file_path in _iter_text_files(Path(root)):
            if file_path.resolve() in self_excluded:
                continue
            try:
                text = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for lineno, line in enumerate(text.splitlines(), start=1):
                for domain in domains:
                    if domain in line:
                        findings.append(
                            f"{file_path}:{lineno}: forbidden SaaS domain: {domain}"
                        )
                for literal in literals:
                    if literal in line:
                        findings.append(
                            f"{file_path}:{lineno}: forbidden cloud literal: {literal}"
                        )

    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", required=True, help="path to onprem-policy.yaml")
    parser.add_argument("--marketplace", help="generated marketplace or selection file")
    parser.add_argument(
        "--scan", action="append", default=[], dest="scan",
        help="directory or file to scan for forbidden domains/literals (repeatable)",
    )
    parser.add_argument(
        "--source-mode",
        help="source mode to validate (connected-git, internal-mirror, local-checkout)",
    )
    args = parser.parse_args(argv)

    policy_path = Path(args.policy)
    try:
        policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        print(f"error: cannot read policy {policy_path}: {exc}", file=sys.stderr)
        return 2
    if not isinstance(policy, dict):
        print(f"error: policy {policy_path} is not a mapping", file=sys.stderr)
        return 2

    findings = check(
        policy,
        marketplace=Path(args.marketplace) if args.marketplace else None,
        scan_roots=[Path(p) for p in args.scan],
        source_mode=args.source_mode,
        policy_path=policy_path,
    )

    if findings:
        print("On-prem boundary violations:")
        for finding in findings:
            print(f"  {finding}")
        return 1

    print("check-onprem-boundary: within the on-prem boundary")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
