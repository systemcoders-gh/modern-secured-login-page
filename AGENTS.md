# Project instructions

## Scope and architecture

This repository is Modern Secured Login Page, an independent Django authentication teaching application owned by System Coders. It is not InfoBusiness. Read the actual code and [docs/architecture.md](docs/architecture.md) before making architectural claims. Use `accounts` for user/security behavior, `config` for settings/routing/middleware, shared Django templates/static assets for UI, and `tests` for behavior regressions. Preserve Django/allauth authentication; do not add alternate login paths or home-grown cryptographic primitives.

## Safety boundaries

- Local, reversible source/documentation/test improvements are allowed within the user's scope. Production deployment, DNS, credential rotation, real databases, customer records, costly services, destructive changes, and public repository visibility require explicit user approval.
- Never display, copy, commit, attach, or transmit secrets or real user data. Use synthetic accounts. `.env`, `.local`, databases, mail files, tokens, private keys, and test artifacts stay untracked.
- Preserve identity, passwords, MFA enrollment, recovery-code state, session policy, and account configuration across compatible upgrades. Back up and prove restore before risky migrations.
- Initial GitHub destination must be the separate private `systemcoders-gh/modern-secured-login-page` repository. Do not change any other repository or widen its permissions. Stage an audited file allowlist; scan staged bytes and all history before publishing.
- Explain a new dependency/integration's purpose, trust/maintenance evidence, permissions, overlap, and removal plan before adding it. Reuse existing tooling; no silent plugin installations or production tokens.

## Implementation standards

Use Python 3.13, Django 5.2 LTS, type hints where they clarify contracts, snake_case modules/functions, PascalCase classes, Django ORM, Ruff formatting, and named routes. Avoid raw SQL, unsafe template HTML, inline script exemptions, password complexity rules, and frontend-only authorization. Normalize email on every write and retain the database uniqueness constraint. Keep state changes behind POST, CSRF, ownership checks, and fresh authentication where sensitive.

Keep external APIs disabled unless requested. URL/status behavior and existing account/session rules are compatibility contracts; changes need documented callers, migration or deprecation plans, and regressions. UI must retain semantic labels, meaningful focus, keyboard operation, accessible errors, reduced-motion support, readable contrast, and usable mobile layouts. Verify measured claims rather than asserting complete accessibility from a screenshot.

Do not weaken rate limits, production validation, CSP, cookie protection, MFA replay protection, or ownership checks to make a test pass. Keep production throttling on shared Redis. Sensitive values must not enter request logs, audit-event details, traces, screenshots, or CI artifacts.

## Delivery workflow

Use scoped `feature/`, `fix/`, or `docs/` branches; use `feat:`, `fix:`, `test:`, `docs:`, `chore:`, or `security:` commit subjects. No direct unreviewed production release. PRs explain the user-visible problem, final behavior, tests, compatibility/data impact, and rollout/rollback needs. Architectural changes add an ADR in [docs/decisions.md](docs/decisions.md).

Agents receive disjoint file ownership and a contract before editing. One coordinator integrates changes, resolves conflicts, and reruns affected checks. Read-only review/testing can run in parallel. Do not run migrations on another agent's database or change shared dependencies without coordinating. The role/handoff table is in [docs/engineering-bootstrap.md](docs/engineering-bootstrap.md#engineering-roles-and-handoffs).

## Verification and definition of done

Run proportionate behavior/security tests, Django checks, migration drift detection, Ruff, Bandit, dependency auditing, secret scanning, and browser checks for UI/auth journeys. Use disposable/synthetic databases only. Record exact commands, outcomes, skips, and environmental limits in [docs/verification.md](docs/verification.md). No meaningless tests for coverage counts; test behavior, failure states, ownership, reuse/replay, and concurrency where relevant.

Done means requested behavior works end to end; negative paths and data safety pass; migrations are version controlled and rerunnable/protected; documentation matches code; source and history are safe to publish; a human reviewer can assess changes; and unresolved gates are explicit. AI-generated code receives the same correctness, security, maintainability, dependency, backward compatibility, and data-preservation review as human code. Never claim a tool was installed or hosted CI/deployment passed without evidence.

## Database and release rules

Review every migration's preconditions, lock/write impact, verification, backup, and rollback compatibility. Prefer expand-and-contract; destructive schema/data operations need explicit approval. The custom user model is established from the first migration. SQLite is local; production uses PostgreSQL. Never use production credentials in tests or reset the local database to hide a migration defect.

Run the documented release checklist and production checks before an approved staging/production rollout. Keep secrets/state outside release artifacts, serialize releases with a deployment lock, prove the backup restores, canary one installation, pause on failure, and retain the matched code/data rollback. [docs/deployment.md](docs/deployment.md) and [docs/operations.md](docs/operations.md) define procedures. This bootstrap does not authorize deployment.
