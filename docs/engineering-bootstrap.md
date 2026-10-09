# Engineering Bootstrap Report — Modern Secured Login Page

Date: 2026-10-09. The requested generic InfoBusiness engineering bootstrap is adapted to the actual repository and the later attached Modern Secured Login Page implementation request. This report makes no architecture/security claim about an uninspected InfoBusiness installation.

## 1. Executive summary

A new standalone Django authentication demonstration is implemented locally with documented engineering instructions, role handoffs, a threat model, tests, quality/security tooling, CI definitions, and a production-oriented container/deployment plan. The repository was first created and reviewed privately. On 2026-10-09, the owner explicitly approved public visibility for only `systemcoders-gh/modern-secured-login-page`; repository Settings, connector metadata, and an unauthenticated GitHub API read subsequently confirmed public visibility/readability. Production changes remain a separate approval gate. Actual execution and publication status live in [verification.md](verification.md); no successful test or hosted action is inferred merely from a definition existing.

## 2. Detected technology stack

The initial target directory contained no application repository. The attached requirements selected Python/Django, so the new stack is deliberate, not guessed from InfoBusiness. The local `.venv` inspection confirmed Python **3.13.13**, Django **5.2.18**, django-allauth **65.19.7**, Ruff **0.16.10**, Bandit **1.9.4**, pip-audit **2.10.1**, Playwright **1.63.0**, and pip-tools **7.6.2**. Runtime dependency policy/locks are in `requirements.in`/`.txt`; dev equivalents are separate. No Node/framework build chain is needed. SQLite is the local default; PostgreSQL/Redis are the required production design.

## 3. Current architecture

[architecture.md](architecture.md) maps `accounts`, `config`, migrations, templates/static, tests, docs, and CI. Django/allauth own authentication stages; custom extensions enforce normalized user identity, encrypted MFA/session data, hashed single-use recovery, ownership, and security events. Server templates provide a responsive UI. Email uses local files or SMTP. No POS, inventory, purchasing, accounting, license, payment, SMS/WhatsApp, uploads, public API, or cron/queue subsystem is present.

## 4. Existing strengths

Maintained framework flows avoid inventing reset/TOTP primitives. The custom user model precedes the first migration. Database uniqueness complements normalization; ORM/CSRF/escaping remain enabled. Production configuration requires explicit secure values. Local secrets/mail/database are ignored. Documented checks test meaningful behavior and failure conditions, and CI has read-only permissions, no deploy step, hash installs, and pinned official actions. Concrete passing evidence belongs in the verification record.

## 5. Critical risks

The highest-impact remaining risks are deployment misconfiguration, key loss/exposure, unproven backup/restore, SMTP timing/delivery, distributed throttling behavior, and overstated readiness. No unresolved Critical source finding is confirmed in this report. Public release and real hosting must not proceed from local screenshots alone.

## 6. Security findings

[security-review.md](security-review.md) contains assets/boundaries/threats, evidence, severity, impact, likelihood, recommended mitigations, and safe checks. Its High deployment/key-management gates, Medium SMTP/performance gates, Low retention gap, and Informational review limits are explicitly separated from exploited vulnerabilities. Password/MFA/reset/CSRF/authorization/token/session regressions are interpreted through `verification.md`.

Integration review added and verified a guard for password reset/change during incomplete MFA and email-verification stages. Browser evidence also drove `strict-origin` referrer policy after Chromium 153 form POST/CSRF failures under `no-referrer`. HSTS subdomain/preload defaults remain owner-controlled and produce expected `security.W005`/`security.W021` deployment warnings; synthetic CI opts in only for its example domain.

## 7. Testing gaps

The practical pyramid is in [testing.md](testing.md). Local and hosted Linux suites cover only executed scenarios; `verification.md` now records passing disposable PostgreSQL/Redis, browser and container build/UID checks. SMTP delivery and timing, multiworker/concurrency behavior, proxy/TLS behavior, restore drills, capacity, independent security review, full screen-reader/zoom and WCAG qualification remain open. A skipped/browser-unavailable/network-audit check remains skipped/unverified; it must not be described as passed. Business-domain tests for absent InfoBusiness modules are out of scope.

## 8. Deployment gaps

