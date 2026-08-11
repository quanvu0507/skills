# Private Prometheus registry

## Why not the default registry

`CollectorRegistry.defaultRegistry` is process-global mutable state. In a Play
application that produces three concrete failures:

- registering the same collector twice throws `IllegalArgumentException` at
  startup, and the second registration is often in a library you do not control;
- tests sharing a JVM leak metrics between suites, so a test passes alone and
  fails in the suite;
- a dependency's opinionated default collectors appear in your scrape output with
  names you never chose and cannot remove.

Own one registry, pass it explicitly.

## Shape

```scala
import io.prometheus.metrics.model.registry.PrometheusRegistry

@Singleton
final class AppMetricsRegistry {
  val registry: PrometheusRegistry = new PrometheusRegistry()
}
```

Bind it as an eager singleton so registration happens once at startup and a
duplicate-name mistake fails the boot rather than the first scrape.

Every collector takes the registry as a constructor argument:

```scala
@Singleton
final class HttpMetrics @Inject() (metrics: AppMetricsRegistry) {
  private val requests = Counter.builder()
    .name("http_server_requests_total")
    .help("Terminal HTTP request outcomes")
    .labelNames("method", "route", "status_class", "outcome")
    .register(metrics.registry)

  private val duration = Histogram.builder()
    .name("http_server_request_duration_seconds")
    .help("HTTP request duration")
    .labelNames("method", "route")
    .register(metrics.registry)
}
```

Declare collectors as `private val` fields of a singleton, created once. Building a
collector inside a request handler re-registers it on every request.

## Version pinning

Pin the Prometheus Java client to an exact version in `build.sbt`, and record that
version in the observability ADR:

```scala
libraryDependencies += "io.prometheus" % "prometheus-metrics-core" % "1.8.0"
```

The 0.16 and 1.x APIs differ substantially. A floating version turns a routine
dependency bump into a compile failure in instrumentation code that nobody is
looking at.

## JVM and process collectors

Register the built-in JVM collectors deliberately, once, on the same private
registry. They are cheap, bounded and answer the first question in most incidents
(is it GC, is it heap, is it threads). Register them at startup next to the
registry itself, not scattered across modules.

## Exposition

Expose the registry through one controller action that writes the text exposition
format for the scraper's `Accept` header. The action must:

```text
read only precomputed state — never block, never call a dependency
never touch a KafkaConsumer, a database or an HTTP client
complete well inside the scrape timeout
```

A `/metrics` endpoint that performs work is a denial-of-service surface: the
scraper calls it every 15–30 seconds forever, and a slow scrape both loses data
and consumes a request thread.

## Testing

```text
a test asserts the registry contains exactly the expected metric names
a test asserts scraping twice returns the same series with no duplicate registration
each test builds its own registry instance — no shared global state
a test asserts label values come from the expected finite domain
```
