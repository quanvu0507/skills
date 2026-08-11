# systemd services

## Unit state is a first-class signal

Without an orchestrator, nothing replaces a failed process unless systemd is told
to. Collect unit state and make it visible:

```text
unit active state       active | inactive | failed | activating
restart count           rising means crash-looping
last start timestamp    a fresh value nobody triggered means it restarted
time since last change  a unit flapping every minute reads as "active" at any instant
```

A dashboard showing "active" while the service restarts every 30 seconds is the
classic miss. Track restarts and start time, not only current state.

## Restart policy is a decision

```ini
[Service]
Restart=on-failure
RestartSec=5s
StartLimitBurst=5
StartLimitIntervalSec=60
```

`Restart=always` on a service with a fatal configuration error produces an infinite
loop that hides the error and consumes the host. `Restart=on-failure` with a start
limit lets it fail visibly after a few attempts, which is what you want an alert to
see.

State the chosen policy and **observe it working** once — a restart policy that was
never exercised is `not-verified`.

## Journal

Logs go to stdout and reach the journal. Configure a size cap:

```ini
SystemMaxUse=2G
SystemKeepFree=1G
```

An uncapped journal fills the disk, and a full disk stops everything on the host,
not just the service that filled it. This is the single most common bare-metal
observability incident.

Alloy reads the journal and forwards to Loki. Map bounded unit metadata to labels:

```text
keep:  unit name, host
drop:  PID, boot id, anything id-shaped
```

## Resource limits

```ini
[Service]
MemoryMax=2G
CPUQuota=200%
TasksMax=512
```

Limits turn "the host got slow" into "this unit hit its limit", which is diagnosable.
Without them, one service's leak is an unattributable host-wide problem.

Export the limit alongside the usage so a dashboard can show headroom, not just an
absolute number nobody can interpret.

## Timers

For `systemd.timer` units, the job outcome semantics from the application
instrumentation skill apply: one terminal outcome per run, `skipped_lock`
distinguished from failure, and staleness alerting on time since last success. Also
collect the timer's own last-trigger time — a timer that stopped firing looks
identical to a job with no work to do.

## Ordering and dependencies

`After=` is not `Requires=`. A unit that starts after the database unit but does not
require it will start happily when the database is absent and fail in a way that
looks like an application bug. Make the dependency explicit and observable.

## Checklist

```text
unit state, restart count and last start time are collected
restart policy is stated and was observed working
journal size cap is configured
disk usage on the journal path is monitored with an alert
resource limits are set and exported alongside usage
timer units expose last trigger and last success
unit dependencies are explicit
