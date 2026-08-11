# Host, process and container resources

## Three layers, all needed

```text
host       CPU, memory, disk, network, load, file descriptors
container  per-container CPU, memory, restarts, OOM kills
process    per-process CPU, RSS, threads, open files, GC where applicable
```

Without an orchestrator nothing else is watching the host, so host metrics are part
of the service's observability rather than someone else's platform concern.

Collect all three. A slow service with a healthy process and a saturated host is a
different incident from one with a leaking process on an idle host, and only the
combination distinguishes them.

## Disk is the one that stops the machine

On a host, a full disk is not a degraded service — it stops everything, including
the agents that would have told you. Monitor both space and inodes, on every path
that grows:

```text
log directory
journal
metrics buffer / write-ahead log
container storage
application data volumes
```

Alert on **projected** exhaustion, not on a fixed percentage. A disk at 70% that
gains 5% a day is more urgent than one that has been at 85% for a year.

```promql
predict_linear(node_filesystem_avail_bytes{mountpoint="/var"}[6h], 24*3600) < 0
```

Inode exhaustion presents as "no space left on device" while the space graph looks
fine — many small files, typically logs or cache. Monitor it separately.

## Memory

Track RSS against the configured limit, not as an absolute number. Absolute memory
means nothing without the limit next to it, and the interesting event is
approaching the limit.

OOM kills must be counted explicitly. An OOM-killed and restarted process is
invisible in "is it running" — the service is up, and it silently lost whatever it
was doing.

## File descriptors

Exhaustion presents as connection failures that look like a network problem. Track
open descriptors against the limit; a slow leak is obvious in the ratio and
invisible in the absolute count.

## Network

Interface throughput, errors and drops. On a bare-metal host these are often the
only evidence of a physical problem, and they are the first thing to check when
"the application is slow" has no application-side explanation.

## Time

Clock skew corrupts every timestamp-based query and makes rate calculations produce
nonsense. Monitor NTP synchronization; on hosts that reboot rarely, drift builds up
unnoticed for months.

## Labels

```text
keep:  host, unit or container name, mountpoint, device, interface
never: PID, boot id, container id, ephemeral hostname
```

PID and boot id change on every restart, which is churn on every metric they touch.

## Baseline before alerting

Every threshold here needs a baseline. A host that normally runs at 80% CPU is fine;
one that normally runs at 20% and reaches 80% is an incident. Record the observed
range before choosing a threshold, or the first busy night pages someone for normal
behaviour.

## Checklist

```text
host, container and process metrics all collected
disk space and inodes monitored on every growing path
disk alerts use projected exhaustion, not a fixed percentage
memory tracked against its limit; OOM kills counted
file descriptors tracked against the limit
network errors and drops collected
clock synchronization monitored
no ephemeral identifier appears in a label
thresholds derived from a recorded baseline
