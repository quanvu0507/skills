# Fork governance

## Why the upstream review workflows were replaced

Upstream `grafana/skills` runs two workflows that authenticate to Grafana's
internal Vault through OIDC:

| Upstream workflow | Internal dependency |
|---|---|
| `.github/workflows/skill-review.yml` | `get-vault-secrets` → `tessl-token:token` (Tessl API) |
| `.github/workflows/agent-scan.yml` | `get-vault-secrets` → `snyk-token:token` (Snyk API) |

A fork has no Vault role and no `id-token` trust relationship with Grafana, so
both jobs fail on every run. Both were removed and replaced with equivalents that
need no external credentials.

## Fork CI

| Workflow | Canonical source | Purpose |
|---|---|---|
| `.github/workflows/fork-quality.yml` | `fork-config/workflows/quality.yml` | lint, unit tests, catalog check, upstream boundary |
| `.github/workflows/fork-security.yml` | `fork-config/workflows/security.yml` | public-content scan, secret-like content gate |
| `.github/workflows/lint-skills.yml` | upstream | preserved unchanged |
| `.github/workflows/validate.yml` | upstream | preserved unchanged |

`fork-config/workflows/` holds the canonical text. `scripts/sync-upstream.py`
restores those files into `.github/workflows/fork-*.yml` after each upstream
merge, so an upstream change can never silently reintroduce a Vault dependency.
`tests/test_public_workflows.py` fails if the installed copy drifts from its
canonical source or if a Vault reference reappears.

**Edit the file in `fork-config/workflows/`, never the copy in `.github/workflows/`.**

## Content boundaries

Two scanners guard what this public repository may contain:

- `scripts/scan-public-content.py` rejects private project identifiers, internal
  hostnames and IP ranges, credentials and current incident detail in fork-owned
  paths.
- `scripts/check-onprem-boundary.py` rejects Grafana Cloud and other SaaS paths,
  domains and literals from anything that becomes a distribution artifact.

Immutable upstream text under `skills/grafana-*` is out of scope for both scanners.
It documents Cloud variants and stays as-is so upstream sync remains mechanical;
what the policy blocks is that text entering an on-prem catalog, selection, lock
or installed skill tree.

## Upstream-owned paths

Everything under `skills/grafana-*` is read-only in this fork. Changing it requires
an entry in the allowlist inside `scripts/check-upstream-boundary.py`, a test that
covers the change and a stated security or correctness reason. Fixes that are
generically useful should be sent upstream instead — see
[`docs/upstream-contributions.md`](upstream-contributions.md).
