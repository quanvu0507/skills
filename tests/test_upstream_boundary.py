"""Upstream-owned skill paths must stay read-only in this fork."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER = REPO_ROOT / "scripts" / "check-upstream-boundary.py"


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def _write(repo: Path, relative: str, body: str) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _run_checker(repo: Path, base: str, head: str = "HEAD") -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CHECKER), "--repo", str(repo), "--base", base, "--head", head],
        capture_output=True,
        text=True,
    )


@pytest.fixture
def baseline_repo(tmp_path: Path) -> tuple[Path, str]:
    """A repository shaped like the fork, with one upstream baseline commit."""
    repo = tmp_path / "fork"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "test")

    _write(repo, "skills/grafana-core/promql/SKILL.md", "---\nname: promql\n---\n# PromQL\n")
    _write(repo, "skills/grafana-lgtm/loki/SKILL.md", "---\nname: loki\n---\n# Loki\n")
    _write(repo, ".agents-plugin/marketplace.json", '{"plugins": []}\n')
    _write(repo, "README.md", "# fork\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "baseline")
    return repo, _git(repo, "rev-parse", "HEAD")


def test_modifying_upstream_skill_is_rejected(baseline_repo) -> None:
    repo, base = baseline_repo
    _write(repo, "skills/grafana-core/promql/SKILL.md", "---\nname: promql\n---\n# Edited\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "edit upstream skill")

    result = _run_checker(repo, base)
    assert result.returncode == 1
    assert "skills/grafana-core/promql/SKILL.md" in result.stdout


def test_adding_custom_onprem_skill_is_accepted(baseline_repo) -> None:
    repo, base = baseline_repo
    _write(
        repo,
        "skills/onprem-observability/example/SKILL.md",
        "---\nname: example\n---\n# Example\n",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "add custom skill")

    result = _run_checker(repo, base)
    assert result.returncode == 0, result.stdout + result.stderr


def test_regenerated_manifest_is_accepted(baseline_repo) -> None:
    repo, base = baseline_repo
    _write(repo, ".agents-plugin/marketplace.json", '{"plugins": [{"name": "x"}]}\n')
    _write(repo, "skill-registry.json", '{"plugins": []}\n')
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "regenerate manifests")

    result = _run_checker(repo, base)
    assert result.returncode == 0, result.stdout + result.stderr


def test_deleting_upstream_skill_is_rejected(baseline_repo) -> None:
    repo, base = baseline_repo
    (repo / "skills/grafana-lgtm/loki/SKILL.md").unlink()
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "delete upstream skill")

    result = _run_checker(repo, base)
    assert result.returncode == 1


def test_invalid_baseline_exits_two(baseline_repo) -> None:
    repo, _ = baseline_repo
    result = _run_checker(repo, "not-a-revision")
    assert result.returncode == 2


def test_allowlist_contains_no_path_traversal() -> None:
    source = CHECKER.read_text(encoding="utf-8")
    assert ".." not in source.split("ALLOWED_PATTERNS = (")[1].split(")")[0]


def test_this_repository_respects_the_boundary() -> None:
    base = (REPO_ROOT / "UPSTREAM_BASE").read_text(encoding="utf-8").strip()
    result = _run_checker(REPO_ROOT, base)
    assert result.returncode == 0, result.stdout + result.stderr
