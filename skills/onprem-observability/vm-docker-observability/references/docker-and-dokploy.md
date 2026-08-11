# Docker and Dokploy

## Discovery and labels

Use Docker discovery so targets follow containers automatically, and relabel
metadata into a bounded set:

```text
keep:  compose service name, container name, image repository, host
drop:  container id, image digest, ephemeral hostname, anything id-shaped
```

The container id changes on every restart. Relabeling it into a label starts a new
series for every metric on every deploy, breaks `rate()` across the boundary, and
makes long-range panels unusable. Container **name** from Compose is stable and is
the right identifier.

Keep the image repository, not the mutable tag: `latest` as a label value is
uninformative, and a tag that changes per deploy is churn.

## Reach the exporter internally

Scrape over the internal Docker network, not through a published host port. A
published metrics port is reachable from anywhere the host is, and it makes
collection depend on the host's port mapping surviving every deployment change.

```yaml
services:
  example-service:
    expose:
      - "9000"          # internal network only, not "ports:"
    networks:
      - internal
```

## Restart policy

```yaml
    restart: unless-stopped
```

`restart: always` restarts a container that is failing on a bad configuration
forever, hiding the error. Whatever policy is chosen, collect restart counts:

```text
container restart count      rising means crash-looping
container start timestamp    a fresh value nobody triggered means it restarted
container exit code          distinguishes OOM-kill from application exit
```

An OOM-killed container and a container that exited cleanly look identical in "is
it running", and their causes are completely different.

## Logs

Containers write JSON Lines to stdout; the runtime captures it; Alloy forwards it.
Cap the local log driver so a chatty container cannot fill the host disk:

```yaml
    logging:
      driver: json-file
      options:
        max-size: "50m"
        max-file: "3"
```

Without a cap, the failure is host-wide and takes down every other container.

## Dokploy specifics

Dokploy manages deployment; it does not manage observability. Confirm explicitly:

```text
which internal network the scraper can reach
whether container names are stable across redeploys
where the deployment configuration lives in version control
what happens to volumes on redeploy
whether a redeploy changes the label set the scraper sees
```

If the deployment configuration is only in the Dokploy UI, it is not in version
control, and neither the rollback nor the review has a source of truth. Say so.

## Volumes and persistence

Anything that must survive a redeploy is on a named volume, and the volume is
backed up by someone named. A metrics buffer or a local queue on the container
filesystem is lost on every deploy — usually discovered when the data it held
turns out to have mattered.

## Checklist

```text
discovery uses stable names; no container id or digest in a label
the exporter is reachable on the internal network, not a published port
restart policy stated; restart count, start time and exit code collected
log driver size cap configured
host disk usage monitored with an alert
volumes identified, with an owner for backup
deployment configuration is in version control
