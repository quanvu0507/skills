"""On-prem distribution must fail closed for cloud, SaaS and unknown contexts."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / "catalog" / "onprem-policy.yaml"

_spec = importlib.util.spec_from_file_location(
    "check_onprem_boundary", REPO_ROOT / "scripts" / "check-onprem-boundary.py"
)
assert _spec and _spec.loader
checker = importlib.util.module_from_spec(_spec)
sys.modules["check_onprem_boundary"] = checker
_spec.loader.exec_module(checker)


@pytest.fixture
def policy() -> dict:
    return yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))


def _policy_file(tmp_path: Path, policy: dict) -> Path:
    path = tmp_path / "policy.yaml"
    path.write_text(yaml.safe_dump(policy, sort_keys=False), encoding="utf-8")
    return path


def _marketplace(tmp_path: Path, skill_paths: list[str]) -> Path:
    path = tmp_path / "marketplace.json"
    path.write_text(
        json.dumps({"plugins": [{"name": "onprem-observability", "skills": skill_paths}]}),
        encoding="utf-8",
    )
    return path


def test_deployment_model_is_onprem(policy) -> None:
    assert policy["deployment_model"] == "onprem"


def test_grafana_cloud_paths_are_not_allowlisted(policy) -> None:
    for path in policy["allowed_skill_paths"]:
        assert not path.startswith("skills/grafana-cloud/")


def test_selected_grafana_cloud_path_is_rejected(tmp_path: Path, policy) -> None:
    marketplace = _marketplace(
        tmp_path, ["./skills/grafana-cloud/adaptive-metrics", "./skills/grafana-lgtm/loki"]
    )
    findings = checker.check(
        policy, marketplace=marketplace, scan_roots=[], source_mode="local-checkout"
    )
    assert any("grafana-cloud" in finding for finding in findings)


def test_forbidden_saas_domains_are_rejected(tmp_path: Path, policy) -> None:
    scan = tmp_path / "skills"
    scan.mkdir()
    (scan / "SKILL.md").write_text(
        "Send metrics to prometheus-prod-01.grafana.net for storage.\n", encoding="utf-8"
    )
    findings = checker.check(
        policy, marketplace=None, scan_roots=[scan], source_mode="local-checkout"
    )
    assert any("grafana.net" in finding for finding in findings)


def test_grafana_cloud_tokens_and_roles_are_rejected(tmp_path: Path, policy) -> None:
    scan = tmp_path / "skills"
    scan.mkdir()
    (scan / "SKILL.md").write_text(
        "Create an access policy with the MetricsPublisher role and a glc_ token.\n",
        encoding="utf-8",
    )
    findings = checker.check(
        policy, marketplace=None, scan_roots=[scan], source_mode="local-checkout"
    )
    assert any("MetricsPublisher" in finding for finding in findings)
    assert any("glc_" in finding for finding in findings)


@pytest.mark.parametrize("mode", ["connected-git", "internal-mirror", "local-checkout"])
def test_allowed_source_modes(tmp_path: Path, policy, mode: str) -> None:
    findings = checker.check(policy, marketplace=None, scan_roots=[], source_mode=mode)
    assert findings == []


def test_unknown_source_mode_is_rejected(tmp_path: Path, policy) -> None:
    findings = checker.check(
        policy, marketplace=None, scan_roots=[], source_mode="cloud-api"
    )
    assert any("source mode" in finding for finding in findings)


def test_unknown_deployment_model_fails_closed(tmp_path: Path, policy) -> None:
    for model in ("cloud", "saas", "", None):
        broken = dict(policy)
        broken["deployment_model"] = model
        findings = checker.check(
            broken, marketplace=None, scan_roots=[], source_mode="local-checkout"
        )
        assert any("deployment model" in finding for finding in findings), model


def test_immutable_upstream_text_is_not_scanned(tmp_path: Path, policy) -> None:
    """Upstream skills document Cloud variants; the text stays, execution does not."""
    upstream = tmp_path / "skills" / "grafana-core" / "alloy"
    upstream.mkdir(parents=True)
    (upstream / "SKILL.md").write_text(
        'password = sys.env("GRAFANA_CLOUD_API_KEY")  # prometheus-prod.grafana.net\n',
        encoding="utf-8",
    )
    findings = checker.check(
        policy, marketplace=None, scan_roots=[], source_mode="local-checkout"
    )
    assert findings == []


def test_repository_passes_its_own_policy() -> None:
    policy = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
    findings = checker.check(
        policy,
        marketplace=REPO_ROOT / ".agents-plugin" / "marketplace.json",
        scan_roots=[REPO_ROOT / "skills" / "onprem-observability", REPO_ROOT / "catalog"],
        source_mode="local-checkout",
        policy_path=POLICY_PATH,
    )
    assert findings == [], findings


def test_documented_refusal_paths_are_exact_files(policy) -> None:
    """The exemption must never widen into a directory or a glob."""
    for entry in policy.get("documented_refusal_paths", []):
        assert "*" not in entry
        assert (REPO_ROOT / entry).is_file(), entry


def test_refusal_exemption_does_not_cover_siblings(tmp_path: Path, policy) -> None:
    """A file next to an exempt one is still scanned."""
    scan = REPO_ROOT / "skills" / "onprem-observability" / "observability-contract"
    findings = checker.check(
        policy, marketplace=None, scan_roots=[scan],
        source_mode="local-checkout", policy_path=POLICY_PATH,
    )
    assert findings == [], findings
