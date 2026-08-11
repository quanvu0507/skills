# Desktop and local applications

## The environment decides, not the language

A `desktop-local` environment profile declares:

```yaml
features:
  vmservicescrape: false
  vmrule: false
  central_scrape: false
network:
  telemetry_egress: internal-only
```

`central_scrape: false` is the important one. It means **no background exporter and
no telemetry leaving the machine**. A desktop application is installed on a
workstation the platform does not own and cannot secure the same way.

Do not, unless the project profile explicitly enables it and the decision is
recorded:

```text
open a metrics listener in the background
push metrics or logs to any central endpoint
start a collector agent alongside the application
enable an OTLP exporter
```

An unrequested listening socket on a user's machine is a security finding, not an
implementation detail. Telemetry leaving a workstation is a data-handling decision
that belongs to whoever owns that data classification.

## What to build instead

**Local rotating log file.** Bounded total size, bounded per-file size, JSON Lines
in the same format the servers use. Same schema means the same tooling works if a
user ever sends a log bundle.

```text
one directory under the platform's standard application-data path
size-capped rotation — a log that fills a user's disk is a support incident
the same field names and event names as the server side
no credentials, tokens, payloads or document contents
```

**In-process counters, surfaced on demand.** Keep the same counters a server would
keep, and expose them through a diagnostics view the user opens deliberately:

```text
operation counts by outcome
durations for the slow paths
error counts by finite error_kind
version, build id and configuration summary
```

This gives support engineers the same numbers without a network listener.

**Explicit, user-initiated diagnostic bundle.** When a user reports a problem, a
bundle they choose to export is the correct mechanism:

```text
the user takes an explicit action to create it
the contents are listed before export
redaction is applied and stated
the file stays local until the user sends it
```

## Crash and startup signals

Record locally: last clean shutdown, startup duration, config load failures,
update-check outcome. These answer most desktop support questions and require no
network at all.

## If central telemetry is genuinely required

Then the project profile must say so, and the decision needs:

```text
a written data classification for what is collected
consent or a documented internal-device policy
an internal-only destination from the environment profile
an off switch that actually stops collection
retention and ownership for the resulting data
```

Absent all five, the answer is local diagnostics.

## Tests

```text
a test asserts no listening socket is opened when central_scrape is false
a test asserts log rotation enforces the total size cap
a test asserts the diagnostics view reads in-process state without I/O on the UI thread
a test asserts no credential or document content reaches the local log
a test asserts a diagnostic bundle is produced only on explicit request
```
