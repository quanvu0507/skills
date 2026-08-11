# Gateway and management paths

## The rule

`/metrics`, `/health`, `/ready` and any other management route must be reachable
from inside the cluster and refused from outside it. Verify with a **negative
probe** before rollout — an explicit test that the path is refused, not an
assumption that it is.

## Why the assumption fails

A Gateway or Ingress rule that forwards a path prefix forwards everything under it:

```yaml
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /
```

That forwards `/metrics` too. The service is now publishing its internal metric
names, label values, route templates, dependency names and version to anyone who
asks. Metric label values routinely leak internal topology that is not public
elsewhere.

Serving management routes on the same port as business traffic is still the right
choice — a second port means a second probe, a second rule and a second thing to
secure. What it requires is an explicit deny at the gateway.

## Explicit deny

Prefer an explicit rule over relying on route ordering:

```yaml
  rules:
    - matches:
        - path: { type: PathPrefix, value: /metrics }
      filters:
        - type: RequestRedirect
          requestRedirect: { statusCode: 404 }
    - matches:
        - path: { type: PathPrefix, value: /api }
      backendRefs:
        - name: <service>
          port: 80
```

Match the exact prefixes used by the application, and keep that list next to the
route definitions so adding a management route prompts adding a deny.

## Negative probe

Run from outside the cluster boundary, as an unauthenticated caller:

```bash
for path in /metrics /health /ready /debug/pprof; do
  code=$(curl -s -o /dev/null -w '%{http_code}' "https://<external-host>${path}")
  printf '%s -> %s\n' "$path" "$code"
done
```

Pass condition: every management path returns 401, 403 or 404. A 200 is a release
blocker, not a warning.

Record the probe output as `runtime-evidence` with the date and the external host
used. Re-run it after any gateway or ingress change — this is the check most
likely to regress silently, because nothing else fails when it does.

## Internal reachability

The scrape must still work. Confirm from inside:

```bash
kubectl -n <ns> run probe --rm -it --restart=Never --image=curlimages/curl:8.11.1 -- \
  curl -s -o /dev/null -w '%{http_code}\n' http://<service>.<ns>.svc:80/metrics
```

Expect 200. Pin the probe image to an exact tag; `latest` in a diagnostic command
is still a supply-chain decision.

## Probes

Liveness and readiness are configured by the GitOps repository, and they must use
the endpoints the application actually implements:

```text
liveness  -> /health  constant-time, no dependency calls
readiness -> /ready   local components only, never downstream dependency health
```

A readiness probe that fails on downstream dependency health removes every replica
from the pool at once during a shared-dependency incident, turning degradation into
a full outage.

Set `timeoutSeconds` above the endpoint's real response time under load, and
`failureThreshold` high enough that one slow scrape does not restart the pod.

## Checklist

```text
management paths enumerated and listed next to the route definitions
explicit deny rule present for each
negative probe run from outside; all paths refused; output recorded
internal probe confirms the scrape path returns 200
liveness endpoint performs no dependency calls
readiness reflects local state only
probe timings justified by measured response time
re-probe scheduled after any gateway change
```
