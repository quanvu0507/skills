# On-premises runtime boundary

The deployment model is fixed to `onprem`. Every distribution artifact — catalog,
allowlist, project selection, consumer lock, installed skill tree, generated
config, evaluated agent output — is checked against
[`catalog/onprem-policy.yaml`](../catalog/onprem-policy.yaml) before release.

## The four rules

```text
GitHub/internal Git is a source-control option, not a runtime dependency.
Telemetry data remains inside the on-prem network.
Internet lookup is optional and cannot be required for normal execution.
Air-gapped environments use an internal mirror or verified local bundle.
```

## Backends

| Signal | Backend |
|---|---|
| metrics | VictoriaMetrics (`vmagent` + `vmsingle` or `vmcluster`) |
| logs | Loki OSS |
| visualization | Grafana OSS |
| collection | Grafana Alloy |

Every data-plane endpoint comes from the project's environment profile as an
internal DNS name or address. A skill never hardcodes one.

## Out of scope

```text
Grafana Cloud stacks and APIs
Hosted Mimir/Loki/Tempo/Pyroscope
Grafana Cloud OTLP gateway and cloud publisher roles
Adaptive Metrics, DPM Finder and cloud cost-management workflows
Cloud integrations and private-connectivity products
Grafana Cloud k6 test management
Any recommendation that exports telemetry outside the on-prem network
```

## Immutable upstream text

Upstream skills under `skills/grafana-*` frequently document an OSS path and a
Cloud path in the same file. The fork does not edit them: rewriting upstream text
would turn every sync into a manual merge, and the text itself harms nothing.

What the policy blocks is that material becoming executable guidance:

- it never enters the on-prem catalog, a selection, a lock or an installed tree;
- the private on-prem runtime contract has higher precedence and forbids emitting
  Cloud endpoints, credentials or operations;
- benchmark and output checks fail a release when an agent emits a Cloud branch.

`immutable_upstream_content_policy: allow-text-but-forbid-cloud-execution` in the
policy file records this decision in machine-readable form.

## Cloud request mapping

| Requested | On-prem equivalent |
|---|---|
| Grafana Cloud Metrics | VictoriaMetrics |
| Grafana Cloud Logs | Loki OSS |
| Grafana Cloud OTLP gateway | internal Alloy/collector endpoint |
| Adaptive Metrics | source-side label redesign, recording rules, retention policy |
| Cloud k6 | k6 OSS executed inside the controlled network |

## Running the checker

```bash
python scripts/check-onprem-boundary.py \
  --policy catalog/onprem-policy.yaml \
  --marketplace .agents-plugin/marketplace.json \
  --scan skills/onprem-observability
```

It fails when:

1. the deployment model is not exactly `onprem`;
2. a selected or installed path starts with `skills/grafana-cloud/`;
3. a custom skill, selection, generated config or evaluated agent output contains
   a forbidden domain or literal;
4. a normal workflow requires an external SaaS API;
5. the source mode is not `connected-git`, `internal-mirror` or `local-checkout`.

Unknown values are findings, not defaults: the checker fails closed.

## Source modes

| Mode | Network requirement | Use |
|---|---|---|
| `connected-git` | outbound Git to GitHub or an internal Git server | normal development hosts |
| `internal-mirror` | none outside the internal network | restricted and air-gapped networks |
| `local-checkout` | none | development and test |

All three must resolve to the same skill set and the same SHA-256 manifest.
