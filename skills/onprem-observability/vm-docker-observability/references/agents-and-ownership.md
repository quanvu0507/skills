# Agents, reverse proxy and ownership

## vmagent

`vmagent` scrapes targets and writes to VictoriaMetrics. Two things matter beyond
the scrape configuration itself.

**Discovery source.** Prefer file-based discovery over static targets whenever
targets change without a redeploy — vmagent re-reads the files, so no restart is
needed and no window of missed scrapes appears.

```yaml
scrape_configs:
  - job_name: example-service
    scrape_interval: 30s
    scrape_timeout: 10s
    file_sd_configs:
      - files:
          - /etc/vmagent/targets/*.json
```

Configuration management owns those files. A target added by hand on one host
disappears at the next rebuild, and nobody notices until the metric is needed.

**Its own buffer.** vmagent buffers on disk when VictoriaMetrics is unavailable,
then drops. Monitor the buffer path's disk usage and vmagent's own metrics —
remote-write failures, retries, dropped samples, buffer size. Silent drops are what
makes people stop trusting the metrics, and the buffer filling the disk takes the
host with it.

## Alloy on the host

Alloy runs as a unit or a container, reads the journal or log files, and writes to
Loki. Same rules:

```text
pin the version and record it — component arguments change across versions
scrape Alloy's own metrics: write status, retries, dropped entries, queue depth
cap its buffer and monitor that path's disk usage
collect Alloy's own logs, at a level that cannot feed itself
```

An agent that is running is not an agent that is delivering. Verify with a canary
line end to end, not with the process being up.

## Agents are single points of failure

On Kubernetes an agent pod is rescheduled. Here, if the agent stops, telemetry
stops silently and everything looks healthy because nothing is reporting otherwise.

```text
set a restart policy on the agent unit or container, and observe it working
alert on the absence of data, not only on bad data
run a periodic canary and alert when it stops arriving
```

Alerting on absence is the only thing that catches a dead agent:

```promql
time() - vmagent_last_successful_write_timestamp_seconds > 600
```

## Internal reverse proxy

Where a reverse proxy fronts the service:

```text
enumerate the management paths: /metrics, /health, /ready, any debug path
add an explicit deny for each — do not rely on route ordering
verify with a negative probe from outside the boundary before rollout
record the probe output; re-run it after any proxy change
```

A proxy forwarding `/` forwards `/metrics` too. This is the check most likely to
regress silently, because nothing else fails when it does.

Collect the proxy's own metrics: request rate, status classes, upstream errors and
connection counts. It is the first place to look when the application says it is
healthy and users say it is not.

## Ownership

Write these down; without an orchestrator they are genuinely ambiguous:

| Layer | Question |
|---|---|
| application code | who changes the instrumentation? |
| deployment | who owns the unit file or compose file? |
| scrape config | who owns the vmagent target files? |
| agent config | who owns the Alloy configuration? |
| host | who owns disk, upgrades and reboots? |
| dashboards and rules | who owns them, and where do they live? |
| runbook | who is called, and what do they do first? |

Missing data is usually reported to whoever owns the application, and the cause is
usually a layer they do not own.

## Runbook

Minimum contents:

```text
what this service does and what breaks when it stops
how to check whether it is running, and where the logs are
how to restart it safely, and what the restart affects
what to check when metrics or logs stop arriving
how to roll back the application, the scrape config and the agent config
who to escalate to, and when
```

A runbook that only says how to restart the service is not enough — most of these
incidents are agent, disk or proxy problems, not application problems.

## Rollback

```text
application:  previous immutable image tag or package version
scrape:       revert the target file; confirm the target returns
agent:        revert the Alloy or vmagent configuration; re-run the canary
proxy:        revert the configuration; re-run the negative probe
```

Each layer rolls back independently, and each needs its own verification.
