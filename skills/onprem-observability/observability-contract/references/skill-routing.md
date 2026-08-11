# Skill routing

## Allowed upstream skills

This contract routes to these upstream Grafana skills, and only for their OSS
content:

```text
skills/grafana-core/grafana-oss
skills/grafana-core/dashboarding
skills/grafana-core/promql
skills/grafana-core/alloy
skills/grafana-lgtm/loki
skills/grafana-lgtm/prometheus
```

Several of them document a Grafana Cloud path alongside the OSS path. Read the OSS
sections; never emit the Cloud ones. The private on-prem runtime contract has
higher precedence than any Cloud branch found in an upstream skill.

## Refused routes

Never load or follow guidance from `skills/grafana-cloud/**`, and never produce a
configuration that reaches a SaaS endpoint:

```text
grafana.net (any subdomain)
api.k6.io, cloudlogs.k6.io
glc_ tokens
MetricsPublisher / LogsPublisher / TracesPublisher access-policy roles
stack IDs, tenant IDs, cloud publisher credentials
```

## Cloud request mapping

When a request names a Cloud feature, answer with the on-prem equivalent and say
why:

| Requested | On-prem answer |
|---|---|
| Grafana Cloud Metrics | VictoriaMetrics |
| Grafana Cloud Logs | Loki OSS |
| Grafana Cloud OTLP gateway | internal Alloy or collector endpoint |
| Adaptive Metrics | source-side label redesign, recording rules, retention policy |
| DPM Finder / cloud cost management | series-count queries against VictoriaMetrics |
| Fleet Management | the project's own configuration management |
| Cloud Integrations | Alloy components configured in the environment profile |
| Grafana Cloud k6 | k6 OSS executed inside the controlled network |
| Assistant MCP | not available; use the repository's own skills |

## On-prem skill selection

Selection is resolved from the environment profile plus declared capabilities plus
a language adapter — never from a repository name.

| Environment | Runtime skill | `VMServiceScrape` | `VMRule` | central scrape |
|---|---|---:|---:|---:|
| `kubernetes-talos` | `kubernetes-observability` | yes | yes | yes |
| `docker-dokploy` | `vm-docker-observability` | no | no | yes |
| `vm-systemd` | `vm-docker-observability` | no | no | yes |
| `bare-metal` | `vm-docker-observability` | no | no | yes |
| `desktop-local` | none by default | no | no | no |

| Capability | Skill |
|---|---|
| any active boundary | `application-instrumentation` |
| `observability.logging: required` | `log-pipeline` |
| `observability.metrics: required` | `metrics-pipeline` |
| owns or consumes Grafana dashboards, alerts or runbooks | `grafana-operations` |
| reviewing work | `observability-review` |

Generating `ServiceMonitor`, `PrometheusRule` or `serviceMonitor.enabled` in a
VictoriaMetrics profile is always wrong — those are Prometheus Operator resources
and the VictoriaMetrics Operator ignores them, so the scrape silently never
happens.

## Process ownership

Superpowers owns the process: brainstorming and design, writing plans,
subagent-driven development or plan execution, verification before completion.
These observability skills supply domain constraints and evidence requirements.
They do not restate or replace process instructions.
