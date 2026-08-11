---
name: vm-docker-observability
license: Apache-2.0
compatibility: "Docker, Dokploy, systemd, bare metal, vmagent, Grafana Alloy, Loki OSS, Grafana OSS, VictoriaMetrics; no Kubernetes and no Grafana Cloud dependency"
description: "Observability for services that do not run on Kubernetes — Docker or Dokploy containers, systemd units and bare-metal hosts. Covers unit and container health, host, process and container resource metrics, vmagent scrape configuration with static or file discovery, Alloy on the host, internal reverse-proxy management paths, and restart, persistence and runbook ownership. Use when instrumenting or reviewing a service deployed with Docker Compose, Dokploy, systemd or directly on a host."
---

# VM, Docker and bare-metal observability

Applies to environments `docker-dokploy`, `vm-systemd` and `bare-metal`. For
Kubernetes use `kubernetes-observability` instead — and never generate
`VMServiceScrape`, `VMRule` or any other Kubernetes resource here, because nothing
would reconcile them.

Read [`observability-contract`](../observability-contract/SKILL.md) first.

## What is different without an orchestrator

| Kubernetes gives you | Here you must arrange it |
|---|---|
| service discovery | static or file-based discovery, owned by config management |
| restart policy and health-driven replacement | systemd or Docker restart policy, explicitly configured |
| bounded metadata labels | relabeling from unit or container metadata, hand-checked |
| an ingress layer with policy | an internal reverse proxy you configure |
| ephemeral storage assumptions | disks that fill up and stay full |

The last row is the one that causes incidents: on a host, a log file or a metrics
buffer that grows without bound eventually stops the machine, not just the process.

## Coverage

```text
systemd service health
Docker container discovery
host/process/container resource metrics
internal reverse proxy management paths
Alloy on host
vmagent scrape configuration
restart/persistence/runbook ownership
```

| Topic | Reference |
|---|---|
| systemd units, restart policy, journal | [`systemd-services.md`](references/systemd-services.md) |
| Docker and Dokploy containers | [`docker-and-dokploy.md`](references/docker-and-dokploy.md) |
| host, process and container resources | [`host-and-resource-metrics.md`](references/host-and-resource-metrics.md) |
| vmagent, Alloy, reverse proxy, ownership | [`agents-and-ownership.md`](references/agents-and-ownership.md) |

## Management paths

The exporter binds to the internal interface named by the environment profile.
Never bind a management listener to all interfaces on a host that has a public
address — that publishes metric names, label values, route templates and dependency
names to anyone who asks.

If an internal reverse proxy fronts the service, add an explicit deny for
`/metrics`, `/health`, `/ready` and any debug path, and verify with a negative
probe from outside the boundary before rollout. Record the probe output.

## Never

```text
generate VMServiceScrape, VMRule, ServiceMonitor or PrometheusRule
assume a container is restarted automatically without checking the restart policy
let a log file or a metrics buffer grow unbounded on a host disk
relabel a container id or an ephemeral hostname into a label
declare a target monitored because the exporter responds locally
```

## Done

```text
the target appears in vmagent and up == 1 with recent scrapes
host, process and container resource metrics are collected
disk usage on the log and buffer paths is monitored with an alert
the restart policy is stated and was observed working
management paths are refused from outside; probe output recorded
a runbook exists and names the owner
rollback for the scrape and agent configuration is documented
```
