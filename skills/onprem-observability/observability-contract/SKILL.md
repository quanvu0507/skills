---
name: observability-contract
license: Apache-2.0
compatibility: "Grafana OSS, Loki OSS, Alloy, VictoriaMetrics, Kubernetes/Talos; no Grafana Cloud dependency"
description: "On-premises-only observability contract for logs, metrics, correlation and rollout. Enforces bounded metric cardinality, JSON-Lines logs on stdout, internal-only telemetry backends (Grafana OSS, Loki OSS, Alloy, VictoriaMetrics) and evidence-based rollout. Use when asked to standardize logs, add metrics, integrate Loki or Grafana, review an observability plan, design a label strategy, instrument a legacy Scala/Play service, or work against a VictoriaMetrics-backed Grafana — and use it before any language- or runtime-specific observability skill."
---

# On-premises observability contract

The durable rules every on-prem service follows, independent of language, runtime
and orchestrator. Language adapters and runtime skills implement this contract;
they never override it.

## Deployment gate

This contract applies **only** when the environment declares
`deployment_model: onprem`. If the model is `cloud`, `saas`, missing or unknown,
stop and report it — do not fall back to a default.

Telemetry stays inside the internal network:

| Signal | Backend |
|---|---|
| metrics | VictoriaMetrics |
| logs | Loki OSS |
| visualization | Grafana OSS |
| collection | Grafana Alloy |

Never recommend Grafana Cloud stacks or APIs, hosted Mimir/Loki/Tempo/Pyroscope,
the Grafana Cloud OTLP gateway, Adaptive Metrics, DPM Finder, Fleet Management,
Cloud Integrations, Private Connectivity, Grafana Cloud k6 or any destination
outside the network declared by the environment profile. See
[`references/skill-routing.md`](references/skill-routing.md) for the on-prem
replacement of each cloud feature.

## The five rules

1. **Logs are JSON Lines on stdout.** One line per event, one terminal event per
   HTTP request. No payloads, credentials, cookies, signed queries or decoded
   authentication data. → [`references/logging-contract.md`](references/logging-contract.md)

2. **Metric labels are finite.** Enum values or normalized route templates only.
   Never a raw URI, request ID, correlation ID, device serial, fleet ID, user ID,
   actor path, exception message, Kafka topic/offset or payload value.
   → [`references/metrics-contract.md`](references/metrics-contract.md)

3. **High-cardinality identity belongs in logs, not in labels.** Correlate by
   querying log fields at read time, never by promoting an ID to a metric label or
   a Loki index label.
   → [`references/correlation-and-security.md`](references/correlation-and-security.md)

4. **Claims carry an evidence level.** `source-confirmed`, `runtime-evidence`,
   `inference` or `not-verified`. A profile or a plan is never evidence of current
   runtime state. → [`references/rollout-and-evidence.md`](references/rollout-and-evidence.md)

5. **Rollback is planned per layer** — application, scrape, dashboard, rule —
   before rollout, because those layers are usually owned by different repositories.

## Decision sequence

```text
1. Confirm deployment_model=onprem from the environment profile.
2. Read the project profile: capabilities, ownership, logging/metrics/tracing state.
3. Instrument only declared, active boundaries.
4. Define success/failure/latency/in-flight semantics before writing code.
5. Choose label domains and prove each is finite.
6. Verify the scrape or log path produces real series before building a dashboard.
7. Build alerts only after a baseline exists and the alert platform is enabled.
8. Record evidence level and rollback for every claim.
```

Steps 6–8 are ordered deliberately: a dashboard built before runtime series exist
encodes guesses, and an alert threshold chosen before a baseline exists is noise.

## Out of scope by default

OpenTelemetry SDKs, Tempo and distributed tracing are **not** part of the initial
distribution. They are enabled only by an explicit environment/project decision
after a self-hosted collector pipeline is approved. If a project profile says
`tracing: disabled`, do not introduce tracing, an OTLP exporter or a second
telemetry agent — say what would be needed instead.

## Definition of done

A signal is complete only when all of these hold:

```text
metric or log field is documented with name, unit, type and label domain
expected series count is stated and bounded
the scrape or log path is verified against a running instance
a consumer exists: a dashboard panel or a rule
sensitive-data review passed
rollback is written down per layer
evidence level is recorded for every claim
```

"Alerting is done" additionally requires the rule engine, the receiver and a
synthetic delivery test — see
[`references/rollout-and-evidence.md`](references/rollout-and-evidence.md).

## Where to go next

| Situation | Skill |
|---|---|
| choosing which boundaries to instrument | `application-instrumentation` |
| shipping logs to Loki | `log-pipeline` |
| scraping metrics into VictoriaMetrics | `metrics-pipeline` |
| Kubernetes/Talos GitOps resources | `kubernetes-observability` |
| Docker, VM/systemd or bare metal | `vm-docker-observability` |
| dashboards, datasources, alert delivery | `grafana-operations` |
| reviewing an implementation or plan | `observability-review` |
| Scala/Play or Rust specifics | the matching adapter skill |

Process is owned by the Superpowers workflow skills — brainstorming, writing
plans, subagent-driven development, verification before completion. This contract
supplies domain constraints, not process.
