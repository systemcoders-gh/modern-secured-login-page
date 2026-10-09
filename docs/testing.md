# Testing guide

Use synthetic identities and a disposable test database. Django's test runner creates its own database; do not point tests at a production URL or reuse real credentials. All current execution outcomes, counts, failures, skips, and browser screenshots are recorded separately in [verification.md](verification.md).

## Practical test pyramid

| Level | Highest-value behavior |
| --- | --- |
| Model/unit | Email normalization/uniqueness, password validation, encrypted serialization, recovery-code hashing and atomic consumption |
| Django integration/security | Register→verify→login; generic recovery; token expiration/reuse; session revocation; CSRF; ownership; rate limits; MFA stages, replay, and recovery; production settings fail closed |
| Database | Fresh and repeated migrations, case-insensitive uniqueness, PostgreSQL constraints, concurrent recovery-code consumption where the database supports meaningful concurrency |
| Browser | Real forms/email flow, MFA/settings/session journeys, desktop/mobile/dark mode, keyboard/focus/errors, console issues |
| Staging/operations | TLS/proxy identity, distributed Redis abuse limits, SMTP delivery/timing, backups/restores, realistic capacity, monitoring, rollback |

There are no POS, financial, inventory, license, or multi-client customer workflows in this app. Adding empty tests for them would not add evidence. Tests should exercise business outcomes and failure conditions instead of mirroring implementation details or chasing coverage percentages.

## Local commands

Use `.venv\Scripts\python.exe` on Windows or `.venv/bin/python` on Linux/macOS. After installing `requirements-dev.txt` with `--require-hashes`, run:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
$env:SKIP_BROWSER_TESTS = '1'
.\.venv\Scripts\python.exe manage.py test tests --verbosity 2
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m bandit -r accounts config -x accounts/migrations
.\.venv\Scripts\python.exe -m pip_audit -r requirements.txt --no-deps --disable-pip
.\.venv\Scripts\python.exe scripts/check_secrets.py
```

Bandit is a static heuristic; review findings with context. `pip-audit` queries advisory sources and can fail due to network limits. Such a failure is unverified audit coverage, not a clean result. The secret script reports only path/line/rule, supports exact staged bytes and reachable history, and cannot detect every secret. Review stage contents manually; never print a suspicious value. A deliberate synthetic fixture may carry `# secret-scan: synthetic fixture` on its line, but real values must never be exempted.

```powershell
.\.venv\Scripts\python.exe scripts/check_secrets.py --staged
.\.venv\Scripts\python.exe scripts/check_secrets.py --history
.\.venv\Scripts\python.exe -m playwright install chromium
$env:SKIP_BROWSER_TESTS = '0'
.\.venv\Scripts\python.exe manage.py test tests.test_browser --verbosity 2
```

On Linux CI, Playwright's `install --with-deps chromium` also installs system browser dependencies on the disposable runner. Do not silently install those on a production server. Browser logs/screenshots must use synthetic data and exclude active MFA/recovery secrets. `SKIP_BROWSER_TESTS=1` intentionally skips the browser module in the general suite; run it explicitly with `0` before claiming browser coverage.

## PostgreSQL and production checks

Use a separately created local/staging PostgreSQL database and a role able to create the disposable Django test database. Supply `DATABASE_URL` through the environment/secret store, never as a printed shell command containing a real password. The GitHub workflow provides a disposable PostgreSQL 17 service and Redis service with synthetic credentials.

With the full production configuration loaded securely:

```powershell
.\.venv\Scripts\python.exe manage.py check --deploy --fail-level WARNING
```

This validates configuration, not an actual HTTPS endpoint or SMTP delivery. Conservative `HSTS_INCLUDE_SUBDOMAINS=0` and `HSTS_PRELOAD=0` defaults produce expected `security.W005`/`security.W021` warnings and make `--fail-level WARNING` exit unsuccessfully. The owner must review the real domain's policy; do not silently enable subdomain-wide HSTS/preload. CI uses both flags enabled for its synthetic example domain. Do not point `migrate` or `test` at production during bootstrap. Verify a matched backup restores in isolated staging before a real migration is approved.

## Browser and accessibility review

Check at least 360px, 390px, 768px, and 1440px widths, document the actual widths executed, and review both themes and reduced motion. Verify no horizontal overflow, visible focus, labels/aria associations, error focus and announcements, keyboard navigation, usable controls, and real loading/disabled states. Verify actual form POST/CSRF behavior with the configured `strict-origin` referrer policy; a successful page GET or Django test-client POST does not prove browser-origin behavior. Measure any contrast or 44px target claims using computed styles/layout; screenshots alone do not prove them. Manual screen-reader and zoom testing remain separate gates.

## CI and release evidence

The workflow uses hash-enforced dependencies and pinned official actions, read-only repository permission, ephemeral GitHub-hosted runners, SQLite and PostgreSQL suites, browser journeys, production checks, and a non-root container build. There is no deploy step. Cache keys depend on the lockfile, and cached packages still undergo hash verification. Provider credentials are not available to PR jobs.

A workflow file existing locally is not proof it has run. Record the repository/commit, hosted job URL, exact successful/failed/skipped status, and artifact limits after the private repository is created. Stop on auth/security failures; do not suppress them to publish. Network advisory failures and unavailable PostgreSQL/Docker/browser runtimes must remain explicit in the release report.
