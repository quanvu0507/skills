# Scheduled jobs

## Four terminal outcomes

Every scheduled run ends in exactly one of these:

```text
success
partial_failure
failure
skipped_lock
```

| Outcome | Meaning |
|---|---|
| `success` | the job ran and completed all work |
| `partial_failure` | the job ran, completed some items, and recorded per-item failures |
| `failure` | the job ran and aborted |
| `skipped_lock` | another instance held the lock, so this instance did no work |

`skipped_lock` is a **normal** outcome under a `SingleFlight` pattern, not an
error. Conflating it with `failure` makes a correctly-behaving multi-instance
deployment look broken. Conflating it with `success` hides the case where *every*
instance skips — a stuck lock — and the job silently stops running while the
success rate stays at 100%.

`partial_failure` matters because a job that processes 10,000 items and fails 3 is
neither success nor failure, and collapsing it into either one loses the signal.

## Record at the lock boundary

```scala
def runWithMetrics(jobName: String)(body: => JobResult): Unit = {
  val started = System.nanoTime()
  val outcome =
    advisoryLock.tryAcquire(jobName) match {
      case None => "skipped_lock"                       // no work attempted
      case Some(lock) =>
        try body match {
          case JobResult.Ok            => "success"
          case JobResult.Partial(_, _) => "partial_failure"
          case JobResult.Failed(_)     => "failure"
        } catch {
          case NonFatal(_) => "failure"
        } finally lock.release()                        // always released
    }
  metrics.jobRuns.labelValues(jobName, outcome).inc()
  metrics.jobDuration.labelValues(jobName).observe(elapsedSeconds(started))
}
```

The wrapper sits **outside** the lock acquisition so the skipped case is
observable, and the counter increments on exactly one path. Putting the recording
inside the lock makes `skipped_lock` unobservable, which is the case you most need
to see.

`finally lock.release()` is not optional: a PostgreSQL advisory lock held by a
crashed job blocks every future run until the session ends.

## Metrics

| Metric | Type | Labels |
|---|---|---|
| `scheduled_job_runs_total` | counter | `job_name`, `outcome` |
| `scheduled_job_duration_seconds` | histogram | `job_name` |
| `scheduled_job_last_success_timestamp_seconds` | gauge | `job_name` |
| `scheduled_job_items_processed_total` | counter | `job_name`, `outcome` |

`job_name` comes from a fixed, enumerated list defined in code — never from
configuration that a deployment could extend without review, and never from data.

## Alert on staleness, not on failures

A job that has not succeeded is the actual problem; a single failed run that the
next run recovers is usually not.

```promql
time() - scheduled_job_last_success_timestamp_seconds{job_name="example"} > 7200
```

Set the threshold from the job's schedule plus a tolerated number of missed runs.
Only set it after a baseline exists — a job whose real runtime is unknown gets a
threshold picked from imagination, and it will page on the first slow night.

## Overlap and long runs

If a run can exceed its interval, the scheduler will start the next one. The
advisory lock is what prevents concurrent execution — that is why `skipped_lock`
exists and why it must be distinguishable. Track:

```text
scheduled_job_duration_seconds       is the run approaching the interval?
skipped_lock rate                    is another instance always winning?
```

A `skipped_lock` rate of 100% on every instance means nothing is running at all.

## Tests

```text
a test per outcome: success, partial_failure, failure, skipped_lock
a test asserts exactly one outcome is recorded per invocation
a test asserts a thrown exception records failure and releases the lock
a test asserts the lock is released on every path
a test asserts job_name values come from the fixed enumerated list
```
