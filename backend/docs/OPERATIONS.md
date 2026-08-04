# Operations Runbook

Practical, followable procedures for running this backend in production.
Written for whoever's on call, not as a policy document.

## Backups

**What's backed up:** everything - MongoDB is the only datastore this
application writes to (see the architecture note in the main README about
why Django's relational `DATABASES` isn't used for app data). Back up
MongoDB and you've backed up the whole application's state.

**Manual backup:**
```bash
./scripts/backup_mongodb.sh                # writes to ./backups/
./scripts/backup_mongodb.sh /mnt/external   # or any directory you choose
```
Produces a single `.tar.gz` you can move anywhere. **Upload it off the
machine it was created on** (S3, GCS, Azure Blob, or even just `scp` to a
second machine) - a backup that lives only on the server it protects
against doesn't protect against that server failing.

**Automated backup:** `k8s/06-backup-cronjob.yaml` runs the same script
daily via a Kubernetes CronJob. It stops short of the actual upload step
since that's provider-specific (AWS/GCP/Azure credentials differ) - fill
in the `aws s3 cp` (or equivalent) line marked in that file for your
provider before relying on it.

**MongoDB Atlas users:** Atlas has its own automated continuous backup
with point-in-time recovery, which is generally a better primary backup
strategy than `mongodump` (no downtime risk, finer recovery granularity).
Treat `mongodump`/this CronJob as a secondary, portable backup you control
independently of Atlas - useful for migrating providers or for an extra
copy outside Atlas's own infrastructure, not as a replacement for Atlas's
built-in backup if you're on a tier that has it.

**Restore:**
```bash
./scripts/restore_mongodb.sh ./backups/ndc_platform-20260703T020000Z.tar.gz
```
Requires typing the database name to confirm - this is a real,
destructive-to-conflicting-data operation, not a dry run.

**Test your restores.** A backup nobody has ever restored from is a
hypothesis, not a backup. Restore into a scratch database
(`MONGO_DB_NAME=ndc_platform_restore_test ./scripts/restore_mongodb.sh
...`) on a schedule (quarterly is a reasonable floor) and confirm the
application actually boots against it.

## Monitoring & error tracking

**Error tracking (Sentry):** set `SENTRY_DSN` (see `.env.example`) and
every unhandled exception - and, at the configured `traces_sample_rate`,
performance data - flows to Sentry automatically via
`sentry_sdk.integrations.django.DjangoIntegration`, wired in
`config/settings.py`. Unset, it's a complete no-op (skipped entirely
under the test suite too, so tests never depend on network access).

**Application logs:** structured to stdout (see the `LOGGING` config in
`config/settings.py`), the standard 12-factor approach - your platform
(Kubernetes, Docker, systemd) captures and ships these; there's no
separate log-shipping agent baked into this codebase to configure. The
`ndc` logger is where this application's own log statements go
(`logger = logging.getLogger("ndc")`, used throughout `apps/*/delivery.py`,
`apps/*/ai_reporting.py`, etc. for the "no-op because unconfigured"
messages) - worth an explicit log-based alert on ERROR-level entries from
that logger if you don't have Sentry wired up yet.

**Health checks:** `GET /api/v1/health/` (unauthenticated) actually pings
MongoDB (`mongoengine.connection.get_db().command("ping")`), not just
confirms the Django process is alive - returns `200` with
`{"status": "ok", "mongodb": true}` when healthy, `503` with
`"status": "degraded"` if the database is unreachable. The Docker
`HEALTHCHECK` and the Kubernetes `readinessProbe`/`livenessProbe` in
`k8s/04-backend.yaml` both point here.

**Metrics:** `GET /metrics` (unauthenticated, standard Prometheus scrape
path - no trailing slash, note the difference from `/api/v1/health/`)
exposes request-rate/latency/error-rate and Python process metrics via
`django-prometheus`, wired in as middleware
(`django_prometheus.middleware.PrometheusBeforeMiddleware`/
`PrometheusAfterMiddleware`, bracketing the whole middleware stack per its
own requirements) and `INSTALLED_APPS`. Point a Prometheus scrape config
at this path; Grafana (or any Prometheus-compatible dashboard) on top of
that gets you request dashboards with no further backend changes needed.

## Scaling notes

- The backend is stateless (JWT auth, no server-side sessions) - the
  `k8s/04-backend.yaml` HorizontalPodAutoscaler already scales 3-10
  replicas on CPU. Increase `maxReplicas` if you outgrow that ceiling.
- MongoDB Atlas scales independently - watch connection count as replicas
  grow (each pod's Django process holds a MongoEngine connection pool).
- Redis is used for the JWT refresh-token blacklist and Django's cache
  backend - both cheap workloads; a single small Redis instance handles
  this comfortably at any scale this platform is likely to reach before
  MongoDB itself becomes the bottleneck.
- The external delivery calls in `apps/messaging/delivery.py` (email/SMS/
  push) and `apps/analytics/ai_reporting.py` (AI summaries) are currently
  **synchronous** - they block the request that triggered them on a
  third-party HTTP round-trip. This is fine at low volume; before it
  becomes a real bottleneck, move them behind a task queue (Celery, RQ,
  Django-Q) rather than trying to out-scale it with more web workers.

## Load testing

`scripts/load_test.py` is a real Locust script (`locust` is already in
`requirements.txt`'s testing section) targeting this platform's actual
highest-load scenario: election-day traffic, where branch executives
across the country submit collation results in a compressed window while
officers repeatedly poll the live summary endpoint. Seed a database
(`python manage.py seed_platform`), point the script's environment
variables (`LOAD_TEST_ELECTION_ID`, `LOAD_TEST_BRANCH_UNIT_ID`, etc. - see
the script's docstring) at real IDs from that data, then:

```bash
locust -f scripts/load_test.py --host http://localhost:8000 \
    --users 200 --spawn-rate 20 --run-time 5m --headless
```

`GET /api/v1/elections/<id>/results/summary/` is the endpoint to watch
first - it aggregates every submission in a subtree on every call with no
caching layer. If response times degrade under load, that's where to add
a short-TTL Redis cache (invalidated on new submissions) or a
precomputed/materialized rollup before reaching for more web workers.
**Never point this script at a production database** without a clear
maintenance window and a fresh, tested backup - it generates real writes.

## Security

- Rotate `SECRET_KEY` and `JWT_SECRET` on a schedule and immediately on
  suspected compromise; rotating `JWT_SECRET` invalidates every
  outstanding access/refresh token, so plan for a mass re-login.
- `DEBUG=False` in production enables HSTS, secure cookies, and SSL
  redirect automatically (see `config/settings.py`) - don't override
  these individually without understanding why.
- Third-party credentials (Twilio, FCM, Anthropic, SMTP, Sentry) belong in
  your platform's secret manager, injected as environment variables (see
  `k8s/02-secret.template.yaml`) - never committed, never baked into the
  image.
- A dedicated penetration test is out of scope for this document (and for
  this codebase to self-certify) - commission one before handling real
  election data at scale, particularly around the authentication,
  election voting, and result-collation endpoints given what's at stake
  if any of those are compromised.
