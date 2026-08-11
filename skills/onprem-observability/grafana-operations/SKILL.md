---
name: grafana-operations
license: Apache-2.0
compatibility: "Grafana OSS, VictoriaMetrics, Loki OSS, vmalert, Alertmanager; no Grafana Cloud dependency"
description: "Operate Grafana OSS on-premises: provision datasources, keep dashboards in version control, validate panels against real series, navigate from metrics to logs with a preserved time range, own alert rules and receivers, test alert delivery, and plan backup, restore, runbooks and rollback. Use when a project owns or consumes Grafana dashboards, alert rules or runbooks, when dashboards have drifted from source, or when deciding whether alerting is genuinely operational."
---

# Grafana operations

Applies when the project owns or consumes Grafana OSS dashboards, alerts or
runbooks. Read [`observability-contract`](../observability-contract/SKILL.md) first.

## Coverage

```text
datasource provisioning
source-controlled dashboards
dashboard validation
time-bounded metrics-to-logs navigation
alert rule ownership
receiver delivery test
backup/restore
runbook and rollback
```

| Topic | Reference |
|---|---|
| datasources and provisioning | [`datasources-and-provisioning.md`](references/datasources-and-provisioning.md) |
| dashboards as source, validation, logs links | [`dashboards-as-code.md`](references/dashboards-as-code.md) |
| rules, receivers, delivery testing | [`alerting-operations.md`](references/alerting-operations.md) |
| backup, restore, runbooks, rollback | [`backup-and-runbooks.md`](references/backup-and-runbooks.md) |

## Two rules that prevent most of the pain

**Everything is provisioned from version control.** Datasources, dashboards, alert
rules and contact points all come from files. A change made in the UI is discarded
by the next reconcile, and the person who made it believes it shipped — that
mismatch is discovered during an incident.

**Alerting is not operational until a synthetic alert reaches a human.** A merged
rule file is one step of six:

```text
baseline data
rule engine enabled and evaluating
Alertmanager enabled
receiver configured with a named owner
rule tested against sample data
synthetic delivery observed by a human
```

Describing alerting as "configured" before the last line is true produces a system
that looks monitored and is not.

## Datasource choice

```text
metrics -> VictoriaMetrics via the Prometheus datasource type
logs    -> Loki OSS
```

Both point at internal endpoints supplied by the environment profile. A datasource
URL is never hardcoded in a skill, a dashboard or a document.

## Never

```text
edit a provisioned dashboard, datasource or rule in the UI
hardcode an internal endpoint or a credential in a dashboard or a document
point a datasource at a Grafana Cloud or other SaaS endpoint
declare alerting complete without receiver delivery evidence
ship a dashboard whose panels were never run against real series
let a template variable enumerate a high-cardinality label
```

## Done

```text
datasources provisioned from version control and reachable
dashboards in Git; source and generated artifact updated together
every panel query was run and returned data
logs navigation preserves the time range and uses bounded selectors
rules provisioned; the engine is evaluating them
each alert has a receiver with a named owner and a runbook link
a synthetic alert was delivered and confirmed by a human
backup and restore are configured and restore was actually tested
rollback is documented per layer
```
