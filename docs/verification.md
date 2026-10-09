# Implementation and verification evidence

Date: 2026-10-09. Project: Modern Secured Login Page, System Coders.

The initial workspace was empty, with no source, database, configuration, or Git repository. The pasted Django application brief is the implementation scope. No InfoBusiness repository, production domain, client data, DNS, license, or deployment was changed.

## Executed local checks

| Check | Command / result |
| --- | --- |
| Python runtime | Project virtual environment: Python 3.13.13 |
| Django / authentication | Django 5.2.18, django-allauth 65.19.7 installed from PyPI |
| Dependency reproduction | `pip-compile --generate-hashes --allow-unsafe --strip-extras` for both input files; `python -m pip install --require-hashes -r requirements-dev.txt` succeeded |
| Dependency compatibility | `python -m pip check`: no broken requirements |
| Local schema | `python manage.py makemigrations accounts`; `python manage.py migrate --noinput`: initial application/framework migrations applied to the new ignored local SQLite database |
| Migration drift | `python manage.py makemigrations --check --dry-run`: no changes detected |
| Django checks | `python manage.py check`: zero issues |
| Backend/security suite | `SKIP_BROWSER_TESTS=1 python manage.py test tests --verbosity 1`: 60 discovered, **56 passed**, 4 browser cases intentionally skipped, 21.280 seconds |
| Browser suite | `SKIP_BROWSER_TESTS=0 SAVE_SCREENSHOTS=1 python manage.py test tests.test_browser --verbosity 1`: **4/4 passed**, 17.086 seconds, official Playwright Chromium 153.0.8010.12 |
| Responsive visual review | 28 layout checks: login in both themes at 320/375/768/1440px; five additional public screens at those widths. No horizontal overflow or console/page errors. Cached Chromium 149.0.7827.55 used for that separate visual pass |
| Accessibility checks | Labels, main landmark, keyboard skip link, password visibility, theme persistence and reduced motion tested. Theme toggle 44 x 44px; password toggle 49.28 x 44px. Full manual WCAG/assistive-technology qualification remains open |
| Production configuration | Ephemeral synthetic keys, fake PostgreSQL/Redis/SMTP endpoints and exact HTTPS host: `check --deploy --fail-level WARNING` passed with synthetic HSTS subdomain/preload flags enabled; this command makes no service connection |
| Production default HSTS policy | Strict check with optional subdomain/preload flags off reports expected W005/W021 and exits nonzero. Real owner opt-in is required; no live domain was enrolled |
| Static files | `python manage.py collectstatic --noinput`: local assets collected. Separate synthetic production collectstatic produced a manifest |
| Ruff | `python -m ruff check .`; `python -m ruff format --check .`: passed at local review |
| Bandit | `python -m bandit -r accounts config -x accounts/migrations`: no unsuppressed findings. Four B105 heuristics on form import/rate-limit strings reviewed and narrowly annotated; no global rule disabled |
| Runtime advisory audit | `python -m pip_audit -r requirements.txt --no-deps --disable-pip --cache-dir .tmp/audit`: no known vulnerabilities found |
| Development advisory audit | Equivalent audit of `requirements-dev.txt`: no known vulnerabilities found; sandbox network/cache restrictions on the first attempt were resolved by approved execution |
| Secret patterns | `python scripts/check_secrets.py`: passed. Source/staged/history coverage is recorded separately when Git preparation completes; this pattern scan is not universal secret assurance |
| Email templates | Three plain-text/HTML verification/reset variants compiled and rendered with synthetic adapter context; real SMTP delivery is not tested |

## Behaviors exercised

Real routes cover registration, normalized/unique email, generic duplicate completion, verification POST/expiry/reuse, resend limits, correct/incorrect login, unknown-user generic messages, session rotation and bounded remember-me, long Unicode passwords and weak-password rejection, profile ownership, recovery request/token expiry/reuse, reset notifications and full-session invalidation, password changes, sibling-session revocation, freshness for email/security actions, TOTP enrollment/activation/deactivation/challenge/replay, recovery hashing/show-once/regeneration/reuse/user isolation, pending MFA/email stages invalidated after credential changes, encrypted pending enrollment/session/TOTP storage, key rotation, CSRF, XSS escaping, hostile login input, external redirect rejection, proxy trust defaults, rate cooldowns, CSP/cookies/referrers, and production startup guards.

Four browser journeys cover registration through verification/login/reset, MFA setup and recovery login/session revocation/reused-code rejection, responsive themes/keyboard/labels/motion/targets, and unauthenticated access/incorrect credentials/CSRF rejection. Screenshot artifacts contain only anonymous pages or disposable synthetic account identity, never raw MFA/recovery keys or active tokens.

## Failures found and resolved

1. Independent review found missing allauth fresh-authentication enforcement on email management. Enabled it and proved stale sessions cannot add a recovery email.
2. Review found that partial password-to-MFA sessions are anonymous and absent from session tracking, so deleting authenticated sessions alone did not invalidate them after reset. Bound staged authentication to the original credential hash and checked fresh database state before login. Reset/change and verification-boundary regressions pass.
3. Disabled local debug tracebacks by default, redacted all POST parameters for error reporting, and marked sensitive MFA/recovery local variables.
4. Chromium sent `Origin: null` on POST forms with `no-referrer`; CSRF rejected the requests. `strict-origin` omits token paths/query while preserving origin checks; actual browser registration/reset/MFA now pass.
5. Fixed 44px controls and mobile recovery-code wrapping. Browser harness fixes included Playwright event-loop/ORM lifetime, Windows media-path handling, and selectors matching actual button/link labels. Early harness failures were not successful test runs.
6. Initial virtual-environment/browser/audit attempts met Windows sandbox temporary-directory, subprocess-pipe, or network restrictions. Approved isolated execution completed the required local work; no production credentials were used.

## External publication and remaining qualification

The GitHub connector confirmed the authenticated identity `systemcoders-gh`. Automatic approval review initially rejected inspection of the authenticated browser session; the owner then explicitly authorized creating and pushing only the private `systemcoders-gh/modern-secured-login-page` repository. GitHub creation succeeded on 2026-10-09; the repository page and connector metadata both confirmed private visibility (repository ID 1412275704). The initial staged-byte secret scan passed for 113 files/blobs, and `git diff --cached --check` passed. Push, history and hosted CI evidence will be recorded after they complete. Public visibility still requires separate final approval.

Not qualified by local passes: real SMTP delivery/timing, multiworker Redis rate/replay behavior, PostgreSQL concurrency, Docker runtime, production TLS/proxy/permissions, backup/key restoration and rollback rehearsal, load/capacity, independent human security review, full screen-reader/zoom accessibility. Hosted CI service/browser/container checks may narrow those gaps, but do not qualify a real production installation.

## Screenshots

- [Desktop login](screenshots/login-desktop.png)
- [Mobile login](screenshots/login-mobile.png)
- [Synthetic dashboard](screenshots/dashboard-desktop.png)
