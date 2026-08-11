"""The public fork must never publish private project or infrastructure detail."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location(
    "scan_public_content", REPO_ROOT / "scripts" / "scan-public-content.py"
)
assert _spec and _spec.loader
scan_public_content = importlib.util.module_from_spec(_spec)
sys.modules["scan_public_content"] = scan_public_content
_spec.loader.exec_module(scan_public_content)


def _scan(tmp_path: Path, relative: str, body: str) -> list[str]:
    target = tmp_path / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    return scan_public_content.scan(tmp_path, ("docs",))


def test_repository_is_clean() -> None:
    assert scan_public_content.scan(REPO_ROOT, scan_public_content.DEFAULT_TARGETS) == []


def test_private_project_name_is_rejected(tmp_path: Path) -> None:
    findings = _scan(tmp_path, "docs/example.md", "See waylens-fms-gps for details.\n")
    assert findings and "private project identifier" in findings[0]


def test_cloud_token_is_rejected(tmp_path: Path) -> None:
    findings = _scan(tmp_path, "docs/example.md", "token: glc_abcdef123456\n")
    assert findings and "Grafana Cloud access token" in findings[0]


def test_internal_hostname_is_rejected(tmp_path: Path) -> None:
    findings = _scan(tmp_path, "docs/example.md", "url: https://grafana.internal/api\n")
    assert findings and "internal hostname" in findings[0]


def test_internal_ip_is_rejected(tmp_path: Path) -> None:
    findings = _scan(tmp_path, "docs/example.md", "remote_write: 10.20.30.40:8428\n")
    assert findings and "internal IP address" in findings[0]


def test_incident_reference_is_rejected(tmp_path: Path) -> None:
    findings = _scan(tmp_path, "docs/example.md", "Blocked by INC-4821 since Monday.\n")
    assert findings and "incident identifier" in findings[0]


def test_generic_onprem_text_is_accepted(tmp_path: Path) -> None:
    body = (
        "# Metrics pipeline\n\n"
        "Route application metrics to VictoriaMetrics through vmagent.\n"
        "Endpoints come from the environment profile, never from this document.\n"
    )
    assert _scan(tmp_path, "docs/example.md", body) == []
