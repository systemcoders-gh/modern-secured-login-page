# Deployment and release guide

This is a plan and local build definition. No production host, database, DNS, mail credential, or customer installation is changed by this guide. Real deployment and public publication require explicit owner approval.

## Target environment

Use Python 3.13 with the locked dependencies, PostgreSQL, protected shared Redis, SMTP, and a controlled HTTPS reverse proxy in front of Gunicorn. Django documents Gunicorn as a WSGI option in [its deployment guide](https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/gunicorn/). Workers, timeouts, database connections, and Argon2 capacity need measurement for the chosen host.

Hostinger's current support documentation places Python/Django on VPS hosting rather than ordinary Web/Cloud plans. A Python-capable VPS is a possible target; no account or hosting plan was verified for this project. See [Hostinger supported technologies](https://www.hostinger.com/support/which-programming-languages-and-frameworks-are-supported-at-hostinger/). Do not assume an InfoBusiness PHP hosting arrangement can run this Django application.

## Environment reference

Keep `.env` private or inject variables using the platform's secure secret store. Never put production values in Git, CI logs, image layers, examples, issue bodies, or command history. Environment variables override the optional `.env` file.

| Variable | Meaning / production requirement |
| --- | --- |
| `APP_ENV` | `production` for production; development uses local defaults |
| `DJANGO_DEBUG` | Default off; production must keep it off; only enable for isolated synthetic debugging |
| `DJANGO_SECRET_KEY` | Strong unique Django signing secret; no committed default |
| `MFA_ENCRYPTION_KEYS` | Comma-separated Fernet keys, newest first; protect separately from DB backups |
| `APP_ORIGIN` | Canonical exact HTTPS origin used for sensitive email URLs |
| `ALLOWED_HOSTS` | Comma-separated explicit hostnames; no wildcard |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated explicit HTTPS origins |
| `DATABASE_URL` | PostgreSQL connection URL, unique installation credentials |
| `REDIS_URL` | Shared protected Redis URL for production rate limiting |
| `EMAIL_BACKEND` | Production: `django.core.mail.backends.smtp.EmailBackend` |
| `EMAIL_HOST`, `EMAIL_PORT` | Approved SMTP host and port |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | SMTP credentials from secure storage, when the provider requires them |
| `EMAIL_USE_TLS` | Enable SMTP STARTTLS for the selected provider (typically `1` on port 587) |
| `EMAIL_USE_SSL` | Alternative SMTP implicit TLS, typically port 465; do not enable both TLS modes |
| `DEFAULT_FROM_EMAIL` | Approved sender address |
| `TRUST_PROXY_HTTPS` | Default `0`; enable only behind a controlled proxy which sanitizes HTTPS headers |
| `ALLAUTH_TRUSTED_PROXY_COUNT` | Default `0`; exact trusted proxy hop count, not guessed from public requests |
| `HSTS_INCLUDE_SUBDOMAINS` | Default off; enable only when every affected subdomain supports HTTPS |
| `HSTS_PRELOAD` | Default off; enable only after the domain owner approves the browser preload commitment |
| `SKIP_BROWSER_TESTS` | Test-only flag; `1` for general suite and `0` for explicit browser suite |

Do not replace keys casually: losing Fernet decrypt keys loses access to encrypted MFA/session material. Generate production secrets through the hosting secret store or a trusted offline mechanism. A single installation must not share keys with other installations.

The host-level HSTS policy is enabled in production, while subdomain-wide policy and preload remain opt-in. With both optional flags off, Django reports `security.W005` and `security.W021`; a strict `check --deploy --fail-level WARNING` exits unsuccessfully for those expected warnings. Review and document the owner-approved policy instead of turning the flags on simply to silence CI. The synthetic CI production profile enables both only for its `example.test` domain, making the strict check useful without committing any real domain to preload.

The application uses `Referrer-Policy: strict-origin`, which excludes the complete path/query of token-bearing URLs while retaining the origin used in browser POST/CSRF validation. A local Chromium 153 journey exposed `Origin: null` and rejected form POSTs under the earlier `no-referrer` policy; final regression evidence is recorded in `verification.md`.

## Local container definition

`Dockerfile` installs the hash-locked runtime requirements, collects manifest/static files with transient build-only keys that are never persisted, and runs Gunicorn as UID/GID 10001. Application source/static files remain owned by root and readable by the runtime user. The image defaults to `APP_ENV=production` and needs securely injected runtime configuration. It does not migrate a database on startup. `.dockerignore` excludes secrets, databases, runtime state, tests, and local artifacts.

For an approved isolated staging environment:

```text
docker build --tag modern-secured-login-page:reviewed-version .
docker run --rm --env-file /secure/path/staging.env modern-secured-login-page:reviewed-version python manage.py check --deploy --fail-level WARNING
```

An `.env` path here is an example; use a protected file outside the source. Do not paste its contents. Bind the application only to an internal network or loopback behind TLS. Pin the release image and base image to reviewed digests before production; the provided Python image tag receives updates and is not an immutable release lock. Container build/runtime verification is only confirmed when recorded in `verification.md`.

