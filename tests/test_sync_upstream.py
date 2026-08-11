"""Upstream sync must preserve custom skills and gate the baseline on validation."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location(
    "sync_upstream", REPO_ROOT / "scripts" / "sync-upstream.py"
)
assert _spec and _spec.loader
sync_upstream = importlib.util.module_from_spec(_spec)
sys.modules["sync_upstream"] = sync_upstream
_spec.loader.exec_module(sync_upstream)


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def _write(repo: Path, relative: str, body: str) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _init(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "test")


@pytest.fixture
def fork_and_upstream(tmp_path: Path) -> tuple[Path, Path]:
    """An upstream repo with a new commit, and a fork that carries a local delta."""
    upstream = tmp_path / "upstream"
    _init(upstream)
    _write(upstream, "skills/grafana-core/promql/SKILL.md", "# PromQL\n")
    _write(upstream, ".github/workflows/skill-review.yml", "name: Skill Review\n")
    _git(upstream, "add", "-A")
    _git(upstream, "commit", "-qm", "upstream baseline")
    baseline = _git(upstream, "rev-parse", "HEAD")

    fork = tmp_path / "fork"
    subprocess.run(
        ["git", "clone", "-q", str(upstream), str(fork)], check=True, capture_output=True
    )
    _git(fork, "config", "user.email", "test@example.com")
    _git(fork, "config", "user.name", "test")
    _git(fork, "remote", "add", "upstream", str(upstream))

    # Fork delta: custom skill, canonical workflow overrides, upstream workflow removed.
    _write(fork, "skills/onprem-observability/contract/SKILL.md", "# Contract\n")
    _write(fork, "fork-config/workflows/quality.yml", "name: Fork Quality\n")
    _write(fork, "fork-config/workflows/security.yml", "name: Fork Security\n")
    _write(fork, ".github/workflows/fork-quality.yml", "name: Fork Quality\n")
    _write(fork, ".github/workflows/fork-security.yml", "name: Fork Security\n")
    (fork / ".github/workflows/skill-review.yml").unlink()
    _write(fork, "UPSTREAM_BASE", baseline + "\n")
    _git(fork, "add", "-A")
    _git(fork, "commit", "-qm", "fork delta")

    # New upstream work to be merged.
    _write(upstream, "skills/grafana-lgtm/loki/SKILL.md", "# Loki\n")
    _git(upstream, "add", "-A")
    _git(upstream, "commit", "-qm", "upstream: add loki skill")

    return fork, upstream


def test_sync_preserves_custom_skills_and_upstream_history(fork_and_upstream) -> None:
    fork, upstream = fork_and_upstream
    code, message = sync_upstream.sync(fork, "upstream/main")

    assert code == 0, message
    assert (fork / "skills/onprem-observability/contract/SKILL.md").is_file()
    assert (fork / "skills/grafana-lgtm/loki/SKILL.md").is_file()
    # The merge keeps upstream history reachable rather than replaying it.
    assert _git(upstream, "rev-parse", "HEAD") in _git(fork, "log", "--format=%H")


def test_sync_restores_fork_workflow_overrides(fork_and_upstream) -> None:
    fork, upstream = fork_and_upstream
    # Upstream reintroduces the Vault-dependent workflow.
    _write(upstream, ".github/workflows/agent-scan.yml", "name: Snyk Agent Scan\n")
    _git(upstream, "add", "-A")
    _git(upstream, "commit", "-qm", "upstream: agent scan")

    code, message = sync_upstream.sync(fork, "upstream/main")

    assert code == 0, message
    assert not (fork / ".github/workflows/agent-scan.yml").exists()
    assert not (fork / ".github/workflows/skill-review.yml").exists()
    assert (fork / ".github/workflows/fork-quality.yml").read_text() == "name: Fork Quality\n"


def test_failed_validation_does_not_advance_baseline(fork_and_upstream, monkeypatch) -> None:
    fork, _ = fork_and_upstream
    before = (fork / "UPSTREAM_BASE").read_text(encoding="utf-8")

    monkeypatch.setattr(sync_upstream, "run_validation", lambda repo: (False, "boom"))
    code, message = sync_upstream.sync(fork, "upstream/main")

    assert code == 1
    assert "UPSTREAM_BASE unchanged" in message
    assert (fork / "UPSTREAM_BASE").read_text(encoding="utf-8") == before


def test_branch_name_is_deterministic(fork_and_upstream) -> None:
    fork, _ = fork_and_upstream
    _git(fork, "fetch", "-q", "upstream", "main")
    fixed = datetime(2026, 8, 11, tzinfo=timezone.utc)
    first = sync_upstream.branch_name(fork, "upstream/main", fixed)
    second = sync_upstream.branch_name(fork, "upstream/main", fixed)
    assert first == second
    assert first.startswith("sync/upstream-20260811-")


def test_dirty_worktree_is_refused(fork_and_upstream) -> None:
    fork, _ = fork_and_upstream
    (fork / "dirty.txt").write_text("uncommitted\n", encoding="utf-8")
    with pytest.raises(sync_upstream.SyncError):
        sync_upstream.sync(fork, "upstream/main")
