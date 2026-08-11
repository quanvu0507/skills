# Actor systems

## Instrument types, never instances

An actor system creates and destroys actors continuously. Labelling by actor path
or actor id produces one series per instance — unbounded by construction, and it
grows for as long as the process runs.

```text
actor_type="device_session"   bounded, from a fixed list
actor_path="/user/dev/8f2c"   one series per actor; never a label
```

Take `actor_type` from a compile-time constant per actor class.

## Metrics

| Metric | Type | Labels |
|---|---|---|
| `actor_messages_total` | counter | `actor_type`, `outcome` |
| `actor_message_duration_seconds` | histogram | `actor_type` |
| `actor_mailbox_depth` | gauge | `actor_type` |
| `actor_instances_active` | gauge | `actor_type` |
| `actor_restarts_total` | counter | `actor_type`, `reason` |
| `actor_dead_letters_total` | counter | `actor_type` |

## Mailbox depth is the leading indicator

An actor whose mailbox is growing is falling behind, and nothing else shows it: the
actor is alive, the process is healthy, throughput looks normal until the moment it
does not. Track depth per actor type, and alert on sustained growth rather than on
an absolute number.

An unbounded mailbox converts backpressure into memory growth. If the framework
supports a bounded mailbox, use one and count the rejections.

## Restarts and supervision

Supervision restarts are invisible by default — that is the point of supervision.
Count them with a finite `reason`, because a rising restart rate is a failure that
is being masked, and masked failures surface later as data problems.

`actor_dead_letters_total` catches messages sent to a stopped actor. A rising dead
letter count means work is being silently dropped.

## Do not change supervision or ordering

```text
do not change the supervision strategy to make a metric easier to record
do not add a message hop for measurement
do not change mailbox type or ordering guarantees
do not change the remote protocol shape
```

The last one matters most in a clustered system: a change to the wire shape breaks
rolling upgrades, because nodes on different versions can no longer talk. Adding a
field to a message for tracing purposes is a protocol change.

## Remote and cluster

For a clustered system, also track membership events and unreachable-node counts,
labelled by role from a fixed set — never by node address, which changes on every
restart and starts a new series each time.

## Logs

Log actor failures once, at the supervisor that handled them, with `actor_type` and
a finite `error_kind`. Do not log the message that caused the failure: it is a
payload, and it may carry credentials or personal data.

## Tests

```text
labels use actor_type only; no path, id or address appears
mailbox depth is observable per type
a restart increments the counter with a finite reason
a dead letter is counted
the supervision strategy and message ordering are unchanged by instrumentation
