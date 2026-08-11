# Tokio async boundaries

## Cancellation is a terminal outcome

A dropped future never resumes. Code after an `.await` that was cancelled does not
run, so recording at the end of a function loses every cancelled operation — and
an in-flight gauge incremented at the start is never decremented, so it climbs
forever and eventually reads as thousands of concurrent requests that do not exist.

Record in a guard whose `Drop` runs on every path:

```rust
struct TaskGuard {
    metrics: Arc<Metrics>,
    kind: &'static str,
    started: Instant,
    outcome: Outcome,       // set to Success/Failure before the guard drops
}

impl TaskGuard {
    fn new(metrics: Arc<Metrics>, kind: &'static str) -> Self {
        metrics.in_flight.with_label_values(&[kind]).inc();
        Self { metrics, kind, started: Instant::now(), outcome: Outcome::Cancelled }
    }
    fn finish(&mut self, outcome: Outcome) { self.outcome = outcome; }
}

impl Drop for TaskGuard {
    fn drop(&mut self) {
        self.metrics.in_flight.with_label_values(&[self.kind]).dec();
        self.metrics.total
            .with_label_values(&[self.kind, self.outcome.as_label()])
            .inc();
        self.metrics.duration
            .with_label_values(&[self.kind])
            .observe(self.started.elapsed().as_secs_f64());
    }
}
```

The guard defaults to `Cancelled`. A task that completes overwrites it; a task that
is dropped mid-`await` records `cancelled` and releases the gauge. Exactly one
terminal record per task, on every path.

## The four outcomes

```text
success    completed and produced its result
failure    completed with an error
timeout    the timeout wrapper elapsed first
cancelled  the future was dropped before completion
```

`timeout` and `cancelled` are distinct and must not be merged. A rising `timeout`
rate points at a slow dependency; a rising `cancelled` rate points at clients
disconnecting or at shutdown behaviour. Collapsing them into `failure` makes both
undiagnosable.

```rust
match tokio::time::timeout(budget, work).await {
    Ok(Ok(value)) => { guard.finish(Outcome::Success); Ok(value) }
    Ok(Err(err))  => { guard.finish(Outcome::Failure); Err(err) }
    Err(_elapsed) => { guard.finish(Outcome::Timeout);  Err(Error::Timeout) }
}
```

## In-flight cleanup on shutdown

Graceful shutdown cancels outstanding tasks. Because each guard's `Drop` records a
terminal outcome, shutdown produces a burst of `cancelled` — which is correct and
worth seeing. Assert in a test that in-flight gauges return to zero after a
shutdown, because a leak here is invisible until an operator is looking at an
impossible number during an incident.

## Channels

Every channel is bounded and every channel has a depth gauge:

```rust
let (tx, rx) = tokio::sync::mpsc::channel::<Item>(capacity);
metrics.channel_capacity.with_label_values(&["ingest_queue"]).set(capacity as f64);
```

An unbounded channel does not remove backpressure; it converts backpressure into
memory growth, and the process is killed by the OOM reaper with no signal that
would have predicted it.

Record saturation, not just depth:

| Metric | Meaning |
|---|---|
| `channel_depth{channel}` | current queued items |
| `channel_capacity{channel}` | configured bound |
| `channel_send_blocked_total{channel}` | sends that had to wait |
| `channel_send_dropped_total{channel}` | sends abandoned via `try_send` |

`channel_send_blocked_total` is the leading indicator: depth reaching capacity is
already the incident, whereas blocked sends rise before that.

`channel` is a compile-time constant name. Never label by item content.

## Business ordering is not negotiable

Instrumentation observes; it does not restructure. Do not:

```text
add a task spawn to make a measurement possible
change a channel from bounded to unbounded to avoid a blocked-send metric
move an await, a commit or a flush to make timing easier to record
add a lock that changes contention behaviour
```

If a measurement requires changing behaviour, record it as a known gap instead.

## `spawn_blocking`

Blocking work on the async runtime stalls every task sharing that worker thread.
Measure the blocking pool separately — queue time there is invisible in the async
task metrics and is a common cause of "the service is slow but every metric looks
fine".

## Tests

```text
a test per outcome: success, failure, timeout, cancelled
a test drops a future mid-await and asserts exactly one cancelled record
a test asserts in-flight returns to zero after a cancellation storm
a test asserts a shutdown records cancelled, not failure
a test fills a bounded channel and asserts send_blocked increments
a test asserts channel and task_kind labels come from the fixed constant set
```
