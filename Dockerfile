FROM python:3.13-slim

ENV APP_ENV=production \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY requirements.txt ./
RUN python -m pip install --require-hashes -r requirements.txt

COPY accounts/ accounts/
COPY config/ config/
COPY templates/ templates/
COPY static/ static/
COPY manage.py ./

# Generate transient build-only keys without displaying or persisting them.
# Use production storage so hashed asset names and the manifest are generated.
RUN python - <<'PY'
import os
import secrets
import subprocess
from cryptography.fernet import Fernet

env = os.environ.copy()
env.update(
    DJANGO_SECRET_KEY=secrets.token_urlsafe(64),
    MFA_ENCRYPTION_KEYS=Fernet.generate_key().decode(),
    APP_ORIGIN="https://build.example.test",
    ALLOWED_HOSTS="build.example.test",
    CSRF_TRUSTED_ORIGINS="https://build.example.test",
    DATABASE_URL="postgresql://localhost/auth_build",
    REDIS_URL="redis://localhost:6379/0",
    EMAIL_HOST="smtp.example.test",
    DEFAULT_FROM_EMAIL="demo@build.example.test",
)
subprocess.run(["python", "manage.py", "collectstatic", "--noinput"], env=env, check=True)
PY

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

USER 10001:10001
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--access-logfile", "/dev/null", "--error-logfile", "-", "--capture-output"]
