"""Local learning defaults; production refuses incomplete security configuration."""

import json
import os
import secrets
from pathlib import Path
from urllib.parse import urlsplit

import dj_database_url
from cryptography.fernet import Fernet
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
# Environment variables take precedence over the optional, ignored local .env file.
try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env", override=False)
except ImportError:
    pass


def flag(name, default=False):
    return os.environ.get(name, str(default)).lower() in {"true", "1", "yes"}


def csv(name, default=""):
    return [v.strip() for v in os.environ.get(name, default).split(",") if v.strip()]


PRODUCTION = os.environ.get("APP_ENV", "development") == "production"
DEBUG = flag("DJANGO_DEBUG", False)
LOCAL_DIR = BASE_DIR / ".local"
if not PRODUCTION:
    LOCAL_DIR.mkdir(exist_ok=True)
    key_file = LOCAL_DIR / "secrets.json"
    if not key_file.exists():
        # O_EXCL avoids competing development processes replacing each other's keys.
        try:
            with key_file.open("x", encoding="utf-8") as handle:
                json.dump(
                    {"django": secrets.token_urlsafe(64), "mfa": Fernet.generate_key().decode()},
                    handle,
                )
            key_file.chmod(0o600)
        except FileExistsError:
            pass
    local_keys = json.loads(key_file.read_text(encoding="utf-8"))
else:
    local_keys = {}

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY") or local_keys.get("django", "")
MFA_ENCRYPTION_KEYS = csv("MFA_ENCRYPTION_KEYS") or ([local_keys["mfa"]] if local_keys else [])
APP_ORIGIN = os.environ.get("APP_ORIGIN", "http://127.0.0.1:8000").rstrip("/")
origin = urlsplit(APP_ORIGIN)
if (
    origin.scheme not in {"http", "https"}
    or not origin.hostname
    or origin.username
    or origin.password
    or origin.path
    or origin.query
    or origin.fragment
):
    raise ImproperlyConfigured("APP_ORIGIN must be an absolute origin without path or credentials.")
ALLOWED_HOSTS = csv("ALLOWED_HOSTS", "127.0.0.1,localhost,[::1]" if not PRODUCTION else "")
CSRF_TRUSTED_ORIGINS = csv("CSRF_TRUSTED_ORIGINS", APP_ORIGIN)
redis_url = os.environ.get("REDIS_URL", "")
database_url = os.environ.get("DATABASE_URL", "")
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND",
    "django.core.mail.backends.smtp.EmailBackend"
    if PRODUCTION
    else "django.core.mail.backends.filebased.EmailBackend",
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = flag("EMAIL_USE_TLS", True)
EMAIL_USE_SSL = flag("EMAIL_USE_SSL", False)
if EMAIL_USE_TLS and EMAIL_USE_SSL:
    raise ImproperlyConfigured("Select one SMTP TLS mode, not both.")
EMAIL_TIMEOUT = 10
EMAIL_FILE_PATH = LOCAL_DIR / "emails"
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "System Coders <noreply@localhost>")

if not SECRET_KEY or not MFA_ENCRYPTION_KEYS:
    raise ImproperlyConfigured("Set DJANGO_SECRET_KEY and MFA_ENCRYPTION_KEYS.")
try:
    for key in MFA_ENCRYPTION_KEYS:
        Fernet(key.encode())
except (ValueError, TypeError) as exc:
    raise ImproperlyConfigured("MFA_ENCRYPTION_KEYS must contain valid Fernet keys.") from exc
