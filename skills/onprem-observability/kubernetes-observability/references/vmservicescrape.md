# VMServiceScrape

## Minimum shape

```yaml
apiVersion: operator.victoriametrics.com/v1beta1
kind: VMServiceScrape
spec:
  endpoints:
    - port: http
      path: /metrics
```

`port` is the **name** of the port in the Service, not its number. Using a number
here silently matches nothing.

Full form with selectors:

```yaml
apiVersion: operator.victoriametrics.com/v1beta1
kind: VMServiceScrape
metadata:
  name: <service>
  namespace: <namespace>
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: <service>
  namespaceSelector:
    matchNames:
      - <namespace>
  endpoints:
    - port: http
      path: /metrics
      interval: 30s
      scrapeTimeout: 10s
```

## The five ways this silently fails

1. **`ServiceMonitor` instead of `VMServiceScrape`.** Applies cleanly, reconciles
   nothing. No error anywhere.
2. **Port number instead of port name.** The endpoint matches no port; the target
   list stays empty.
3. **Selector does not match the Service labels.** Check the *Service* labels, not
   the Pod labels — the scrape selects Services.
4. **Wrong namespace.** Without `namespaceSelector`, the operator's configured
   default applies, which may not be the Service's namespace.
5. **Scrape timeout longer than the interval.** Rejected or truncated depending on
   version; either way the series arrive irregularly and rate queries go wrong.

Always confirm with the operator's target view that the target is `up` and has a
recent successful scrape. "The resource exists" is not evidence the scrape works.

## Interval and timeout

```text
interval      30s is a sane default; shorter multiplies storage and query cost
scrapeTimeout must be shorter than interval, with margin
```

A histogram-heavy endpoint can take seconds to encode. Measure the endpoint's real
response time before choosing the timeout, rather than discovering it as
intermittent gaps in the data.

## Relabeling

Keep relabeling minimal and reviewable. Two legitimate uses:

```yaml
      relabelConfigs:
        # Drop a noisy metric family at ingest rather than storing it.
        - action: drop
          sourceLabels: [__name__]
          regex: go_gc_duration_seconds.*
        # Normalize a label the application cannot easily change.
        - action: replace
          sourceLabels: [__meta_kubernetes_service_label_tier]
          targetLabel: tier
```

Do not use relabeling to manufacture identity labels — pod name, pod IP, container
id. Those change on every restart, so every rollout starts a new series for every
metric and breaks `rate()` across the deployment boundary.

## What must not become a label

```text
pod name, pod IP, node IP, container id
any generated or ephemeral identifier
request, correlation or trace ids
device, tenant or user identity
```

`namespace`, `service`, `app` and `tier` are bounded by the platform and are fine.

## Scaling and staleness

When a Deployment scales, each replica contributes its own series. That is
expected; aggregate in the query with `sum without (instance, pod)`. What is not
expected is series identity changing on every rollout — if it does, an identity
label crept in through relabeling.

## Verification

```bash
kubectl -n <ns> get vmservicescrape <name> -o yaml
kubectl -n <ns> get svc <name> -o jsonpath='{.spec.ports[*].name}'
```

Then, against VictoriaMetrics:

```promql
up{job=~".*<service>.*"}
count by (__name__) ({__name__=~"<namespace>_.*"})
```

Record the target state and the series count as `runtime-evidence` with the exact
query used. Without that, the claim is `inference`.
