---
name: log-pipeline
license: Apache-2.0
compatibility: "Grafana Alloy, Loki OSS, Grafana OSS, Kubernetes, Docker, VM/systemd, bare metal; no Grafana Cloud dependency"
description: "Ship application logs to Loki OSS through Alloy, from stdout or a host file, keeping index labels bounded and high-cardinality values as query-time fields. Covers JSON Lines validation, secret and PII redaction, Alloy write/retry/drop metrics, canary read-write verification, retention and ownership. Use when configuring or reviewing log collection, choosing Loki labels, debugging missing or dropped logs, or setting log retention for an on-premises project."
---

# Log pipeline

Applies when the project profile declares `observability.logging: required`. Read
[`observability-contract`](../observability-contract/SKILL.md) first.

## Topology

```text
application stdout or host file
  -> container/host runtime
  -> Alloy
  -> Loki OSS
  -> Grafana OSS
```

The application writes to stdout (or, on a host, to a file with rotation). It never
opens a connection to Loki. That keeps the application free of backend credentials,
survives Loki being down without blocking the application, and means a
configuration change to collection needs no redeploy of the service.

**The destination must be inside the network declared by the environment profile.**
Reject any configuration that writes logs outside it — that is a data-egress
decision, not a collection detail.

## The label rule

This is the decision that determines whether Loki stays usable:

| Kind | Becomes | Examples |
|---|---|---|
| bounded infrastructure metadata | an **index label** | `namespace`, `app`, `pod`, `container`, `host`, `job`, `level` |
| everything with unbounded cardinality | a **parsed field** at query time | `request_id`, `correlation_id`, `device_id`, `route`, `user_id` |

Every distinct combination of index labels creates a stream. Adding one
high-cardinality label multiplies stream count by that label's cardinality, which
degrades ingestion and query for **every** tenant on the instance — not just the
service that added it.

High-cardinality lookup is what query-time parsing is for, and it costs nothing at
write time:

```logql
{namespace="apps", app="example-service"} | json | correlation_id="01J..."
```

If a structured metadata mechanism is available in the deployed Loki version, it is
the middle option for values queried often but too large to index. Confirm the
version supports it before relying on it.

## Required checks

```text
JSON Lines validity
secret/PII redaction
bounded index labels
high-cardinality values as structured metadata or parsed fields
Alloy write/retry/drop metrics
canary log read/write verification
retention and ownership
```

Each is covered in
[`references/alloy-collection.md`](references/alloy-collection.md),
[`references/loki-labels.md`](references/loki-labels.md) and
[`references/verification-and-retention.md`](references/verification-and-retention.md).

## Collection by environment

| Environment | Source | Discovery |
|---|---|---|
| `kubernetes-talos` | container stdout | Kubernetes pod discovery |
| `docker-dokploy` | container stdout | Docker discovery |
| `vm-systemd` | journal or file | journal or file match |
| `bare-metal` | file | file match |
| `desktop-local` | local rotating file | none — no central collection |

## Never

```text
send logs to any destination outside the declared internal network
put a request id, correlation id, device id, user id or route into a Loki label
log a payload, credential, cookie, signed URL or decoded token claim
rely on a downstream pipeline stage to remove a secret — it already hit disk
declare the pipeline working because Alloy is running
```

That last one is the most common false completion: Alloy running proves a process
exists, not that a line travelled end to end.

## Done

```text
a real log line was written, collected and returned by a LogQL query
the line parses as valid JSON with the expected field names
index labels are enumerated, each bounded, and the stream count is stated
a sensitive-value test shows the redaction marker, not the value
Alloy write, retry and drop metrics are scraped and have a dashboard
retention is configured and an owner is named
```
