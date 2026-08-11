"""Fork CI must run without Grafana-internal Vault roles or secrets."""

from pathlib import Path

FORBIDDEN = (
    "grafana/shared-workflows/actions/get-vault-secrets",
    "vault_instance:",
    "tessl-token:token",
    "snyk-token:token",
)


def _workflow_text() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(Path(".github/workflows").glob("*.yml"))
    )


def test_fork_workflows_do_not_require_grafana_vault() -> None:
    text = _workflow_text()
    for token in FORBIDDEN:
        assert token not in text


def test_fork_workflow_overrides_are_mirrored_in_fork_config() -> None:
    """sync-upstream restores overrides from fork-config; they must stay in step."""
    for override in sorted(Path("fork-config/workflows").glob("*.yml")):
        installed = Path(".github/workflows") / f"fork-{override.name}"
        assert installed.is_file(), f"missing installed override: {installed}"
        assert installed.read_text(encoding="utf-8") == override.read_text(
            encoding="utf-8"
        ), f"{installed} drifted from {override}"


def test_replaced_workflows_are_absent() -> None:
    for name in ("skill-review.yml", "agent-scan.yml"):
        assert not (Path(".github/workflows") / name).exists()
