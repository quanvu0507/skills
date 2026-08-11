---
name: kubernetes-observability
license: Apache-2.0
compatibility: "Kubernetes, Talos, VictoriaMetrics Operator (VMServiceScrape/VMRule), Grafana OSS, Loki OSS, Alloy, GitOps; no Grafana Cloud dependency"
description: "GitOps observability for on-premises Kubernetes backed by the VictoriaMetrics Operator. Covers VMServiceScrape targeting, VMRule rollout gates, dashboard ownership between source JSON and generated ConfigMaps, and gateway protection of management paths. Use when adding or reviewing scrape configuration, alert rules, dashboards or ingress policy for a service on Kubernetes or Talos, and whenever ServiceMonitor or PrometheusRule is proposed in a VictoriaMetrics cluster."
---

# Kubernetes observability (VictoriaMetrics GitOps)

Applies only when the environment profile declares `environment: kubernetes-talos`
with `features.vmservicescrape: true`. For Docker, VM/systemd or bare metal use
`vm-docker-observability` instead — generating Kubernetes resources there produces
YAML that nothing reconciles.

Read [`observability-contract`](../observability-contract/SKILL.md) first.

## Use the VictoriaMetrics resources

| Wrong | Right |
|---|---|
| `ServiceMonitor` | `VMServiceScrape` |
| `PodMonitor` | `VMPodScrape` |
| `PrometheusRule` | `VMRule` |
| `serviceMonitor.enabled: true` in Helm values | the operator's own values key |

`ServiceMonitor` and `PrometheusRule` are Prometheus Operator CRDs. In a
VictoriaMetrics cluster they apply cleanly, pass review, and are then **ignored**.
Nothing errors. The scrape simply never happens and the alert never evaluates, and
the gap is usually discovered during the incident the alert was written for.

If the cluster runs the operator's Prometheus-CRD conversion, say so explicitly
with evidence — do not assume it.

## What GitOps owns

The GitOps repository, not the application repository, owns:

```text
image tag or digest (immutable)
Helm values and templates
probe paths and timings
VMServiceScrape
Gateway / ingress policy
dashboard source and its generated ConfigMap
VMRule and alert routing
runbook and rollback
```

An observability change therefore usually spans two repositories. State which
change lands where, and in which order, before starting.

## Rollout order

```text
1. application exposes /metrics on its existing port
2. VMServiceScrape added; target confirmed up
3. expected series confirmed present in VictoriaMetrics
4. dashboard built against those confirmed series
5. baseline observed over a representative period
6. VMRule written against the baseline
7. alert delivery tested end to end
```

Never build step 4 before step 3 is evidenced. A dashboard authored against
imagined metric names renders empty and looks like a broken deployment.

## References

| Topic | Reference |
|---|---|
| scrape targeting and common failures | [`vmservicescrape.md`](references/vmservicescrape.md) |
| alert rollout gates | [`vmrule-rollout.md`](references/vmrule-rollout.md) |
| dashboard ownership and validation | [`dashboards.md`](references/dashboards.md) |
| protecting `/metrics` and management routes | [`gateway-management-paths.md`](references/gateway-management-paths.md) |

## Assets

- [`assets/vmservicescrape.template.yaml`](assets/vmservicescrape.template.yaml)
- [`assets/dashboard-review-checklist.md`](assets/dashboard-review-checklist.md)

## Never do

```text
expose /metrics or any management path through the public gateway
create a second Service or port purely for metrics
put a pod name, pod IP or container id into a metric label
write a dashboard before runtime series exist
declare alerting complete while vmalert or Alertmanager is disabled
use a mutable image tag such as latest for a workload under observation
```

## Verification

```text
kubectl get vmservicescrape -n <ns> shows the resource
the VictoriaMetrics targets view shows the target as up with a recent scrape
a query for each expected metric returns series, with the expected label set
a negative probe from outside the cluster confirms /metrics is refused
the dashboard source and the generated ConfigMap are in the same commit
vmalert shows the rule loaded and evaluating
a synthetic alert reached the receiver and a human confirmed it
```
