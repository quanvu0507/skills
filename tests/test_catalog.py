"""Marketplace manifests and the skill registry come from one generator.

Three agent hosts read three separate marketplace files. They drift the moment a
human edits one of them, so the generator writes all three and these tests hold
them to a single source of truth.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
MARKETPLACES = (
    REPO_ROOT / ".agents-plugin" / "marketplace.json",
    REPO_ROOT / ".claude-plugin" / "marketplace.json",
    REPO_ROOT / ".cursor-plugin" / "marketplace.json",
)
REGISTRY = REPO_ROOT / "skill-registry.json"
CUSTOM_PLUGINS = REPO_ROOT / "catalog" / "onprem-plugins.json"
POLICY = REPO_ROOT / "catalog" / "onprem-policy.yaml"
ALLOWLIST = REPO_ROOT / "catalog" / "onprem-allowlist.json"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _marketplace_skill_paths() -> list[str]:
    marketplace = _json(MARKETPLACES[0])
    return [
        skill.removeprefix("./")
        for plugin in marketplace["plugins"]
        for skill in plugin["skills"]
    ]


def test_three_marketplace_files_are_byte_identical() -> None:
    contents = [path.read_bytes() for path in MARKETPLACES]
    assert contents[0] == contents[1] == contents[2]


def test_every_declared_path_contains_skill_md() -> None:
    missing = [
        path for path in _marketplace_skill_paths()
        if not (REPO_ROOT / path / "SKILL.md").is_file()
    ]
    assert missing == []


def test_no_duplicate_plugin_or_skill_path() -> None:
    marketplace = _json(MARKETPLACES[0])
    names = [plugin["name"] for plugin in marketplace["plugins"]]
    assert len(names) == len(set(names))
    paths = _marketplace_skill_paths()
    assert len(paths) == len(set(paths))


def test_every_custom_skill_is_registered() -> None:
    """A custom skill on disk that nobody declared is invisible to every host."""
    declared = set(_marketplace_skill_paths())
    on_disk = {
        skill_md.parent.relative_to(REPO_ROOT).as_posix()
        for group in ("onprem-observability", "onprem-observability-adapters")
        for skill_md in (REPO_ROOT / "skills" / group).glob("*/SKILL.md")
    }
    assert on_disk - declared == set()


def test_registry_contains_all_marketplace_skills() -> None:
    registry = _json(REGISTRY)
    registered = {
        skill["path"]
        for plugin in registry["plugins"]
        for skill in plugin["skills"]
    }
    assert set(_marketplace_skill_paths()) - registered == set()


def test_grafana_core_registry_is_not_empty() -> None:
    registry = _json(REGISTRY)
    core = next(p for p in registry["plugins"] if p["name"] == "grafana-core")
    assert core["skills"]


def test_onprem_plugin_contains_no_grafana_cloud_skill() -> None:
    """Custom plugins must never distribute a Grafana Cloud skill."""
    custom = _json(CUSTOM_PLUGINS)
    for plugin in custom["plugins"]:
        for skill in plugin["skills"]:
            assert not skill.removeprefix("./").startswith("skills/grafana-cloud/")


def test_onprem_policy_forbids_saas_endpoints() -> None:
    policy = yaml.safe_load(POLICY.read_text(encoding="utf-8"))
    assert policy["deployment_model"] == "onprem"
    assert "skills/grafana-cloud/" in policy["forbidden_skill_prefixes"]
    for domain in ("grafana.net", "api.k6.io", "cloudlogs.k6.io"):
        assert domain in policy["forbidden_domains"]
    assert "glc_" in policy["forbidden_literals"]


def test_allowlist_excludes_forbidden_prefixes() -> None:
    allowlist = _json(ALLOWLIST)
    for path in allowlist["skills"]:
        assert not path.startswith("skills/grafana-cloud/")


def test_generator_is_idempotent() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/generate-catalog.py", "--check"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
