# Security policy

Modern Secured Login Page is an educational reference implementation. Security depends on the application, supported dependency versions, TLS/proxy configuration, key management, mail provider, database/cache isolation, and operating procedures. A passing local suite is not production certification.

## Report a vulnerability privately

For the intended `systemcoders-gh/modern-secured-login-page` repository, use its **Security → Report a vulnerability** option if the owner has enabled private reporting. If that option is unavailable, contact the maintainer through [System Coders](https://systemcoders.net) and request a private reporting channel before sharing sensitive details. No security mailbox or response SLA is assumed here.

Include affected commit/version, component, impact, minimal steps with synthetic accounts, and suggested mitigation. Do not include passwords, actual tokens, customer data, active reset links, authenticator keys, or working production credentials. Do not run destructive tests against live installations. Coordinate public disclosure with the maintainer after a fix is available.

## Controls and boundaries

- Django/allauth enforce account verification, authentication stages, reset tokens, and TOTP. The custom user model normalizes email and enforces database uniqueness.
- Argon2id is the preferred password hasher. Minimum password length is 15; common/similar-password validation remains enabled. Password managers, paste, long passphrases, and Unicode are supported.
- Sessions are server-side and encrypted at rest. TOTP secrets use Fernet encryption; keys stay outside the database. Recovery codes carry 128 bits of randomness and are stored as hashes, consumed once, and replaced on regeneration.
- Security changes require recent authentication. Password recovery revokes authenticated sessions and requires a new login while keeping the existing second factor.
- POST/CSRF protection, Django escaping/ORM, account ownership checks, validated hosts/origins, redirect checks, secure cookies, CSP, frame restrictions, and `strict-origin` referrer policy provide layered protection. The referrer contains only the origin, excluding reset/verification token paths; preserving origin also supports real browser POST/CSRF validation.
- Rate limiting covers sensitive allauth endpoints. Production requires shared Redis; local cache behavior is for learning, not multi-worker abuse protection.
- Security events omit passwords, codes, raw tokens, session identifiers, and authenticator secrets. Restrict database/log access and set retention appropriate to the deployment.

The design/threat model and unresolved deployment gates are in [docs/security-review.md](docs/security-review.md). Exact tested controls and failures are recorded in [docs/verification.md](docs/verification.md).

## Safe local use

Use synthetic accounts and bind the development server to loopback. `.local/emails/` contains active verification/reset links, and `.local/secrets.json` protects local encrypted state. Keep both private. Do not copy real production databases or keys into this project. Removing/replacing encryption keys can make enrolled MFA secrets and sessions unreadable; preserve them with separately protected backups.

## Production prerequisites

Use a supported Python and patched locked dependencies, HTTPS, explicit hosts, PostgreSQL, protected shared Redis, SMTP, least-privilege services, verified backup/restore, monitoring, and owner-approved deployment. Never trust client-supplied forwarded headers unless a controlled proxy strips and replaces them. Do not expose the application server directly to the internet behind such a proxy.

Production HSTS protects the configured host. `HSTS_INCLUDE_SUBDOMAINS` and `HSTS_PRELOAD` default off because applying policy to every subdomain or submitting a preload commitment needs an explicit domain-owner decision. Django's deployment checker emits `security.W005`/`security.W021` for those conservative defaults, and `--fail-level WARNING` therefore exits unsuccessfully until the warnings are reviewed or the owner approves the corresponding settings. The synthetic CI profile opts into both flags only for its example domain.

Key rotation is an operational change requiring approval. Add the new Fernet key first while retaining old decrypt keys, validate on a restored synthetic/staging database, re-encrypt stored data through a reviewed migration, and only remove old keys after verification and backup-retention review. This project does not automatically rotate or export keys.

## Known limits

No independent penetration test, production capacity qualification, or full WCAG audit is implied. Local email generation does not verify SMTP delivery, anti-spam/DKIM/SPF/DMARC, or mailbox security. SMTP runs synchronously; recovery response timing and mail-flood resilience need staging measurement. No third-party breached-password lookup, social login, SMS recovery, WebAuthn, administrative account-recovery bypass, or background mail queue is configured. Browser tests cover documented scenarios and do not prove every assistive-technology behavior.

Account recovery requires the mailbox and, for MFA accounts, an authenticator or unused recovery code. A password-reset email does not disable MFA. Application-server or encryption-key compromise can reveal session/TOTP material; database encryption does not protect an already compromised runtime.