if PRODUCTION:
    if DEBUG or len(SECRET_KEY) < 50:
        raise ImproperlyConfigured("Production requires debug off and a strong secret key.")
    if (
        origin.scheme != "https"
        or not ALLOWED_HOSTS
        or any("*" in host or host.startswith(".") for host in ALLOWED_HOSTS)
        or origin.hostname not in ALLOWED_HOSTS
        or any(not v.startswith("https://") or "*" in v for v in CSRF_TRUSTED_ORIGINS)
    ):
        raise ImproperlyConfigured("Production requires explicit HTTPS origins and allowed hosts.")
    if not database_url.startswith(("postgres://", "postgresql://")) or not redis_url:
        raise ImproperlyConfigured(
            "Production requires PostgreSQL DATABASE_URL and shared REDIS_URL."
        )
    if EMAIL_BACKEND != "django.core.mail.backends.smtp.EmailBackend" or not EMAIL_HOST:
        raise ImproperlyConfigured("Production requires a configured SMTP email backend.")
    if not (EMAIL_USE_TLS or EMAIL_USE_SSL) or "localhost" in DEFAULT_FROM_EMAIL:
        raise ImproperlyConfigured("Production requires encrypted SMTP and a real sender domain.")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts.apps.AccountsConfig",
    "allauth",
    "allauth.account",
    "allauth.mfa",
    "allauth.usersessions",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "accounts.middleware.SecurityHeadersMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "allauth.usersessions.middleware.UserSessionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "accounts.context_processors.brand",
            ],
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
DATABASES = {
    "default": dj_database_url.parse(database_url, conn_max_age=60, conn_health_checks=True)
    if database_url
    else {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": LOCAL_DIR / "db.sqlite3",
        "OPTIONS": {"timeout": 20},
    }
}
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": redis_url,
        "KEY_PREFIX": "secured-login",
    }
    if redis_url
    else {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "security"}
}
AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["allauth.account.auth_backends.AuthenticationBackend"]
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 15},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
PASSWORD_RESET_TIMEOUT = 1800
LOGIN_URL = "account_login"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/accounts/login/"
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_USER_MODEL_EMAIL_FIELD = "email"
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_FORMS = {
    "signup": "accounts.forms.SignupForm",
    "login": "accounts.forms.LoginForm",
    "reset_password": "accounts.forms.ResetPasswordForm",  # nosec B105: import path, not a credential
}
ACCOUNT_ADAPTER = "accounts.adapters.AccountAdapter"
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 1
ACCOUNT_CONFIRM_EMAIL_ON_GET = False
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = False
ACCOUNT_LOGIN_ON_PASSWORD_RESET = False
ACCOUNT_LOGOUT_ON_GET = False
ACCOUNT_EMAIL_NOTIFICATIONS = True
ACCOUNT_PREVENT_ENUMERATION = True
ACCOUNT_EMAIL_UNKNOWN_ACCOUNTS = True
ACCOUNT_SESSION_REMEMBER = None
ACCOUNT_REAUTHENTICATION_TIMEOUT = 300
ACCOUNT_REAUTHENTICATION_REQUIRED = True
ACCOUNT_RATE_LIMITS = {
    "login": "30/m/ip",
    "login_failed": "5/5m/key,20/5m/ip",
    "signup": "5/h/ip",
    "reset_password": "5/h/ip,3/h/key",  # nosec B105: rate-limit policy
    "reset_password_from_key": "10/h/ip",  # nosec B105: rate-limit policy
    "change_password": "5/m/user",  # nosec B105: rate-limit policy
    "reauthenticate": "5/5m/user",
    "manage_email": "5/h/user",
    "confirm_email": "3/h/key,10/h/ip",
    "resend_verification": "3/h/key,5/h/ip",
}
ALLAUTH_TRUSTED_PROXY_COUNT = int(os.environ.get("ALLAUTH_TRUSTED_PROXY_COUNT", "0"))
MFA_ADAPTER = "accounts.mfa.EncryptedMFAAdapter"
MFA_SUPPORTED_TYPES = ["totp"]
MFA_FORMS = {
    "authenticate": "accounts.mfa.AuthenticateForm",
    "reauthenticate": "accounts.mfa.ReauthenticateForm",
}
MFA_TRUST_ENABLED = False
MFA_TOTP_ISSUER = "System Coders"
MFA_TOTP_TOLERANCE = 0
MFA_ALLOW_UNVERIFIED_EMAIL = False
USERSESSIONS_TRACK_ACTIVITY = True
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_SERIALIZER = "accounts.sessions.EncryptedJSONSerializer"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = PRODUCTION
CSRF_COOKIE_SECURE = PRODUCTION
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_SSL_REDIRECT = PRODUCTION
SECURE_HSTS_SECONDS = 31536000 if PRODUCTION else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = flag("HSTS_INCLUDE_SUBDOMAINS", False)
SECURE_HSTS_PRELOAD = flag("HSTS_PRELOAD", False)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin"
X_FRAME_OPTIONS = "DENY"
if flag("TRUST_PROXY_HTTPS"):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = LOCAL_DIR / "media"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
        if PRODUCTION
        else "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
CSRF_FAILURE_VIEW = "accounts.views.csrf_failure"
DEFAULT_EXCEPTION_REPORTER_FILTER = "accounts.middleware.AllPostParametersFilter"
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"redact": {"()": "accounts.middleware.RedactAuthURLsFilter"}},
    "handlers": {
        "console": {"class": "logging.StreamHandler", "filters": ["redact"]},
        "null": {"class": "logging.NullHandler"},
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        # Access paths can contain reset/verification tokens. Never record them here.
        "django.server": {"handlers": ["null"], "propagate": False},
    },
}
