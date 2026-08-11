---
name: application-instrumentation
license: Apache-2.0
compatibility: "Any language or framework; Prometheus-compatible metrics, JSON logs, Grafana OSS, Loki OSS, VictoriaMetrics; no Grafana Cloud dependency"
description: "Choose and instrument application boundaries from declared runtime capabilities — HTTP APIs, background workers, event consumers, scheduled jobs, WebSockets, database clients, outbound HTTP clients and actor systems. Defines terminal outcome, latency and in-flight semantics before code, and preserves business ordering, threading and wire compatibility. Use when deciding what to instrument in a service, adding metrics or logs to a new boundary, or reviewing whether instrumentation changed behaviour."
---

# Application instrumentation

Decides **what** to instrument from a project's declared capabilities. The language
adapter decides **how**. Read
[`observability-contract`](../observability-contract/SKILL.md) first.

## Decision sequence

```text
1. Read the project profile.
2. List declared runtime capabilities.
3. Instrument only declared active boundaries.
4. Preserve business ordering, threading and wire compatibility.
5. Define success/failure/latency/in-flight semantics before adding code.
6. Reject identifiers, payloads and exception text as metric labels.
7. Require tests for every terminal outcome and cleanup path.
```

Follow it in order. Step 3 is the one most often skipped: instrumenting a boundary
the project does not actually use produces metrics that are always zero, and a
zero series is indistinguishable from a broken one during an incident.

**Declared means active.** A capability that exists as dead code, a planned
feature or a disabled code path is not instrumented. Verify it is on the live path
before adding a metric to it.

## Capabilities to boundaries

| Capability | Boundary | Reference |
|---|---|---|
| `http_api` | inbound request lifecycle | [`http-api.md`](references/http-api.md) |
| `background_worker` | task execution | [`workers-and-jobs.md`](references/workers-and-jobs.md) |
| `event_consumer` | message consumption | [`event-consumers.md`](references/event-consumers.md) |
| `scheduled_jobs` | timed run at its lock boundary | [`workers-and-jobs.md`](references/workers-and-jobs.md) |
| `websocket` | connection lifecycle and message flow | [`websockets.md`](references/websockets.md) |
| `database_client` | outbound query lifecycle | [`outbound-clients.md`](references/outbound-clients.md) |
| `external_http_client` | outbound call lifecycle | [`outbound-clients.md`](references/outbound-clients.md) |
| `actor_system` | supervision and mailbox health | [`actor-systems.md`](references/actor-systems.md) |

## Universal semantics

Every boundary defines these four before any code is written:

| Semantic | Question it answers |
|---|---|
| **success** | did the unit of work complete as intended? |
| **failure** | how did it fail, classified into a finite set? |
| **latency** | how long from start to terminal outcome? |
| **in-flight** | how many are running right now? |

Rules that apply to all of them:

```text
exactly one terminal outcome per unit of work, on every path
in-flight increments and decrements are paired, including on the abnormal path
failure is classified into a finite error_kind, never a raw message
latency is measured start-to-terminal, not start-to-success
```

The paired in-flight rule is the one that bites: a gauge incremented at entry and
decremented only on the success path climbs forever, and eventually reads as
thousands of concurrent operations that do not exist.

## Behaviour preservation

Instrumentation observes. It does not restructure. Never, for a measurement:

```text
change ordering of business operations
change commit, flush, acknowledgement or offset behaviour
change threading, add a thread, or move work to another executor
add or remove a lock, or change lock scope
change a wire or protocol shape
add a second server, port or agent
```

If a measurement is only obtainable by changing behaviour, do not take it. Record
it as a known gap and say what would be needed. Ingest correctness outranks
metric granularity every time.

## Label discipline

Before adding any label, write down its domain and count it. If you cannot count
it, it is not a label.

**Rejected, always:** identifiers of any kind, payload values, exception messages,
raw paths, free text, and anything a client or an attacker can influence.

## Tests

```text
one test per terminal outcome, including timeout, cancellation and cleanup
a test asserting exactly one terminal record per unit of work
a test asserting in-flight returns to zero after an abnormal termination
a test asserting label values come from the declared finite domain
a test asserting business ordering is unchanged by the instrumentation
```

## Done

```text
every declared active capability has defined semantics
no undeclared boundary was instrumented
label domains counted; total series within the stated budget
behaviour preservation reviewed explicitly, not assumed
tests cover every terminal path
```
