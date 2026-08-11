# Verification and retention

## Canary: prove the whole path

"Alloy is running" proves a process exists. It does not prove a line travelled from
the application to a query result. Verify end to end with a canary.

```text
1. Emit a uniquely identifiable line from the running application.
2. Query Loki for it, filtering on the unique value at query time.
3. Record the delay between emission and availability.
4. Record the exact query and its output as runtime-evidence.
```

```logql
{namespace="apps", app="example-service"} | json | canary_id="<unique value>"
```

The unique value is a **field**, never a label — a canary that creates a stream per
run is its own cardinality problem.

Run the canary after every change to collection configuration, after an Alloy
upgrade and after a Loki upgrade. It is the only check that covers all of
discovery, relabeling, write, ingestion and query together.

## Continuous canary

A periodic canary plus an alert on its absence detects a broken pipeline before an
incident does. Without it, a collection outage is discovered when someone goes
looking for logs during an incident — the worst possible moment.

```promql
time() - log_canary_last_seen_timestamp_seconds > 600
```

## Redaction verification

Before declaring the pipeline done, sample real traffic and check:

```text
no Authorization header value, cookie or token appears
no request or response body appears
no signed URL or signed query string appears
no personal data beyond the project's classification appears
a deliberately sensitive test value renders as the redaction marker
```

A finding here is a P0: it is live data exposure, and the fix is at the source plus
possible deletion of already-ingested data.

## Retention

Retention is a decision, not a default. Record for each stream class:

| Question | Answer to record |
|---|---|
| how long are these logs kept? | |
| what regulatory or contractual requirement drives it? | |
| what is the storage cost at the current volume? | |
| who is allowed to query them? | |
| how are they deleted, and by whom? | |

Different classes usually need different periods — a debug stream and an audit
stream should not share one policy. If the deployed Loki supports per-stream
retention, use it; otherwise document that the global policy applies and what that
means for the audit class.

## Volume budget

State expected volume per service and compare it with reality after rollout. A
service that emits ten times its budget is usually logging per-message on a hot
path, and it degrades ingestion for everyone else.

```logql
sum(rate({namespace="apps", app="example-service"}[5m]))
```

## Ownership

Name, explicitly:

```text
who owns the application's log format
who owns the Alloy configuration
who owns Loki capacity and retention
who to contact when logs are missing
```

Missing logs are usually reported to whoever owns the application, and the cause is
usually in a layer they do not own. Writing this down shortens every such incident.

## Rollback

```text
collection config: revert the Alloy configuration and re-run the canary
log format:        revert the application; note that queries parsing new fields break
retention:         a shortened retention already deleted data — it is not reversible
```

The retention line is why a retention change needs explicit approval, not a
config-tuning commit.
