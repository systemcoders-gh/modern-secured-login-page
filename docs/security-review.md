# Non-destructive security review and threat model

Date: 2026-10-09. Scope: standalone source/configuration design and synthetic local regression evidence. No live penetration testing, credential disclosure, production inspection, or customer data access is authorized. See [verification.md](verification.md) for executed checks, outcomes, and coverage limitations.

## Assets and trust boundaries

Assets are account identity, verified-mailbox state, password hashes, TOTP secrets, single-use recovery codes, authenticated sessions, private security events, application/signing/encryption keys, and dependency/release artifacts. Boundaries are browser→application; TLS proxy→application; application→database/cache; application→SMTP; CI/contributor→release; and installation→backup storage.

Attackers include unauthenticated abusers, an authenticated account trying to modify another account, a stolen-cookie attacker, a mailbox attacker, an attacker who steals a database backup, and a malicious contributor/dependency. A compromised runtime with access to encryption keys is stronger than a database-only attacker and is not defeated by encrypting the database payload.

| Threat | Source control / safe verification |
| --- | --- |
| Credential stuffing, account guessing, mail floods | Allauth IP/key/user cooldowns in `config/settings.py`; generic responses; test configured limits with synthetic emails and isolated cache |
| Duplicate identity / account ownership abuse | Normalization and `Lower(email)` database uniqueness in `accounts/models.py`; scoped settings/sessions queries; test mixed-case and concurrent duplicates and user A/B ownership |
| MFA bypass, TOTP replay, recovery reuse | Allauth stage handling plus `accounts/mfa.py`; TOTP tolerance/replay checks; hashed code conditional update in `accounts/recovery.py`; test partial login, replay, duplicate consumption, and regeneration |
| Database-only session/TOTP disclosure | `accounts/sessions.py` encrypted serializer and `accounts/mfa.py` MultiFernet; assert stored records omit plaintext synthetic markers |
| Reset/verification token abuse | Framework tokens, configured trusted origin and expiration, POST confirmation, no automatic reset login; test expiry, reuse, hostile Host/next, and owner notification |
| CSRF/XSS/SQL injection/open redirect | CSRF middleware, escaping, ORM, allauth redirect validation, ownership checks; test actual state-changing routes and hostile input without attacking a live host |
| Session fixation/stolen session | Framework session rotation, bounded lifetime, revocation after security changes, fresh authentication; test two independent clients and post-reset access |
| Clickjacking/token referrer/log disclosure | CSP/strict-origin/frame/no-store headers in `accounts/middleware.py`; the referrer omits token paths while retaining origin; redacted auth URL logging and disabled server access logs; assert headers/log values with synthetic tokens and real browser POSTs |
| Unsafe upload/path traversal/SSRF/webhook | No upload, fetch-URL, payment, webhook, command-execution, or public API features are exposed; review future additions separately |
| Supply-chain/publication exposure | Hash locks, official pinned actions, source/staged/history scanner and human review; inspect lock changes and CI permissions before release |

Absence of a feature reduces its attack surface; it does not prove every dependency is free from the corresponding vulnerability class.

## Findings and deployment gates

The following distinguishes confirmed source design/limitations from risks requiring a real deployment to evaluate. A risk severity is not a claim that a live vulnerability was exploited. No unresolved Critical source vulnerability is asserted by this report. That is not an exhaustive assurance.

| ID / severity / status | Evidence | Impact and likelihood | Recommended fix / safe verification |
| --- | --- | --- | --- |
| H-01 High — deployment gate | `config/settings.py` requires production keys, PostgreSQL, Redis, SMTP and HTTPS. No real host/configuration has been qualified. | Incorrect proxy/cache/secret permissions can expose sessions or weaken abuse protection; likelihood unknown until deployment review. | Isolated staging review of exact host/proxy hops, service permissions/TLS/cache sharing, and secrets storage; run deployment checks and synthetic end-to-end journeys. |
| H-02 High — operational gate | TOTP and session encryption depend on external Fernet keys (`accounts/mfa.py`, `accounts/sessions.py`); no managed backup/rotation procedure has been executed here. | Key loss can make enrolled MFA unreadable; key theft plus database theft defeats at-rest protection; operational likelihood depends on host policy. | Separate encrypted key and database backups, least privilege, verified restore, reviewed retained-key rotation. Test with synthetic restored data and retain old decrypt keys until complete. |
| M-01 Medium — confirmed limitation | File/SMTP backends in `config/settings.py`; synchronous sending, no queue, no real provider timing evidence. | Worker blocking and subtle account-response timing differences under network/provider variation remain possible. | Measure known/unknown recovery/resend/login timing and mail limits in staging. If warranted add a reviewed async mail design with generic enqueue behavior, retries and privacy controls. |
| M-02 Medium — performance gate | `accounts/recovery.py` checks salted hashes among up to ten unused codes; Argon2 is intentionally expensive. | MFA recovery attempts consume CPU, affecting availability under load; request throttles limit but do not eliminate cost. | Benchmark valid/invalid TOTP/recovery/reauthentication under synthetic load with realistic ingress and shared Redis. Do not weaken hashing or remove limits. |
| L-01 Low — confirmed operational gap | `SecurityEvent` stores minimal kind/time/user reference; no retention schedule, external alert routing, or centralized sink is configured. | Unbounded retention consumes disk; unconfigured alerting delays detection. Likelihood grows with production use. | Agree data minimization/retention, add reviewed pruning/monitoring with scoped permissions, and prove no secrets reach log/artifacts. |
| I-01 Informational — validation gap | Local browser/static tests are bounded; no independent penetration test/full assistive-technology audit or production restore/capacity evidence is implied. | Overstated readiness can lead to unsafe adaptation. | Preserve honest verification report; independently review before real account hosting. |

If a test or static scanner discovers a source defect, the coordinator must record severity, path/line, impact, likelihood, fix, and regression outcome, preserving the original failure disposition. Do not quietly relabel a failed gate as passed.

Final integration reviewed password reset/change during incomplete MFA and email-verification stages. The adapter binds the initial proof to the original credential hash and rechecks current user state before final login. These regressions passed in the combined local suite; see `verification.md` for scope and remaining deployment gates.

## Review coverage and boundaries

Review authentication/authorization, Argon2/password/session handling, CSRF/escaping/ORM, MFA/recovery, host/origin/redirect validation, cache limits, logging, dependency locks, and deployment startup guards. Manual review and automated heuristics complement each other; neither proves universal safety. The repository scanner checks common patterns and forbidden runtime/key/database files without printing values, and history mode examines reachable Git blobs. Provider-specific secrets and unreachable Git objects may still require specialist review before public release.

There is no InfoBusiness licensing, tenant-domain database, stock/financial transaction, payment signature, upload, API, or notification-provider integration here. No finding about those external systems is justified from this codebase. Any later integration needs a scoped threat model, behavior/security tests, and separate live approval.

## Sources used for configuration review

The design follows the [Django deployment checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/), [allauth account configuration](https://docs.allauth.org/en/latest/account/configuration.html), [allauth MFA configuration](https://docs.allauth.org/en/latest/mfa/configuration.html), and [GitHub Actions security hardening guidance](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions). Their presence does not establish that a deployed environment satisfies the guidance.
