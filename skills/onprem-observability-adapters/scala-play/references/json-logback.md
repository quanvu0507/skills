# JSON logging with Logback

## Goal

One JSON object per line on stdout, with semantic fields, no payloads and no
credentials. Alloy reads stdout; the application never connects to a log backend.

## Encoder

Use a JSON encoder on a `ConsoleAppender`. Pin the encoder library to an exact
version in `build.sbt` and record it in the observability ADR — a floating version
silently changes the field layout and breaks every LogQL query that parsed it.

```xml
<configuration>
  <appender name="STDOUT" class="ch.qos.logback.core.ConsoleAppender">
    <encoder class="net.logstash.logback.encoder.LogstashEncoder">
      <timeZone>UTC</timeZone>
      <fieldNames>
        <timestamp>ts</timestamp>
        <message>msg</message>
        <logger>logger</logger>
        <thread>thread</thread>
        <levelValue>[ignore]</levelValue>
      </fieldNames>
      <!-- Bound the stack trace: an unbounded one can exceed Loki's line limit
           and the whole event is dropped, losing the error entirely. -->
      <throwableConverter class="net.logstash.logback.stacktrace.ShortenedThrowableConverter">
        <maxDepthPerThrowable>30</maxDepthPerThrowable>
        <maxLength>4096</maxLength>
        <rootCauseFirst>true</rootCauseFirst>
      </throwableConverter>
    </encoder>
  </appender>

  <root level="INFO">
    <appender-ref ref="STDOUT"/>
  </root>
</configuration>
```

Keep exactly one appender writing to stdout. A second appender writing a file
inside the container produces logs nobody collects and a disk that fills up.

## Structured arguments, not string interpolation

```scala
import net.logstash.logback.argument.StructuredArguments.keyValue

// Yes — msg stays stable, fields are queryable.
logger.info(
  "http_request_completed",
  keyValue("event", "http_request_completed"),
  keyValue("method", method),
  keyValue("route", routeTemplate),
  keyValue("status", status),
  keyValue("duration_ms", durationMs),
  keyValue("request_id", requestId),
)

// No — the values are trapped inside a sentence and the message is unstable.
logger.info(s"Request $method $uri completed with $status in ${durationMs}ms")
```

Interpolated messages force LogQL regex parsing, and every wording change breaks
the query. A stable `event` value plus separate fields survives rewording.

## Context across futures

Logback's `MDC` is thread-local. Play executes futures on a pool that swaps
threads, so MDC set before a `map` is frequently absent — or worse, holds another
request's value — inside it.

```text
pass the request context explicitly through the call chain, or
attach fields at the log call from the context you already hold
never rely on MDC surviving a Future boundary
never store the current correlation id in a var or a singleton
```

The failure only appears under concurrency, so it passes every local test and
produces mislabeled logs in production, exactly when you are using them to
diagnose an incident.

## Redaction

Redact where the value is constructed, before it reaches the encoder:

```scala
private val Redacted = "[REDACTED]"

def safeHeaders(headers: Headers): Map[String, String] =
  headers.toMap.map { case (name, values) =>
    if (SensitiveHeaders.contains(name.toLowerCase)) name -> Redacted
    else name -> values.mkString(",")
  }
```

`SensitiveHeaders` covers at least `authorization`, `cookie`, `set-cookie`,
`proxy-authorization` and any project-specific API-key header. A fixed marker is
required — truncation still leaks a prefix, and an empty string is
indistinguishable from a header that was legitimately absent.

Never log: request or response bodies, signed URLs or query strings, decoded JWT
claims, or raw third-party payloads.

## Levels

`ERROR` means a human needs to act. A malformed client request is `WARN` or `INFO`
with an outcome field. Logging every 4xx at `ERROR` trains operators to ignore the
error stream, which is the same as having none.

Log a throwable once, at the boundary that handled it. Re-logging as it propagates
turns one failure into several error events and makes every error-rate panel wrong.

## Tests

```text
a captured log line parses as valid JSON
the terminal event appears exactly once per request, including on failure
a request carrying an Authorization header logs the redaction marker, never the value
concurrent requests do not interleave correlation ids
a very long stack trace stays within the configured bound
```
