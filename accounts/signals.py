from allauth.account import signals as account_signals
from allauth.mfa import signals as mfa_signals
from allauth.mfa.models import Authenticator
from allauth.usersessions.models import UserSession
from django.contrib.auth.signals import user_logged_out, user_login_failed
from django.dispatch import receiver

from .audit import record
from .models import RecoveryCode


def end_other_sessions(user, current_key=None):
    for session in UserSession.objects.filter(user=user).exclude(session_key=current_key):
        session.end()


@receiver(account_signals.user_signed_up)
def registered(sender, user, **kwargs):
    record("registered", user)


@receiver(account_signals.user_logged_in)
def logged_in(sender, user, **kwargs):
    record("login_succeeded", user)


@receiver(user_login_failed)
def login_failed(sender, **kwargs):
    record("login_failed")


@receiver(user_logged_out)
def logged_out(sender, request, user, **kwargs):
    if user and user.is_authenticated:
        UserSession.objects.filter(user=user, session_key=request.session.session_key).delete()
        record("logged_out", user)


@receiver(account_signals.email_confirmed)
def email_confirmed(sender, email_address, **kwargs):
    record("email_verified", email_address.user)


@receiver(account_signals.password_changed)
def password_changed(sender, request, user, **kwargs):
    end_other_sessions(user, request.session.session_key)
    record("password_changed", user)


@receiver(account_signals.password_reset)
def password_reset(sender, user, **kwargs):
    end_other_sessions(user)
    record("password_reset", user)


@receiver(mfa_signals.authenticator_added)
def mfa_added(sender, request, user, authenticator, **kwargs):
    if authenticator.type == Authenticator.Type.TOTP:
        end_other_sessions(user, request.session.session_key)
        record("mfa_enabled", user)


@receiver(mfa_signals.authenticator_removed)
def mfa_removed(sender, request, user, authenticator, **kwargs):
    if authenticator.type == Authenticator.Type.TOTP:
        RecoveryCode.objects.filter(user=user).delete()
        end_other_sessions(user, request.session.session_key)
        record("mfa_disabled", user)


@receiver(mfa_signals.authentication_failed)
def mfa_failed(sender, user, **kwargs):
    record("login_failed", user)
