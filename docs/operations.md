# Operations, backup, rollback, and incident response

These procedures are proposed for an approved deployment. No monitoring service, schedule, backup job, alert destination, or production access is configured during local bootstrap.

## Observability baseline

Use metrics and redacted events, avoiding authentication query strings, full URLs containing tokens, email bodies, passwords, cookies, codes, and authenticator secrets. Access logs from Gunicorn are disabled in the image; configure the trusted proxy to log route categories/status/latency with sensitive paths redacted rather than raw request URLs. Error tracking needs explicit privacy review before an integration is added.

| Signal / initial objective | Initial actionable alert | First response |
| --- | --- | --- |
| Availability: 99.9% monthly as a proposed SLO | 3 successive failures from independent health probes | Check proxy/TLS, app worker, DB/cache connectivity, last release |
| Login/reset page latency | p95 above measured baseline by 2× for 10 minutes | Check Argon2 CPU, worker queue, DB and SMTP latency |
| HTTP 5xx | >1% for 5 minutes with enough requests to avoid low-volume noise | Group redacted exception type; correlate release and service errors |
| Database latency/locks | Sustained latency above staging baseline or blocked writes | Inspect connection/lock metrics with read-only access |
| Redis rate-limit state | Cache unavailable or eviction rises | Restore isolated Redis; assess abuse exposure; do not disable limits |
| SMTP delivery | Sustained send failure, expired verified sender, or queue/provider incident | Check provider health/credentials privately; preserve generic public errors |
| Login failures / MFA replay | Sudden aggregate spike, not every individual bad password | Assess source patterns using minimised metadata; tune ingress controls |
| Backup success and restore | Backup older than approved RPO, or restore rehearsal fails | Pause risky releases; restore backup process and prove integrity |
| Disk | >80% warning / >90% urgent after baseline review | Inspect owned paths; preserve DB/backups/keys; no wildcard deletion |
| CPU/memory | Sustained saturation for 10 minutes | Check hasher/worker load and process limits before tuning |
| Deployments | Failed cutover/health/version check | Stop batches, preserve evidence, choose rollback/forward fix |
| Security events | Owner-reported unauthorized settings/session action or suspicious event gap | Contain affected account/runtime, preserve minimal evidence |

Targets are starting proposals, not measured service guarantees. Set thresholds after staging baselines and traffic review. Payment/webhook, inventory, license, and background-job alerts do not apply because those subsystems are absent. Do not add alert noise for nonexistent features.

The public `/health/` endpoint checks database and configured cache availability without user/configuration details. Treat it as a limited readiness check and independently probe a permitted synthetic authentication journey. An HTTP 200 alone does not prove complete authentication or mail delivery.

## Backup and restore

Decide and approve RPO/RTO before hosting real accounts; an initial proposal is RPO 24 hours and RTO 4 hours, tightened if usage warrants. Back up PostgreSQL with a consistent dump/snapshot, application configuration references, migration/version metadata, and encryption/signing keys in separately encrypted access-controlled storage. Redis throttle state is operational state, not the account system of record. Keep backups outside public paths and release artifacts.

For local SQLite learning backups, stop the local app or use SQLite's online backup API for a consistent copy. Do not copy a live database file without accounting for its journaling mode. Local keys and database must stay matched. Never share these backups as test fixtures.

Restore rehearsal: create an isolated network/database with no outbound real email; restore the snapshot and matched config/keys; validate migrations and constraints; run synthetic auth/reset/MFA/session checks; compare expected record counts/hashes without displaying real content; measure restore time; record evidence; dispose only the explicitly owned rehearsal state. Do not declare backup readiness from creation alone.

## Migration rules

Every migration is committed, has reviewed preconditions, version compatibility, lock/write/disk impact, rollback/forward-fix plan, and verification. Prefer additive schema changes and staged expand-and-contract. Run against restored staging first. Destructive changes/data corrections require explicit approval; corrections need an auditable count/reason and must not include raw sensitive records in logs. Migrations must rerun safely or rely on Django migration tracking; do not bypass that tracking to hide failure.

Use short transactions around one-time code consumption and security state updates. Preserve the database email-uniqueness constraint under concurrency. Measure database contention before adding worker concurrency. Stock, financial posting, reconciliation, and POS transactional boundaries belong to InfoBusiness and cannot be inferred from this repository.

## Rollback

Retain the prior reviewed artifact plus matching database/config/key backup. Obtain approval for any production data restore. For schema-compatible releases, revert the application artifact atomically under the deployment lock and verify health/auth paths. For incompatible schema or partial migration failure, stop writes, assess forward repair, and restore a matched snapshot only after accounting for all writes since backup. Never reopen a partially migrated installation as though the upgrade succeeded.

Record the failed version, disposition, exact installation, backup identity, selected recovery path, verification, and observed downtime. Preserve historical failures and evidence. Resume a rollout only after reviewing the cause and obtaining approval for any changed risk/scope.

## Incident runbooks

**Account abuse:** investigate events owned by the affected account; do not expose them to other users. Revoke affected sessions through reviewed mechanisms, require fresh authentication, and coordinate password/MFA changes. Never bypass MFA by removing enrollment as a convenience.

**Suspected secret exposure:** contain the exact scope, revoke/rotate through owner-approved provider procedures, review history/artifacts privately, and assess key/session exposure. Do not paste the value into a report. Fernet rotation needs retained old decrypt keys, a reviewed re-encryption process, and restore validation. Credential rotation is not authorized by this local bootstrap.

**SMTP outage:** public recovery messages remain generic. Inspect provider failures without capturing mail bodies or tokens. Communicate recovery availability through an approved channel. Revalidate sender/domain delivery settings after repair.

**Application/DB/cache outage:** check recent release and health/connectivity metrics; stop conflicting releases; preserve data and keys; recover the stopped service before reseeding/resetting anything. Use read-only inspection by default. Changes to real services require deployment authorization.

## Troubleshooting locally

- Missing Python/dependencies: confirm the `.venv` interpreter and install the hash lock, not the system Python's packages.
- Missing tables: run local `manage.py migrate`; investigate failed migrations instead of deleting the database.
- Missing/stale static assets: run local `manage.py collectstatic --noinput`; default debug-off mode relies on collected WhiteNoise assets.
- Verification/reset mail absent: check the local file backend and `.local/emails` without copying active links into reports.
- CSRF/host errors: use the configured loopback origin; do not add wildcard origins or disable middleware.
- Browser tests skipped: set `SKIP_BROWSER_TESTS=0`, install Chromium in the development environment, and run the explicit browser module.
- MFA/session decrypt errors: confirm the original keys are present. Replacing `.local/secrets.json` destroys access to previous encrypted state.
- Production startup rejects settings: supply the documented explicit secure values; do not weaken validation to boot.