## Release checklist

1. Freeze a reviewed commit and hash-lock dependencies. Run quality, security, behavior, browser, migration-drift, and deployment checks; verify the corresponding hosted CI jobs.
2. Review source, exact staged content, and all reachable Git history for secrets and real data. Review third-party licenses/notices. Prepare honest release notes with remaining gates.
3. Build one immutable artifact without state or secrets. Record commit, dependency lock hash, artifact digest, migration list, supported configuration, and rollback compatibility.
4. Validate in isolated staging with synthetic accounts: registration/mail verification, reset/reuse/expiration, MFA/recovery, ownership, sessions, TLS headers, CSP, Redis limits, error handling, and provider delivery.
5. Verify database/key/configuration backup and a restore rehearsal. Review migration preconditions, locks, disk, and compatibility. Obtain exact installation/version approval before real rollout.
6. Acquire an installation deployment lock. Drain requests or use proxy maintenance mode for incompatible migrations; preserve existing configuration, keys, database, and mail/provider settings.
7. Apply only reviewed migrations once under the lock; deploy artifact atomically; verify permissions and static content. Never run a blanket cleanup over persistent directories.
8. Check health, HTTPS, expected version/artifact hash, and synthetic approved smoke workflows. If checks fail, stop the rollout and use the matched rollback procedure.
9. Record each installation's disposition, backup/restore evidence, version, failures, and post-deployment result. Retain immediate rollback and recovery evidence according to policy.

[Django's deployment checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/) supports the deployment checks. `check --deploy` validates settings; it cannot prove the real proxy, SMTP, backups, or capacity are correct.

## Proposed multi-installation design

This application currently has no automated multi-domain deployer. If multiple independent installations are later approved, build one deployment executor with a registry outside the source containing an installation ID, exact origin/host, runtime adapter, secret references, database/cache names, state paths, active artifact, recovery artifact, and health/smoke definitions. Store credential references only; obtain least-privilege short-lived access from the deployment platform.

Each installation keeps its own database, keys, Redis namespace, configuration, credentials, and backups. Separate database credentials must not allow access to sibling installations. This app has no uploaded media, license, payment, inventory, or branding database subsystem; those requirements must be designed only if such features are added. Do not apply this proposed executor to existing InfoBusiness domains without inspecting that repository and receiving separate approval.

The executor should enforce preflight compatibility/disk/permission checks, a per-installation lock, verified pre-deploy backup, maintenance/draining where needed, migration control, atomic artifact cutover, cache handling, health/version/smoke checks, structured per-domain results, and rollback. Canary one installation, then use small batches; stop after the first failure. Database rollback restores a matched snapshot only when approved and when later writes are accounted for. Prefer a forward fix if reverting would lose new valid data.

Onboarding must record owner/approval, host capacity, origin/TLS, database/cache isolation, secret permissions, SMTP sender validation, backup/restore/RPO/RTO, access-log redaction, and acceptance-test evidence. No domains are registered by this bootstrap.

## Private GitHub preparation

The intended destination is the separate private `systemcoders-gh/modern-secured-login-page` repository. If an authenticated, least-privilege connector/CLI is available, the coordinator may prepare that private repository under the user's instruction. No other repository may be changed. A failed/unavailable access check is not evidence of successful publication.

If owner action is needed, use an authenticated GitHub CLI after inspecting `gh auth status` privately. These commands are a fallback for the owner; this documentation does not execute them:

```powershell
gh repo create systemcoders-gh/modern-secured-login-page --private --description 'Django authentication reference by System Coders'
git init -b main
git add -- AGENTS.md README.md SECURITY.md CONTRIBUTING.md LICENSE .gitignore .env.example .dockerignore Dockerfile requirements.in requirements.txt requirements-dev.in requirements-dev.txt pyproject.toml manage.py accounts config templates static tests scripts docs .github
.\.venv\Scripts\python.exe scripts/check_secrets.py --staged
git diff --cached --stat
git commit -m 'feat: add secure Django authentication reference'
.\.venv\Scripts\python.exe scripts/check_secrets.py --history
git remote add origin https://github.com/systemcoders-gh/modern-secured-login-page.git
git push -u origin main
gh repo view systemcoders-gh/modern-secured-login-page --json nameWithOwner,visibility,url
gh run list --repo systemcoders-gh/modern-secured-login-page
```

Only run `git init` for a new directory and `git remote add` if no remote exists; otherwise inspect the exact existing repository first. Audit the allowlist and screenshot content before staging. GitHub Actions execution on a private account may consume included minutes or incur cost; review account policy before manual extra runs. Configure required CI checks, human review, branch protection, private vulnerability reporting, and available secret/dependency alerts after creation. No setting is claimed configured until verified.

Stop after private review. The owner must explicitly approve making **only** `systemcoders-gh/modern-secured-login-page` public after source/history scans, hosted CI, screenshots, and disclosure configuration are reviewed. No automatic visibility-changing command is supplied or executed.
