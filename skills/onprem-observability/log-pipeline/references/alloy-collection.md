# Alloy collection

## Shape

Alloy discovers log sources, relabels metadata into bounded labels, and writes to
Loki. Keep the pipeline short: discovery, relabel, write. Every extra stage is
another place a line can be dropped without anyone noticing.

Pin the Alloy version in the deployment and record it. Component names and
arguments have changed across versions, and a floating version turns an upgrade
into a silent collection outage.

## Discovery by environment

| Environment | Discovery | Source |
|---|---|---|
| `kubernetes-talos` | Kubernetes pod discovery | container stdout |
| `docker-dokploy` | Docker discovery | container stdout |
| `vm-systemd` | journal | unit output |
| `bare-metal` | file match | log files |

Prefer runtime metadata over parsing paths. A filename pattern breaks the moment a
path convention changes; discovery metadata does not.

## Relabeling

Relabeling exists to map runtime metadata onto the bounded label set. It is also
the easiest place to introduce an unbounded label by accident.

```text
keep:      namespace, app, container, pod, node, job
drop:      annotations, long free-form labels, anything id-shaped
never add: values parsed out of the log line body
```

State the resulting label set explicitly and count its cardinality.

## Do not fix logging in the collector

A malformed or unsafe log line is fixed in the application. Using Alloy to strip a
secret is not redaction — the value was already written to the node's disk and may
already be in a backup. The collector stage removes it from Loki and from nowhere
else.

Legitimate collector-side work: multiline joining for a runtime that splits lines,
dropping a known-noisy source entirely, and adding bounded metadata.

## Backpressure and drops

Alloy buffers when Loki is unavailable, then drops. Silent drops are the failure
mode that makes people distrust the whole pipeline, so scrape Alloy's own metrics
and put them on a dashboard:

```text
write requests by status
retries
dropped entries or bytes
queue or buffer depth
last successful write timestamp
```

Alert on sustained drops and on write failures. Without this, "the logs are
missing" is unanswerable, and the usual conclusion is that logging is unreliable.

Alloy's own logs matter too: collect them, at a level that does not produce a loop.

## Rate limits

Loki enforces per-tenant ingestion and stream limits. When they are hit, lines are
rejected at write and Alloy's error rate rises. Know the configured limits, and
treat a rejection as a capacity or label-design problem, not as a reason to raise
the limit reflexively.

## Multiline

A stack trace split across lines becomes several unrelated log entries and the
error is unreadable. If the application cannot emit a single-line JSON event with a
bounded embedded trace — which is the preferred fix — join it in Alloy with an
explicit anchor pattern, and bound the number of joined lines.

## Verification

```text
Alloy is running and its own metrics are being scraped
a written line appears in a LogQL query within the expected delay
the label set on the arriving stream matches the design
drop and retry counters are zero in steady state, and are dashboarded
stopping Loki produces visible retries, not silence
