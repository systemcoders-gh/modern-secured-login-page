# Architecture decisions and coordination log

Date: 2026-10-09. Scope: safe local construction of Modern Secured Login Page; no production changes.

| ID | Decision | Reason and consequence |
| --- | --- | --- |
| ADR-001 | Build a standalone Django 5.2 LTS app using Python 3.13 | The attached specification requires Django; the initial target directory had no existing app to migrate. InfoBusiness remains outside scope. |
| ADR-002 | Delegate established authentication stages to django-allauth | Verification, token flows, reauthentication, and TOTP need maintained server-side behavior. No alternate password-only route may bypass MFA. |
| ADR-003 | Prefer Argon2id; require 15-character minimum without composition rules | Reduces offline password-guessing risk while permitting passphrases/password managers. CPU capacity must be measured before production. |
| ADR-004 | SQLite locally, PostgreSQL and shared Redis in production | A simple learner setup is compatible with explicit production constraints and shared rate-limit state. No claim about live PostgreSQL tests is made without evidence. |
| ADR-005 | Encrypt session payloads/TOTP with Fernet; hash 128-bit one-time recovery codes | Existing maintained cryptography handles encryption; database-only disclosure should not reveal plaintext MFA/session material. Keys must be backed up separately. |
| ADR-006 | Use local semantic templates, CSS, and minimal JavaScript | No frontend package manager, CDN, or extra supply-chain dependency is needed. UI state never proves authentication. |
| ADR-007 | Use file email locally and configured SMTP in production | Demonstrations need no purchased mail service. Real deliverability and synchronous SMTP timing remain staging gates. |
| ADR-008 | Keep GitHub initial visibility private and require final public approval | The owner explicitly requires independent review of code/history/tests before exposing a new educational repository. |
| ADR-009 | Reuse exposed tools and repository quality tooling; install no new MCP/plugin | Broad connector access is unnecessary. New external services require a separate capability/permission review and approval. |
| ADR-010 | Pin official CI actions to inspected release commits | Limits mutable-action supply-chain risk. Dependabot proposes reviewed updates; hosted workflow success still needs evidence. |
| ADR-011 | Use `strict-origin` referrer policy | Chromium 153 form POSTs under the earlier `no-referrer` policy sent `Origin: null` and failed Django CSRF validation. Origin-only referrers retain browser compatibility without leaking verification/reset paths. Final real-browser regression belongs in `verification.md`. |
| ADR-012 | Leave subdomain-wide HSTS and preload off by default | A teaching app cannot assume domain-owner authority over every subdomain/preload. Expected Django deployment warnings are documented; synthetic CI enables the flags only for its test domain. |

## Safe work order

Inspect target and specification → establish contracts/ownership → implement backend and templates independently → integrate → run behavior/security/browser checks → review actual generated code/docs → create/verify private repository when authenticated access permits → stop before public visibility or production deployment. The coordinator records exact outcomes in `verification.md`.

## ADR template

Copy this section for a new decision; avoid creating a separate file for trivial choices.

```text
ADR-NNN: Title
Date / owner / status: proposed | accepted | superseded
Problem and observed evidence:
Constraints and assets to preserve:
Options considered:
Decision and rationale:
Security, data, compatibility, accessibility, performance impact:
Validation and rollback:
Approvals required:
```

Do not rewrite decisions to erase failed tests, rollback, or canceled work. Mark superseded decisions and link the replacement.
