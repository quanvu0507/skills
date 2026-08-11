# Background workers and scheduled jobs

## Workers and jobs differ

A **background worker** processes items from a queue continuously. A **scheduled
job** runs at a time, does a batch of work, and stops. They fail differently and
need different signals.

| | worker | scheduled job |
|---|---|---|
| primary question | is it keeping up? | did it run, and when did it last succeed? |
| key signal | queue depth and processing rate | time since last success |
| terminal unit | one item | one run |

## Worker metrics

| Metric | Type | Labels |
|---|---|---|
| `worker_items_total` | counter | `worker`, `outcome` |
| `worker_item_duration_seconds` | histogram | `worker` |
| `worker_items_in_flight` | gauge | `worker` |
| `worker_queue_depth` | gauge | `queue` |
| `worker_last_activity_timestamp_seconds` | gauge | `worker` |

`worker` and `queue` are compile-time constants from a fixed list, never derived
from item content.

**Queue depth alone is not enough.** A depth of zero means either "caught up" or
"the producer died". Pair it with the processing rate and the last-activity
timestamp so the two cases are distinguishable.

## Scheduled job outcomes

Four terminal outcomes, exactly one per run:

```text
success
partial_failure
failure
skipped_lock
```

`skipped_lock` is a **normal** outcome when a single-flight lock protects the job
across instances. Merging it into `failure` makes a correctly-behaving deployment
look broken. Merging it into `success` hides the case where *every* instance skips
— a stuck lock — while the success rate stays at 100% and the job has silently
stopped running.

`partial_failure` matters because a run that processes 10,000 items and fails 3 is
neither success nor failure; collapsing it into either loses the signal.

## Record at the lock boundary

The recording wrapper sits **outside** lock acquisition, so the skipped case is
observable. Recording inside the lock makes `skipped_lock` unobservable — the case
you most need to see. Release the lock on every path, including exceptions: a held
lock blocks every future run.

## Job metrics

| Metric | Type | Labels |
|---|---|---|
| `scheduled_job_runs_total` | counter | `job_name`, `outcome` |
| `scheduled_job_duration_seconds` | histogram | `job_name` |
| `scheduled_job_last_success_timestamp_seconds` | gauge | `job_name` |
| `scheduled_job_items_processed_total` | counter | `job_name`, `outcome` |

`job_name` comes from a fixed enumerated list in code — never from configuration a
deployment could extend without review, and never from data.

## Alert on staleness

A job that has not succeeded is the problem; a single failed run that the next run
recovers usually is not.

```promql
time() - scheduled_job_last_success_timestamp_seconds{job_name="example"} > 7200
```

Derive the threshold from the schedule plus a tolerated number of missed runs, and
only after a baseline exists.

## Overlap

If a run can exceed its interval, the scheduler starts the next one and the lock is
what prevents concurrency. Track run duration against the interval, and watch the
`skipped_lock` rate: 100% on every instance means nothing is running at all.

## Tests

```text
one test per outcome, including skipped_lock
exactly one outcome recorded per invocation
an exception records failure and still releases the lock
in-flight returns to zero after an abnormal termination
job_name and worker labels come from the fixed lists