Hosted CI built the image and confirmed its non-root runtime UID; `verification.md` records the bounded result. No live hosting, service account, branch protection, production approval environment, DNS, TLS, installation registry, deployment lock executor, or rollback automation is configured here. Hostinger Python/Django requires a suitable VPS according to [Hostinger's support documentation](https://www.hostinger.com/support/which-programming-languages-and-frameworks-are-supported-at-hostinger/); no existing plan was inspected. See [deployment.md](deployment.md) for approval-gated staging/release steps.

## 9. Database and data-safety findings

Migrations are version controlled. Identity uses normalized email with a database case-insensitive unique constraint. Recovery consumption uses a conditional update to prevent duplicate use; regeneration uses a transaction. SQLite is local, and meaningful PostgreSQL concurrency/lock/restore evidence remains a separate gate. Back up matched database/version/keys outside release artifacts and test restore before risky migrations. No customer data or production credentials belong in local tests. Existing InfoBusiness stock/financial transaction rules cannot be evaluated from this independent app.

## 10. Recommended plugins, skills, and MCP servers

No new MCP/plugin is needed. The environment already exposes file/shell tools, primary-source web lookup, browser control, GitHub repository/PR operations, Codex app coordination, and security-review capabilities. Tool exposure does not prove authentication, account permission, or that broad connectors were used. Reuse project-scoped file commands, read-only repository inspection, and synthetic browser tests. Existing installed skills include development, code review, security, and browser workflows; they can be invoked when relevant without adding duplicates.

| Existing capability / proposal | Purpose and overlap | Security/maintenance/removal |
| --- | --- | --- |
| Git/GitHub tooling | Private source, review, hosted CI; avoids another Git MCP | Limit to this new repository, read-only by default, owner-controlled auth; no tokens in source; revoke the specific credential/integration to remove |
| Official web documentation | Django/allauth/GitHub deployment and security reference | Read-only primary sources; no private code/credentials sent in searches; no new server needed |
| Playwright / browser control | Actual synthetic authentication journeys and layout | Use local target and synthetic data, no production sessions; installed version checked; remove dev package/browser cache through normal tooling when no longer needed |
| Ruff, Bandit, pip-audit, pip-tools | Formatting/static heuristics/advisories/hash locks | Scoped development tooling already installed; advisory lookups disclose package names, not app credentials; reviewed updates, no blanket auto-fixes |
| GitHub Dependabot configuration | Suggest dependency/action/image updates | Official provider, PR review required, no auto-merge or production token; actual enablement depends on repository creation; remove `.github/dependabot.yml` to stop configured updates |
| Repository secret guard | Pattern/path checks for source/index/history | Local, no transmission, values suppressed; not comprehensive; remove `scripts/check_secrets.py` plus CI references only after replacement is reviewed |
| Optional future error tracking | Only if real hosted traffic needs diagnosis | Provider/PII/retention/cost review and approval required; existing logs/metrics first; no SDK/account configured |
| Optional read-only DB inspection | Only for an approved staging diagnosis | Use installation-specific read-only role and avoid user content; current ORM/test runner already covers local DB work; no broad DB MCP installed |

Figma, container/cloud administration, email, issue-management, and observability connectors should not be granted merely because they are available. No Figma project is supplied and no design integration is necessary. New integration proposals must identify official source/current maintenance, exact permissions, why existing tools are insufficient, setup and removal, and owner approval for credentials/cost/production impact.

## 11. Tools successfully configured

The local Python virtual environment contains the versions listed in section 2. Project definitions configure Ruff, Bandit command scope, hash locks, Playwright test entry point, a local secret guard, GitHub CI/Dependabot, and Docker packaging. The repository was created privately, and hosted quality, PostgreSQL/Redis/browser, and container checks passed as recorded in `verification.md`, including final pre-publication run 37973534614 at commit `fdf6c4aa4cb95424a291dc0b49ec08a2c74b40a1`. Public visibility was separately approved and verified on 2026-10-09 through repository Settings, connector metadata, and an unauthenticated API read, retaining repository ID 1412275704. The later publication-status documentation update's commit/push and subsequent CI are not claimed until recorded. A file being present alone is not a successful hosted configuration. No new MCP server/plugin, external monitoring account, scheduled task, or production service was installed by this work.

## 12. Tools requiring approval or credentials

Private GitHub creation/push was explicitly approved and completed using existing authenticated access. On 2026-10-09, the owner separately approved changing only `systemcoders-gh/modern-secured-login-page` to public; the visibility change completed and was verified through repository Settings, connector metadata, and an unauthenticated API read. Staging/production hosting, domain/TLS/SMTP credentials, PostgreSQL/Redis services, observability destinations, managed backups, and any paid service still require owner configuration/approval. Read-only local command discovery found Git/Python/`py`/`rg`, but did not find `gh` or `docker` on PATH; neither was installed. Docker CI built on its disposable hosted runner.

## 13. Files created or modified

Source: `manage.py`, `config/**`, `accounts/**`, migrations, templates, static assets, and tests. Engineering: `AGENTS.md`, `README.md`, `SECURITY.md`, `CONTRIBUTING.md`, `LICENSE`, ignore/environment/dependency/quality files, `scripts/check_secrets.py`, `.github/**`, `Dockerfile`, `.dockerignore`, and `docs/**`. The exact final file inventory/diff and screenshot evidence are recorded in `verification.md`; no original customer application was rewritten.

## 14. Verification commands executed

The command recipes are in `testing.md`; `verification.md` records which commands actually executed and their results. During documentation/tool discovery, the directory/file listing, selected source reads, executable discovery, package-version query, `ruff check scripts/check_secrets.py`, formatting of that script, and its source secret scan were executed. No production, deployment, DNS, data deletion, or credential-rotation command was executed by this work.

## 15. Test results

Use [verification.md](verification.md) as the authoritative result ledger. No counts are duplicated here to avoid stale/conflicting claims. Documentation and definitions do not establish that application tests, hosted CI, PostgreSQL, Docker, or provider workflows passed.

## 16. Remaining failures or uncertainties

Remaining execution failures/unavailable runtimes/publication checks are explicitly listed in `verification.md`. The standing uncertainties are target production host/proxy policy, provider delivery/timing, service capacity, external backup/key permissions/restore, operational retention/monitoring, branch protection/private disclosure settings, and full accessibility qualification. No live endpoint has been qualified.

## 17. Proposed multi-domain deployment architecture

Use one approved immutable artifact and a registry/secret references outside application source, independent database/keys/cache/config per installation, per-installation locking, preflight/backups, explicit migration/maintenance strategy, atomic cutover, health/version/auth smoke, structured dispositions, matched rollback, canary/batches, and pause on first failure. The [deployment guide](deployment.md#proposed-multi-installation-design) describes this proposed executor. It is not implemented or authorized against any existing InfoBusiness domains.

## 18. Prioritized 30-day engineering roadmap

| Period | Work / completion evidence |
| --- | --- |
| Days 1–7 | Maintain reviewed source/history and passing hosted CI/Linux PostgreSQL/Redis/browser/container jobs, retain verified publication evidence, enable required review and private vulnerability reporting |
| Days 8–14 | Owner-approved isolated staging: exact proxy/TLS/cache controls, SMTP delivery/timing, recovery/MFA/session journeys, measured mobile/keyboard/assistive-technology checks |
| Days 15–21 | Prove matched backup/restore and rollback, benchmark Argon2/recovery/SMTP/DB under realistic synthetic load, define RPO/RTO/SLIs/retention and minimal alerts |
| Days 22–30 | Independent security/code review, dependency/license/supply-chain review, finalize honest release notes/limitations; separately evaluate whether an approved live demo is warranted |

Production/multi-domain work is contingent on separate scope/approval, not an automatic extension of this roadmap.

## 19. Five highest-value next actions

1. Resolve and record every remaining local/hosted verification gap at the exact reviewed commit.
2. Maintain review of the public repository's source/history, screenshots, branch protection, and disclosure channel.
3. Qualify approved staging SMTP/TLS/proxy/shared-cache authentication behavior with synthetic accounts.
4. Prove backup/key restore and rollback, then measure realistic authentication/recovery capacity.
5. Complete independent security/accessibility review before real-account hosting; preserve the published reference's explicit limitations.

## 20. Exact next-phase approval requests

- **Public publication — completed:** on 2026-10-09, the owner approved changing only `systemcoders-gh/modern-secured-login-page` from private to public after the private review. The change completed and repository Settings, connector metadata, and an unauthenticated API read verified public visibility/readability with unchanged repository ID 1412275704. No other System Coders repository is involved, and no additional publication approval is requested here.
- **Staging deployment:** approve an exact host/domain/project, runtime/services, credential channel, cost cap, synthetic account scope, and rollback plan. No production data or credentials in tests.
- **Production:** a separate reviewed installation/version/change window approval, verified matched backup/restore, health/smoke criteria, and rollback authority is required.
- **Additional tools:** only if a documented capability gap remains, approve the named official service/package, exact permissions, costs, privacy/retention, and removal procedure.

The publication approval and completed visibility verification are recorded separately from deployment readiness. The remaining requests are future deployment/tool gates, not claims that an application was deployed or instructions to paste credentials into chat.

## Engineering roles and handoffs

The coordinated roles are responsibilities, not a claim that 50 actual agents/accounts were installed. Run parallel agents only for independent, disjoint ownership with a shared contract and coordinator review.

| Role | Responsibility / handoff |
| --- | --- |
| Principal Architect | Own architecture/contracts/ADRs; approve cross-module design before edits |
| Backend Engineer | Own account/adapters/integrations/validation; deliver routes/models/tests to QA |
| Frontend Engineer | Own templates/static/accessibility; deliver real form/route contracts and measured screens |
| Database Engineer | Review constraints, atomic consumption, migrations, locks, backup/restore; no live writes without approval |
| POS/Inventory Domain Specialist | Not active in this auth-only app; review only if actual business integration is scoped |
| QA Automation Engineer | Synthetic failure/ownership/replay/browser tests; report exact failures/skips and reproducible evidence |
| Security Engineer | Threat model, auth/secret/dependency review; return actionable findings with safe regressions |
| DevOps/Release Engineer | CI/artifacts/config/deployment/rollback definitions; separate local, hosted, staging, production evidence |
| Site Reliability Engineer | SLIs, redacted events, recovery/incident policy; no unapproved alert/service credentials |
| Performance Engineer | Benchmark intended hash/DB/mail costs; never infer capacity from functional tests |
| Documentation Engineer | Match guides/report to source/results; avoid invented stack/hosting/provider claims |
| Code Reviewer | Independent correctness/security/data/compatibility/test/accessibility review before merge |

Each task declares owner/files/contracts/read-only versus write scope. No two agents edit the same file concurrently. One coordinator integrates, reviews, and reruns impacted checks; no agent changes shared dependency locks, schema, production state, or publication visibility without coordination and required owner authorization. Failed verification remains visible in the handoff.
