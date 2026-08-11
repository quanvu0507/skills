# Kafka consumer metrics

## The hard rule

**Never call a `KafkaConsumer` method from the `/metrics` request thread.**

`KafkaConsumer` is explicitly not thread-safe. It enforces this with a lightweight
lock and throws `ConcurrentModificationException` when a second thread enters. A
scrape that calls `consumer.metrics()`, `consumer.position()`, `consumer.assignment()`
or `consumer.endOffsets()` will, at some point, collide with the poll loop.

The failure mode is worse than an exception: on the paths that block instead of
throwing, the scrape stalls the poll loop, the consumer misses its
`max.poll.interval.ms` deadline, the broker considers it dead and triggers a
**rebalance**. Adding metrics then causes the outage the metrics were meant to
detect.

## Snapshot pattern

The poll loop owns the consumer. It publishes an immutable snapshot; the scrape
reads the snapshot.

```scala
final case class ConsumerSnapshot(
    assignedPartitions: Int,
    lastPollAt: Long,
    lagByPartition: Map[Int, Long],
    lastCommittedOffset: Map[Int, Long],
)

// Written only by the poll thread, read by anyone.
private val snapshot = new AtomicReference[ConsumerSnapshot](ConsumerSnapshot.empty)
```

The poll thread updates it once per cycle, after it has finished its consumer
interactions:

```scala
while (running.get()) {
  val records = consumer.poll(pollTimeout)   // poll thread only
  persist(records)                           // existing business logic
  consumer.commitSync()                      // existing control flow
  snapshot.set(buildSnapshot(consumer))      // consumer touched on this thread only
}
```

The metrics endpoint reads `snapshot.get()` and never blocks.

`AtomicReference` with an immutable case class is the right tool: readers never
see a half-updated value and never contend with the writer.

## Metrics never reorder business logic

Instrumentation observes the existing control flow. It must not:

```text
move, add or remove a commit
change commit mode (sync vs async) or commit frequency
change offset positioning or replay behaviour
add a poll, a pause or a resume
change the order of persist and commit
introduce a new thread that touches the consumer
```

If a measurement is only obtainable by changing that ordering, do not take the
measurement — derive it from what is already observable, or record it as a known
gap. Correctness of the ingest path outranks the granularity of a metric.

## What to record, and where

| Metric | Type | Recorded by | Labels |
|---|---|---|---|
| `kafka_consumer_records_processed_total` | counter | poll thread, after persist | `outcome` |
| `kafka_consumer_batch_duration_seconds` | histogram | poll thread | none |
| `kafka_consumer_last_poll_timestamp_seconds` | gauge | poll thread | none |
| `kafka_consumer_assigned_partitions` | gauge | from snapshot | none |
| `kafka_consumer_lag_records` | gauge | from snapshot | `partition` |
| `kafka_consumer_rebalance_total` | counter | `ConsumerRebalanceListener` | `phase` |

**Label rules.** `partition` is acceptable only when the partition count is fixed
and small, and it must be documented in the metric inventory with its exact
cardinality. Never label by:

```text
topic name taken from the record (use a fixed configured topic list)
offset, key or any payload value
device, trip, vehicle, session or any entity identifier
consumer group generation id
```

Lag per partition on a 200-partition topic is 200 series for one metric. Decide
that deliberately; if the answer is "aggregate lag is enough", drop the label.

## Staleness beats liveness

`kafka_consumer_last_poll_timestamp_seconds` is the highest-value metric here. A
consumer that is alive but not polling looks perfectly healthy on every process
metric. Alert on the age of the last poll:

```promql
time() - kafka_consumer_last_poll_timestamp_seconds > 300
```

## Rebalance visibility

Register a `ConsumerRebalanceListener` that increments a counter on
`onPartitionsRevoked` and `onPartitionsAssigned`. Rebalance storms are otherwise
invisible and explain most "the consumer is slow" reports. The listener runs on
the poll thread, so it may touch the consumer.

## Tests

```text
a test asserts no consumer method is called from the metrics endpoint
a test drives poll -> persist -> commit and asserts the recorded order is unchanged
a test asserts exactly one outcome is recorded per batch, including the failure path
a test asserts the snapshot is readable concurrently with an active poll loop
a test asserts partition label cardinality matches the documented budget
```
