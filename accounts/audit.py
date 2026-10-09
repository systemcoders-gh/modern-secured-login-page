from .models import SecurityEvent

EVENTS = {
    "registered",
    "login_succeeded",
    "login_failed",
    "logged_out",
    "email_verified",
    "password_reset_requested",
    "password_changed",
    "password_reset",
    "mfa_enabled",
    "mfa_disabled",
    "recovery_codes_generated",
    "recovery_code_used",
    "sessions_revoked",
    "profile_updated",
}


def record(kind, user=None):
    if kind not in EVENTS:
        raise ValueError("Unsupported security event.")
    # Fixed event names only; no request bodies, email addresses, IPs or credentials.
    return SecurityEvent.objects.create(kind=kind, user=user)
