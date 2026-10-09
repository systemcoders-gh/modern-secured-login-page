# Contributing

Start with [README.md](README.md), [AGENTS.md](AGENTS.md), and [docs/architecture.md](docs/architecture.md). Use synthetic data and keep contributions within the standalone authentication app. Report vulnerabilities privately using [SECURITY.md](SECURITY.md), rather than a public issue with exploit details or active links.

## Change process

1. Describe the behavior/bug and acceptance criteria. For a major design change, add an ADR in `docs/decisions.md` before implementation.
2. Work on a scoped `feature/`, `fix/`, or `docs/` branch. Keep commits small and use `feat:`, `fix:`, `test:`, `docs:`, `security:`, or `chore:` subjects.
3. Reuse Django/allauth and existing tooling. Explain new dependencies, maintenance evidence, privileges, and removal before adding them. Commit both dependency policy and updated hash locks.
4. Add tests for meaningful new behavior and failure cases. Check account ownership, verification, MFA, sessions, CSRF, token reuse, and configuration when relevant.
5. Run [the documented checks](docs/testing.md). Describe actual results and skips in the PR template. Update affected documentation.
6. Request review. Avoid self-merging security or schema changes; maintainers configure branch protection after the private repository exists.

## Review expectations

Reviewers inspect authorization on every state change, database constraints/transactions, secret handling, dependency changes, migration safety, accessibility, errors, and backwards compatibility. Review AI-generated code line by line where it handles security decisions. A green test suite does not replace human reasoning.

No production credentials, real users, email files, recovery links, MFA keys, databases, or screenshots showing active secrets may enter commits. Run `python scripts/check_secrets.py --staged` before committing, and `python scripts/check_secrets.py --history` before publication. Pattern scanning is a useful guard and cannot prove absence of all secrets.

## Dependency updates

With the development environment installed:

```powershell
.\.venv\Scripts\python.exe -m piptools compile --generate-hashes --allow-unsafe --strip-extras --no-emit-index-url --output-file requirements.txt requirements.in
.\.venv\Scripts\python.exe -m piptools compile --generate-hashes --allow-unsafe --strip-extras --no-emit-index-url --output-file requirements-dev.txt requirements-dev.in
```

Review platform markers and Linux runtime dependencies such as Gunicorn. A Windows resolver may omit a dependency that is needed in Linux CI or the container; validate the Linux installation before release. Keep index URLs out of generated files and ensure extras are resolved to explicit hash-locked dependencies. Do not hand-edit generated hashes. Audit and rerun authentication/security regressions after updates. Check licenses against MIT distribution obligations and retain required notices.

The development lock uses `--allow-unsafe` to hash-lock resolver/build tooling such as setuptools when included by the dependency graph; otherwise `--require-hashes` can fail on an unpinned dependency. This pip-tools flag is a package-category policy, not permission to skip security review.
