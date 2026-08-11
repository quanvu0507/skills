#!/usr/bin/env python3
"""Generate the marketplace manifests, the skill registry and the on-prem allowlist.

Three agent hosts each read their own `marketplace.json`. Maintaining them by hand
guarantees drift, so one generator writes all three from the same inputs:

    .agents-plugin/marketplace.json   upstream plugin definitions (input + output)
    catalog/onprem-plugins.json       custom on-prem plugin definitions
    catalog/skill-tags.json           curated discovery tags per skill path
    catalog/onprem-policy.yaml        distribution boundary

Custom plugin entries are marked `managed_by: onprem-catalog` in the output, so a
regeneration strips and rebuilds exactly what it owns and leaves upstream entries
untouched. Running the generator twice produces identical bytes.

Exit codes:
    0  written (or, with --check, already up to date)
    1  --check found drift
    2  invalid input
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

MANAGED_MARKER = "onprem-catalog"

MARKETPLACE_FILES = (
    ".agents-plugin/marketplace.json",
    ".claude-plugin/marketplace.json",
    ".cursor-plugin/marketplace.json",
)
REGISTRY_FILE = "skill-registry.json"
ALLOWLIST_FILE = "catalog/onprem-allowlist.json"
CUSTOM_PLUGINS_FILE = "catalog/onprem-plugins.json"
SKILL_TAGS_FILE = "catalog/skill-tags.json"
POLICY_FILE = "catalog/onprem-policy.yaml"

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


class CatalogError(Exception):
    """Invalid input — exit code 2."""


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CatalogError(f"cannot read {path}: {exc}") from exc


def dumps(payload: dict) -> str:
    """Deterministic JSON: fixed indent, preserved key order, newline at EOF."""
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def parse_frontmatter(skill_md: Path) -> dict:
    text = skill_md.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise CatalogError(f"{skill_md}: missing YAML frontmatter")
    data = yaml.safe_load(match.group(1)) or {}
    for field in ("name", "description"):
        if not data.get(field):
            raise CatalogError(f"{skill_md}: frontmatter is missing '{field}'")
    return data


def discover_skills(root: Path) -> dict[str, list[str]]:
    """Map plugin group -> sorted skill paths, from SKILL.md files on disk."""
    groups: dict[str, list[str]] = {}
    for skill_md in sorted((root / "skills").glob("*/*/SKILL.md")):
        rel = skill_md.parent.relative_to(root).as_posix()
        groups.setdefault(skill_md.parent.parent.name, []).append(rel)
    return groups


def build_marketplace(root: Path, custom: dict) -> dict:
    marketplace = read_json(root / MARKETPLACE_FILES[0])
    upstream_plugins = [
        plugin
        for plugin in marketplace["plugins"]
        if plugin.get("managed_by") != MANAGED_MARKER
    ]

    custom_plugins = []
    for plugin in sorted(custom["plugins"], key=lambda p: p["name"]):
        for skill in plugin["skills"]:
            path = skill.removeprefix("./")
            if not (root / path / "SKILL.md").is_file():
                raise CatalogError(f"custom plugin {plugin['name']}: no SKILL.md at {path}")
            if path.startswith("skills/grafana-cloud/"):
                raise CatalogError(
                    f"custom plugin {plugin['name']} declares a Grafana Cloud skill: {path}"
                )
        custom_plugins.append(
            {
                "name": plugin["name"],
                "source": "./",
                "description": plugin["description"],
                "version": plugin["version"],
                "category": plugin["category"],
                "tags": list(plugin.get("tags", [])),
                "managed_by": MANAGED_MARKER,
                "skills": [f"./{s.removeprefix('./')}" for s in sorted(plugin["skills"])],
            }
        )

    upstream_names = {plugin["name"] for plugin in upstream_plugins}
    for plugin in custom_plugins:
        if plugin["name"] in upstream_names:
            raise CatalogError(f"custom plugin name collides with upstream: {plugin['name']}")

    marketplace["plugins"] = upstream_plugins + custom_plugins
    return marketplace


def build_registry(root: Path, marketplace: dict, tags: dict[str, list[str]]) -> dict:
    registry = read_json(root / REGISTRY_FILE)
    on_disk = discover_skills(root)
    plugin_tags = {plugin["name"]: plugin.get("tags", []) for plugin in marketplace["plugins"]}

    plugins = []
    for plugin in marketplace["plugins"]:
        group = plugin["name"]
        declared = [skill.removeprefix("./") for skill in plugin["skills"]]
        # Declared order first, then anything else found on disk for that group.
        paths = declared + [p for p in on_disk.get(group, []) if p not in declared]
        skills = []
        for path in paths:
            frontmatter = parse_frontmatter(root / path / "SKILL.md")
            skills.append(
                {
                    "name": frontmatter["name"],
                    "description": frontmatter["description"],
                    "path": path,
                    "tags": tags.get(path) or plugin_tags.get(group, []),
                }
            )
        plugins.append(
            {"name": group, "description": plugin["description"], "skills": skills}
        )

    registry["plugins"] = plugins
    return registry


def build_allowlist(root: Path, marketplace: dict, policy: dict) -> dict:
    """The deterministic on-prem allowlist the private installer consumes."""
    forbidden = tuple(policy.get("forbidden_skill_prefixes", ()))
    declared = {
        skill.removeprefix("./")
        for plugin in marketplace["plugins"]
        for skill in plugin["skills"]
    }
    allowed = []
    unknown = []
    for path in policy.get("allowed_skill_paths", []):
        if any(path.startswith(prefix) for prefix in forbidden):
            raise CatalogError(f"policy allows a forbidden path: {path}")
        if path in declared and (root / path / "SKILL.md").is_file():
            allowed.append(path)
        else:
            unknown.append(path)
    return {
        "schema_version": 1,
        "deployment_model": policy["deployment_model"],
        "forbidden_skill_prefixes": list(forbidden),
        "skills": sorted(allowed),
        "declared_but_not_yet_present": sorted(unknown),
    }


def generate(root: Path) -> dict[str, str]:
    custom = read_json(root / CUSTOM_PLUGINS_FILE)
    tags = read_json(root / SKILL_TAGS_FILE).get("tags", {})
    try:
        policy = yaml.safe_load((root / POLICY_FILE).read_text(encoding="utf-8"))
    except OSError as exc:
        raise CatalogError(f"cannot read {POLICY_FILE}: {exc}") from exc

    marketplace = build_marketplace(root, custom)
    registry = build_registry(root, marketplace, tags)
    allowlist = build_allowlist(root, marketplace, policy)

    marketplace_text = dumps(marketplace)
    outputs = {name: marketplace_text for name in MARKETPLACE_FILES}
    outputs[REGISTRY_FILE] = dumps(registry)
    outputs[ALLOWLIST_FILE] = dumps(allowlist)
    return outputs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="repository root")
    parser.add_argument(
        "--check", action="store_true", help="fail if any output is out of date"
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    try:
        outputs = generate(root)
    except CatalogError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    drifted = []
    for name, text in outputs.items():
        path = root / name
        current = path.read_text(encoding="utf-8") if path.is_file() else None
        if current != text:
            drifted.append(name)
            if not args.check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")

    if args.check:
        if drifted:
            print("Catalog is out of date; run scripts/generate-catalog.py:")
            for name in drifted:
                print(f"  {name}")
            return 1
        print("generate-catalog: up to date")
        return 0

    if drifted:
        print("generate-catalog: wrote " + ", ".join(drifted))
    else:
        print("generate-catalog: no changes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
