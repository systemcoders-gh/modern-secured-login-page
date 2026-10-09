"""Allauth extensions for encrypted TOTP and hashed, single-use recovery codes."""

from allauth.mfa.adapter import DefaultMFAAdapter, get_adapter
from allauth.mfa.base.forms import AuthenticateForm as AllauthAuthenticateForm
from allauth.mfa.base.forms import ReauthenticateForm as AllauthReauthenticateForm
from allauth.mfa.base.internal.flows import check_rate_limit
from allauth.mfa.models import Authenticator
from cryptography.fernet import Fernet, MultiFernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.views.decorators.debug import sensitive_variables

from accounts.audit import record
from accounts.recovery import consume_recovery_code


class EncryptedMFAAdapter(DefaultMFAAdapter):
    """Keep the encryption key separate from both the database and Django signing key."""

    @staticmethod
    def _cipher() -> MultiFernet:
        keys = settings.MFA_ENCRYPTION_KEYS
        if not keys:
            raise ImproperlyConfigured("At least one MFA encryption key is required.")
        return MultiFernet([Fernet(key.encode("ascii")) for key in keys])

    @sensitive_variables()
    def encrypt(self, text: str) -> str:
        return self._cipher().encrypt(text.encode("utf-8")).decode("ascii")

    @sensitive_variables()
    def decrypt(self, encrypted_text: str) -> str:
        # Never fall back to treating a failed decryption as plaintext.
        return self._cipher().decrypt(encrypted_text.encode("ascii")).decode("utf-8")


class RecoveryCodeAuthenticationMixin:
    @sensitive_variables()
    def clean_code(self) -> str:
        clear_rate_limit = check_rate_limit(self.user)
        code = self.cleaned_data["code"].strip()
        authenticator = Authenticator.objects.filter(
            user=self.user, type=Authenticator.Type.TOTP
        ).first()
        valid = False
        is_recovery = False
        if authenticator and len(code) <= 128:
            if len(code) == 6 and code.isascii() and code.isdecimal():
                valid = authenticator.wrap().validate_code(code)
            else:
                valid = consume_recovery_code(self.user, code)
                is_recovery = valid
        if valid:
            self.authenticator = authenticator
            clear_rate_limit()
            if is_recovery:
                record("recovery_code_used", user=self.user)
            return code
        if authenticator:
            self._emit_authentication_failed(authenticator)
        raise get_adapter().validation_error("incorrect_code")


class AuthenticateForm(RecoveryCodeAuthenticationMixin, AllauthAuthenticateForm):
    """Keep allauth's login stage and authentication recording intact."""


class ReauthenticateForm(RecoveryCodeAuthenticationMixin, AllauthReauthenticateForm):
    """Apply the same recovery validation to fresh-authentication requests."""
