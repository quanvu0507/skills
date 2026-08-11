# Event consumers

## Metrics never change the control flow

A consumer's poll, process, acknowledge and offset behaviour is business-critical.
Instrumentation observes it; it must not:

```text
add, move or remove an acknowledgement or commit
change commit mode or frequency
change offset positioning or replay behaviour
add a poll, pause, resume or seek
introduce a thread that touches a client which is not thread-safe
```

Most message-broker clients are explicitly not thread-safe. Calling one from a
metrics-scrape thread either throws or — worse — blocks the consume loop past its
deadline, the broker declares the consumer dead, and a **rebalance** follows.
Adding metrics then causes the outage the metrics were meant to detect.

## Snapshot pattern

The consume loop owns the client. It publishes an immutable snapshot after it has
finished its client interactions; the metrics endpoint reads the snapshot and never
blocks.

```text
consume loop:  poll -> process -> acknowledge -> publish snapshot
metrics read:  snapshot only, never the client
```

An atomic reference holding an immutable value is the right shape: readers never
see a half-updated state and never contend with the writer.

## Metrics

| Metric | Type | Labels |
|---|---|---|
| `consumer_messages_total` | counter | `consumer`, `outcome` |
| `consumer_batch_duration_seconds` | histogram | `consumer` |
| `consumer_last_poll_timestamp_seconds` | gauge | `consumer` |
| `consumer_assigned_partitions` | gauge | `consumer` |
| `consumer_lag_records` | gauge | `consumer`, `partition` (see below) |
| `consumer_rebalance_total` | counter | `consumer`, `phase` |

## Labels

`consumer` is a fixed configured name. `partition` is acceptable **only** when the
partition count is small and fixed, and the resulting series count is documented.
On a 200-partition topic that single label is 200 series for one metric — decide
that deliberately, and drop it if aggregate lag answers the question.

Never a label:

```text
topic name taken from a message (use the fixed configured topic list)
offset, key, headers or any payload value
device, trip, session, tenant or user identity
consumer group generation id
```

## Staleness beats liveness

`consumer_last_poll_timestamp_seconds` is the highest-value metric here. A consumer
that is alive but not consuming looks perfectly healthy on every process metric.

```promql
time() - consumer_last_poll_timestamp_seconds > 300
```

## Rebalances

Count rebalance phases through the client's rebalance callback, which runs on the
consume thread and may touch the client. Rebalance storms are otherwise invisible
and explain most "the consumer is slow" reports.

## Dead letters and retries

Record retries and dead-letter routing as outcomes, not as separate silent paths. A
message that is retried forever and never acknowledged is invisible unless retry
attempts are counted.

## Tests

```text
no client method is called from the metrics path
the poll -> process -> acknowledge order is unchanged by instrumentation
exactly one outcome per message or per batch, including the failure path
the snapshot is readable concurrently with an active consume loop
partition label cardinality matches the documented budget
