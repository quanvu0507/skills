# WebSockets and long-lived connections

## Connections are not requests

A request is short and its terminal outcome is obvious. A connection lives for
minutes or hours, and the interesting failures are about *duration* and *why it
ended*, not about a status code. Instrument the connection lifecycle and the
message flow as two separate things.

## Metrics

| Metric | Type | Labels |
|---|---|---|
| `websocket_connections_active` | gauge | `endpoint` |
| `websocket_connections_total` | counter | `endpoint`, `close_reason` |
| `websocket_connection_duration_seconds` | histogram | `endpoint`, `close_reason` |
| `websocket_messages_total` | counter | `endpoint`, `direction`, `outcome` |
| `websocket_send_queue_depth` | gauge | `endpoint` |
| `websocket_send_dropped_total` | counter | `endpoint`, `reason` |

`endpoint` is a route template from a fixed list. `direction` is `inbound` or
`outbound`. `close_reason` is a small closed set:

```text
client_closed
server_closed
timeout
protocol_error
auth_expired
shutdown
```

Never label by connection id, session id, user id or device id — that is one series
per connection, which is the definition of unbounded.

## The active gauge must be paired

Increment on establish, decrement in a construct that runs on **every** termination
path: clean close, abrupt disconnect, timeout, server shutdown, panic. An unpaired
decrement makes the gauge climb forever, and "active connections" becomes a number
nobody trusts — usually discovered mid-incident.

Test it explicitly: open connections, kill them abnormally, assert the gauge
returns to zero.

## Backpressure

A slow client is the characteristic WebSocket failure. The server queues outbound
messages, the client does not drain them, and memory grows until the process dies —
with every other metric looking normal.

```text
websocket_send_queue_depth      current queued messages
websocket_send_dropped_total    messages abandoned, by reason
```

Bound the send queue. An unbounded queue does not remove backpressure; it converts
backpressure into an OOM with no preceding signal.

## Duration distribution

Connection duration is bimodal in most systems: short-lived reconnect churn and
long-lived healthy sessions. Choose histogram buckets that resolve both, and watch
for a rising short-duration mode — that is a reconnect loop, and it is usually
invisible in a connection count that looks steady.

## Heartbeats

Track ping/pong outcomes. A connection that is open but not exchanging heartbeats
is functionally dead while still counting as active.

## Logs

Log connection open and close as terminal events with duration and close reason.
Do **not** log message payloads. For a high-rate stream, do not log per message at
all — sample or aggregate, or the log volume exceeds the data the connection
carries.

## Tests

```text
active gauge returns to zero after abnormal disconnects
every close path records exactly one close_reason
a full send queue increments dropped, and does not grow without bound
labels come only from the fixed endpoint, direction and close_reason sets
no payload appears in logs
