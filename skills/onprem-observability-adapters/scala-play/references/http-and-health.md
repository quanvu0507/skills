# HTTP instrumentation and health

## Use the port Play already binds

Serve `/metrics` and the health endpoints from the existing routes file:

```text
GET  /metrics   controllers.ManagementController.metrics
GET  /health    controllers.ManagementController.live
GET  /ready     controllers.ManagementController.ready
```

A second HTTP server for management traffic requires a second container port, a
second probe definition, a second Gateway or ingress rule and a new listener to
secure. None of that buys anything when the same process can answer on the port
that is already open and already protected.

**Management paths must not be reachable from outside.** Before rollout, run a
negative probe from outside the cluster or network boundary and confirm `/metrics`
is refused. Do this as an explicit test, not an assumption — an ingress that
forwards `/` forwards `/metrics` too.

## Instrument the request lifecycle once

Use a Play `Filter`, which sees both the success and the error path:

```scala
final class MetricsFilter @Inject() (metrics: HttpMetrics)(implicit
    val mat: Materializer,
    ec: ExecutionContext,
) extends Filter {

  def apply(next: RequestHeader => Future[Result])(rh: RequestHeader): Future[Result] = {
    val started = System.nanoTime()
    // transform sees Success and Failure, so the terminal event fires on both.
    next(rh).transform { tried =>
      val route = routeTemplate(rh)
      val statusClass = tried.map(r => s"${r.header.status / 100}xx").getOrElse("5xx")
      val outcome = if (tried.isSuccess) "success" else "failure"
      metrics.record(rh.method, route, statusClass, outcome, System.nanoTime() - started)
      tried
    }
  }
}
```

`onComplete` returns `Unit` and is easy to attach to only the success branch;
`transform` forces both branches to be handled. If the application has a custom
`HttpErrorHandler` that short-circuits before filters, instrument there as well and
assert in a test that a failing request produces exactly one terminal record — not
zero, not two.

## Normalized route

Play exposes the matched route template through `HandlerDef`:

```scala
private def routeTemplate(rh: RequestHeader): String =
  rh.attrs.get(Router.Attrs.HandlerDef).map(_.path).getOrElse("other")
```

Never use `rh.uri` or `rh.path`: every distinct identifier in the path becomes a
new series, and a scanner probing random paths becomes an unbounded label domain
an attacker controls.

Requests that match no route fall into a single `other` bucket. Count them —
a rising `other` rate means either a missing route or someone scanning.

## Health semantics

```text
live  = process/framework booted
ready = local essential components initialized/running
dependency degradation = metrics/logs/alerts, not automatic readiness failure
```

| Endpoint | Returns 200 when | Returns 503 when |
|---|---|---|
| `/health` (liveness) | the process is up and the HTTP stack answers | never, except a genuine unrecoverable state |
| `/ready` (readiness) | local components this instance owns are initialized | migrations pending, consumer not yet assigned, cache not warmed |

**A downstream dependency being unhealthy must not fail readiness.** If it did,
every replica would leave the load-balancer pool at the same moment during a shared
database or broker incident, converting degraded service into total unavailability
— and no instance would be left to serve cached or partial responses.

Model dependency health separately:

```scala
dependency_up{dependency="postgres"} 1
dependency_up{dependency="kafka"}    0
```

Alert on that gauge. Keep readiness about this instance.

## Liveness must not be expensive

A liveness probe that queries a database restarts the pod when the database is
slow, which adds load to the database. Liveness answers one question: is this
process wedged? Keep it a constant-time response.

## Tests

```text
a 2xx request records exactly one terminal event
a 5xx request records exactly one terminal event with outcome=failure
a thrown exception inside the action still records exactly one terminal event
an unmatched path records route="other", never the raw path
/ready returns 503 before initialization completes and 200 after
a simulated dependency outage does NOT change /ready
a negative probe confirms /metrics is not reachable from outside the boundary
```
