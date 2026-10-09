"""Fail closed on obvious repository secrets without displaying matched values.

This intentionally small guard is not a substitute for review or provider-side
secret scanning. Ignored runtime data is never opened in the default source scan.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IGNORED_DIRS = {
    ".git",
    ".venv",
    ".local",
    ".tmp",
    "__pycache__",
    ".ruff_cache",
    "staticfiles",
    "output",
    "test-results",
    "playwright-report",
}
BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2", ".pdf"}
PATTERNS = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "github-token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b"),
    "aws-access-key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "credential-url": re.compile(r"\b(?:postgres(?:ql)?|redis|rediss)://[^\s/:]+:[^\s/@]+@"),
    "literal-env-secret": re.compile(
        r"(?:DJANGO_SECRET_KEY|MFA_ENCRYPTION_KEYS|EMAIL_HOST_PASSWORD)"
        r"\s*(?:[\"']\s*)?[:=]\s*[\"']([^\"'\r\n]{12,})[\"']"
    ),
}


def git(*args: str) -> bytes:
    """Use argument arrays, never shell interpolation, and suppress stderr data."""
    result = subprocess.run(  # noqa: S603
        ["git", "-C", str(ROOT), *args],
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError("Git inspection failed; initialize/check the repository first.")
    return result.stdout


def forbidden_path(name: str) -> bool:
    path = Path(name)
    parts = set(path.parts)
    return bool(
        parts.intersection(IGNORED_DIRS)
        or (path.name.startswith(".env") and path.name != ".env.example")
        or path.suffix.lower() in {".sqlite3", ".db", ".pem", ".key", ".p12", ".pfx"}
        or path.name.endswith((".sqlite3-wal", ".sqlite3-shm", ".sqlite3-journal"))
    )


def findings(name: str, data: bytes, enforce_paths: bool = False) -> list[str]:
    if enforce_paths and forbidden_path(name):
        return [f"{name}: forbidden-runtime-or-secret-file"]
    if Path(name).suffix.lower() in BINARY_SUFFIXES:
        return []
    content = data.decode("utf-8", errors="replace")
    issues = []
    for line_number, line in enumerate(content.splitlines(), 1):
        # Deliberate test fixtures may be annotated, but never real values.
        if "secret-scan: synthetic fixture" in line:
            continue
        for rule, pattern in PATTERNS.items():
            if pattern.search(line):
                issues.append(f"{name}:{line_number}: {rule}")
    return issues


def inspect(mode: str) -> tuple[list[str], int]:
    issues: list[str] = []
    count = 0
    if mode == "history":
        objects = git("rev-list", "--objects", "--all").decode().splitlines()
        for entry in objects:
            object_id, _, name = entry.partition(" ")
            if not name or git("cat-file", "-t", object_id).strip() != b"blob":
                continue
            issues.extend(findings(name, git("cat-file", "blob", object_id), True))
            count += 1
    elif mode in {"staged", "tracked"}:
        args = (
            ("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z")
            if mode == "staged"
            else ("ls-files", "-z")
        )
        for raw_name in git(*args).split(b"\0"):
            if not raw_name:
                continue
            name = raw_name.decode("utf-8", errors="strict")
            data = git("show", f":{name}") if mode == "staged" else (ROOT / name).read_bytes()
            issues.extend(findings(name, data, True))
            count += 1
    else:
        for path in sorted(ROOT.rglob("*")):
            if not path.is_file() or any(
                part in IGNORED_DIRS for part in path.relative_to(ROOT).parts
            ):
                continue
            name = path.relative_to(ROOT).as_posix()
            if path.name.startswith(".env") and path.name != ".env.example":
                continue
            # Detect database/key files by path without opening sensitive data.
            if forbidden_path(name):
                issues.append(f"{name}: forbidden-runtime-or-secret-file")
            else:
                issues.extend(findings(name, path.read_bytes()))
            count += 1
    return issues, count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--staged", action="store_true", help="Inspect exact staged bytes.")
    mode.add_argument("--tracked", action="store_true", help="Inspect tracked worktree files.")
    mode.add_argument("--history", action="store_true", help="Inspect all reachable Git blobs.")
    args = parser.parse_args()
    selected = (
        "staged"
        if args.staged
        else "tracked"
        if args.tracked
        else "history"
        if args.history
        else "source"
    )
    try:
        issues, count = inspect(selected)
    except (OSError, UnicodeError, RuntimeError):
        print(
            "Secret inspection could not complete; no secret values were displayed.",
            file=sys.stderr,
        )
        return 2
    if issues:
        print("Potential secret or forbidden runtime files detected (values suppressed):")
        for issue in sorted(set(issues)):
            print(issue)
        return 1
    print(
        f"Secret pattern scan passed: {count} {selected} files/blobs. Manual review remains required."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
