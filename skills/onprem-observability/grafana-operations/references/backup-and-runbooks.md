# Backup, restore and runbooks

## What actually needs backing up

With everything provisioned from Git, most of Grafana is reproducible from a
repository. The state that is **not** in Git is what needs a backup:

```text
users, teams and permissions created in the UI
API tokens and service accounts
annotations (incident history, deploy markers)
alert state, silences and their history
dashboards created ad hoc that were never ported to source
preferences and org settings
```

The last item is the honest one: ad hoc dashboards accumulate, and a restore that
loses them loses real work. Either port them to source or accept that they are
disposable — decide, and say which.

## Restore must be tested

A backup that has never been restored is a hypothesis. Test it on a non-production
instance and record:

```text
how long the restore took
what was missing afterwards
whether provisioned resources reconciled correctly on top of it
whether datasource UIDs still matched what dashboards referenced
```

That last one is the usual failure: dashboards restore fine and render empty
because the datasource UID changed.

## Rebuild from source

The stronger position is that a Grafana instance can be rebuilt from version
control:

```text
provisioning files -> datasources, dashboards, contact points, rules
a documented bootstrap procedure
a short backup only for genuinely UI-created state
```

Time the rebuild once and record it. "We can rebuild from Git" is an assumption
until someone has done it.

## Runbook contents

For each alert, and for the observability stack itself:

```text
what fired, and what it means in one sentence
what the user impact is, and whether it is user-visible at all
first three things to check, with the exact queries or commands
how to confirm it is resolved
how to escalate, and to whom
what NOT to do — the tempting action that makes it worse
```

The last line saves the most time. "Do not restart the collector; it will lose the
buffer" is the kind of knowledge that otherwise exists only in one person's head.

## Runbooks for the observability stack itself

These are the ones usually missing, because the stack is assumed to be working when
it is the thing that broke:

```text
metrics stopped arriving
logs stopped arriving
Grafana is unreachable
the alert engine is not evaluating
alerts fire but nobody receives them
a dashboard renders empty after a restore
a disk holding an agent buffer is full
```

Each needs the layer boundaries spelled out, because the reporter almost never owns
the layer that failed.

## Rollback per layer

| Layer | Rollback | Verification |
|---|---|---|
| dashboard | revert source and generated artifact together | panels render with data |
| datasource | revert provisioning file | health check passes |
| alert rule | revert rule file | engine no longer lists it |
| contact point | revert configuration | synthetic delivery test |
| Grafana version | previous pinned version | dashboards and datasources load |

Pin the Grafana version. An unpinned upgrade changes panel rendering and query
behaviour in ways that are discovered by users, not by a release note.

## Ownership

```text
who owns the Grafana instance and its upgrades
who owns each dashboard
who owns each alert rule and its receiver
who is called when the observability stack itself is down
```

Write it down. During an incident is the wrong time to discover that the answer
was ambiguous.
