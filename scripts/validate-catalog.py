#!/usr/bin/env python3
"""Validate the generated catalog independently of the generator that wrote it.

A generator bug that produces self-consistent nonsense is invisible to
`generate-catalog.py --check`. This validator re-derives every invariant from the
files on disk instead.

Exit codes:
    0  valid
    1  invariant violated
    2  a required file is missing or unreadable
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

MARKETPLACE_FILES = (
    ".agents-plugin/marketplace.json",
    ".claude-plugin/marketplace.json",
    ".cursor-plugin/marketplace.json",
)
REGISTRY_FILE = "skill-registry.json"
ALLOWLIST_FILE = "catalog/onprem-allowlist.json"
POLICY_FILE = "catalog/onprem-policy.yaml"
CUSTOM_GROUPS = (
    "onprem-observability",
    "onprem-observability-adapters",
    "onprem-platform",
)

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def validate(root: Path) -> list[str]:
    errors: list[str] = []

    for name in (*MARKETPLACE_FILES, REGISTRY_FILE, ALLOWLIST_FILE, POLICY_FILE):
        if not (root / name).is_file():
            errors.append(f"missing required file: {name}")
    if errors:
        return errors

    payloads = [(root / name).read_bytes() for name in MARKETPLACE_FILES]
    if len(set(payloads)) != 1:
        errors.append("marketplace manifests are not byte-identical")

    marketplace = json.loads((root / MARKETPLACE_FILES[0]).read_text(encoding="utf-8"))
    registry = json.loads((root / REGISTRY_FILE).read_text(encoding="utf-8"))
    allowlist = json.loads((root / ALLOWLIST_FILE).read_text(encoding="utf-8"))
    policy = yaml.safe_load((root / POLICY_FILE).read_text(encoding="utf-8"))

    plugin_names = [plugin["name"] for plugin in marketplace["plugins"]]
    if len(plugin_names) != len(set(plugin_names)):
        errors.append("duplicate plugin name in marketplace")

    declared: list[str] = []
    for plugin in marketplace["plugins"]:
        for skill in plugin["skills"]:
            path = skill.removeprefix("./")
            declared.append(path)
            if not (root / path / "SKILL.md").is_file():
                errors.append(f"declared path has no SKILL.md: {path}")
    if len(declared) != len(set(declared)):
        errors.append("duplicate skill path in marketplace")

    registered = {
        skill["path"] for plugin in registry["plugins"] for skill in plugin["skills"]
    }
    for path in sorted(set(declared) - registered):
        errors.append(f"declared in marketplace but missing from registry: {path}")

    for plugin in registry["plugins"]:
        group_declared = [
            skill.removeprefix("./")
            for entry in marketplace["plugins"]
            if entry["name"] == plugin["name"]
            for skill in entry["skills"]
        ]
        if group_declared and not plugin["skills"]:
            errors.append(f"registry group is empty but declared: {plugin['name']}")

    # Every custom skill on disk must be declared exactly once.
    for group in CUSTOM_GROUPS:
        for skill_md in sorted((root / "skills" / group).glob("*/SKILL.md")):
            path = skill_md.parent.relative_to(root).as_posix()
            if declared.count(path) != 1:
                errors.append(
                    f"custom skill declared {declared.count(path)} times: {path}"
                )

    # Registry names must match the skill frontmatter they claim to describe.
    for plugin in registry["plugins"]:
        for skill in plugin["skills"]:
            skill_md = root / skill["path"] / "SKILL.md"
            if not skill_md.is_file():
                errors.append(f"registry path has no SKILL.md: {skill['path']}")
                continue
            match = FRONTMATTER_RE.match(skill_md.read_text(encoding="utf-8"))
            frontmatter = yaml.safe_load(match.group(1)) if match else {}
            if frontmatter.get("name") != skill["name"]:
                errors.append(
                    f"registry name {skill['name']!r} does not match frontmatter "
                    f"{frontmatter.get('name')!r} at {skill['path']}"
                )

    forbidden = tuple(policy.get("forbidden_skill_prefixes", ()))
    for path in allowlist["skills"]:
        if any(path.startswith(prefix) for prefix in forbidden):
            errors.append(f"allowlist contains a forbidden path: {path}")
        if path not in declared:
            errors.append(f"allowlist path is not declared in the marketplace: {path}")
    if allowlist.get("deployment_model") != "onprem":
        errors.append("allowlist deployment_model is not 'onprem'")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="repository root")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    try:
        errors = validate(root)
    except (OSError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if errors:
        print("Catalog validation failed:")
        for error in errors:
            print(f"  {error}")
        return 1

    print("validate-catalog: all invariants hold")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
