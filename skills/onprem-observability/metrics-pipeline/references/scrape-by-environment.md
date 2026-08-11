# Scrape configuration by environment

Read `features.central_scrape` and `environment` from the environment profile
first. The mechanism follows the environment, never the language.

## kubernetes-talos

Use `VMServiceScrape` (or `VMPodScrape` when there is no Service). The
VictoriaMetrics Operator reconciles them; the Prometheus Operator CRDs it does not.

```yaml
apiVersion: operator.victoriametrics.com/v1beta1
kind: VMServiceScrape
spec:
  endpoints:
    - port: http          # the port NAME in the Service, not its number
      path: /metrics
```

The full pattern, the five ways this silently fails, and verification commands are
in the `kubernetes-observability` skill.

## vm-systemd and bare-metal

`vmagent` with static or file-based discovery. File discovery is preferable
whenever targets change without a redeploy: `vmagent` re-reads the files, so no
restart is needed.

```yaml
scrape_configs:
  - job_name: example-service
    scrape_interval: 30s
    scrape_timeout: 10s
    file_sd_configs:
      - files:
          - /etc/vmagent/targets/example-service.json
```

```json
[
  {
    "targets": ["127.0.0.1:9000"],
    "labels": { "job": "example-service", "tier": "backend" }
  }
]
```

Bind the exporter to the internal interface the environment profile specifies.
Binding to all interfaces on a host with a public address publishes the metrics.

Configuration management owns these files. A target added by hand on one host is a
target that disappears at the next rebuild.

## docker-dokploy

Docker discovery, or explicit targets when discovery is not available. With Docker
discovery, relabel container metadata into bounded labels:

```text
keep:  container name, compose service, image name (without a mutable tag)
drop:  container id, ephemeral hostnames, anything id-shaped
```

The container id changes on every restart. Relabeling it into a label starts a new
series for every metric on every restart and breaks `rate()` across the boundary.

Reach the exporter over the internal Docker network, not through the published
port, so metrics do not depend on the host's port mapping.

## desktop-local

`central_scrape: false` means **no central scrape and no background exporter**.
Local diagnostics only, surfaced on demand. Enabling collection requires an
explicit project-profile decision with a data classification, a consent or device
policy, an internal-only destination, an off switch and a retention owner.

## Common failures across all environments

| Symptom | Usual cause |
|---|---|
| target missing entirely | selector or discovery matches nothing |
| target down | wrong port, wrong path, or the app binds elsewhere |
| intermittent gaps | scrape timeout below the endpoint's real response time |
| series identity changes on restart | an ephemeral id was relabeled into a label |
| series appear then stop | the exporter blocks on I/O under load |

Confirm with the target list, not with the configuration: a resource existing is
not evidence that a scrape works.

## Verification

```promql
up{job="example-service"}                        # 1 means scraped successfully
scrape_duration_seconds{job="example-service"}   # must stay below the timeout
scrape_samples_scraped{job="example-service"}    # sudden growth means new labels
```

Record the query and its output as runtime-evidence. `scrape_samples_scraped` is
the early warning for a cardinality mistake — it rises before anyone notices a slow
query.
