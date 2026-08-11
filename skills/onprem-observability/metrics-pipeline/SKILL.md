---
name: metrics-pipeline
license: Apache-2.0
compatibility: "VictoriaMetrics (vmagent, vmsingle, vmcluster), VictoriaMetrics Operator, Grafana OSS, Kubernetes, Docker, VM/systemd, bare metal; no Grafana Cloud dependency"
description: "Get Prometheus-compatible application metrics into VictoriaMetrics and make them usable in Grafana OSS. Covers scrape configuration per environment (VMServiceScrape on Kubernetes, vmagent static or file discovery elsewhere), metric inventory with unit, type and label domains, expected series count, scrape verification and a required consumer before a metric is called done. Use when configuring or reviewing metric collection, choosing a scrape mechanism, or debugging missing series and cardinality growth."
---

# Metrics pipeline

Applies when the project profile declares `observability.metrics: required`. Read
[`observability-contract`](../observability-contract/SKILL.md) first.

## Topology

```text
application exporter
  -> Prometheus-compatible scrape
  -> VictoriaMetrics
  -> Grafana OSS
```

The application exposes a scrape endpoint; it never pushes. Pull keeps the
application free of backend credentials, makes target health observable through
`up`, and lets the scrape be reconfigured without redeploying the service.

## Scrape mechanism by environment

```text
kubernetes-talos -> VMServiceScrape
vm-systemd       -> vmagent static/file discovery
bare-metal       -> vmagent static/file discovery
docker-dokploy   -> Docker/host discovery or explicit scrape targets
desktop-local    -> no central scrape unless project profile explicitly enables it
```

Read `features.central_scrape` from the environment profile before designing
anything. On `desktop-local` it is `false`, and an exporter listening in the
background on a user's workstation is a security decision, not an implementation
detail.

→ [`references/scrape-by-environment.md`](references/scrape-by-environment.md)

## Never in a VictoriaMetrics profile

```text
ServiceMonitor
PodMonitor
PrometheusRule
serviceMonitor.enabled
```

These are Prometheus Operator CRDs. In a VictoriaMetrics cluster they apply
cleanly, reconcile nothing, and produce no error — the scrape silently never
happens, usually discovered during the incident the metric was added for.

## A metric is not done until

```text
metric inventory entry exists: name, unit, type, help
every label domain is enumerated and its size stated
expected series count is computed and within the stated budget
the scrape is verified: target up, recent successful scrape
the expected series are confirmed present by query
a consumer exists: a dashboard panel or a rule
```

The consumer requirement is what stops metric sprawl. A metric nobody queries costs
storage and cardinality forever and answers no question.

→ [`references/metric-inventory.md`](references/metric-inventory.md)

## Cardinality is a shared resource

VictoriaMetrics is usually shared. One service adding an unbounded label degrades
queries for every other team. Compute the series count before adding a label — the
product of every label domain size — and if a domain cannot be counted, it is not
finite and must not be a label.

→ [`references/cardinality-and-verification.md`](references/cardinality-and-verification.md)

## Scrape hygiene

```text
interval 30s unless there is a stated reason
scrapeTimeout comfortably below the interval
the endpoint performs no I/O and cannot block
relabeling introduces no identity label (pod name, pod IP, container id)
metric names are stable — renaming breaks every dashboard and rule silently
```

## Recording rules

Use a recording rule when a query is expensive and used in several places, or when
a high-cardinality aggregate is queried repeatedly. A recording rule is not a fix
for a cardinality mistake: the underlying series are still stored. Fix the labels
at the source.

## Done

```text
inventory complete, series count within budget
scrape target up with recent successful scrapes
every declared metric returns data by query
every metric has a dashboard panel or a rule using it
alerting readiness stated separately — see the runtime skill
rollback documented for the scrape configuration
```
