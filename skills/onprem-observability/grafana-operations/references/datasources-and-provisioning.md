# Datasources and provisioning

## Provision from files, never the UI

```yaml
apiVersion: 1
datasources:
  - name: VictoriaMetrics
    type: prometheus
    access: proxy
    url: ${VM_URL}            # from the environment profile, never hardcoded
    isDefault: true
    jsonData:
      httpMethod: POST
      timeInterval: 30s       # match the scrape interval
  - name: Loki
    type: loki
    access: proxy
    url: ${LOKI_URL}
    jsonData:
      maxLines: 1000
```

Provisioned resources are read-only in the UI. That is the point: a UI edit that
appears to work and is silently reverted at the next reconcile is worse than one
that is refused.

`access: proxy` keeps the backend URL server-side. With `direct`, every browser
needs network access to VictoriaMetrics and Loki, which usually means exposing them
more widely than intended.

## URLs come from the environment profile

Never hardcode an internal endpoint in a dashboard, a datasource file committed to a
public repository, or a document. Use a variable substituted at deploy time, and
keep the value in the environment profile or the deployment's secret store.

`timeInterval` should match the scrape interval. When it does not, Grafana suggests
`rate()` windows that are too short and panels show gaps that look like data loss.

## Datasource UIDs

Reference datasources by a **stable UID** set in the provisioning file, not by name
and not by an auto-generated id. A dashboard exported from one instance and imported
into another with a different generated UID renders every panel empty, and the cause
is not obvious from the UI.

```yaml
    uid: victoriametrics-main
```

Use the same UID across environments so one dashboard file works everywhere.

## Query timeouts and limits

Set a query timeout that is shorter than the browser's patience and longer than a
legitimate heavy query. Too short and normal dashboards fail; too long and one bad
query occupies a backend worker for minutes.

For Loki, `maxLines` bounds what a single query returns. Without it, an
accidentally broad selector pulls a very large result and the browser stops
responding.

## Access

```text
who can view dashboards
who can edit dashboard source (in Git, not in the UI)
who can create datasources
who can silence alerts
```

Silencing deserves explicit thought: an alert silenced indefinitely by someone who
then leaves the team is indistinguishable from an alert that never fires.

## Verification

```text
each datasource's health check passes from the Grafana instance
a trivial query returns data through each datasource
the datasource UID matches the one dashboards reference
no credential or internal URL is committed to a public repository
UI editing of provisioned resources is refused
