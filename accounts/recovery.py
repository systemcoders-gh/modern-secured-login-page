"""Generate recovery codes once and consume their stored password hashes safely."""

import re
import secrets

from allauth.account.adapter import get_adapter
from allauth.account.decorators import (
    reauthentication_required,
    verified_email_required,
)
from allauth.core import ratelimit
from allauth.mfa.models import Authenticator
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_variables

from accounts.audit import record
from accounts.models import RecoveryCode
from accounts.signals import end_other_sessions

RECOVERY_CODE_COUNT = 10
RECOVERY_CODE_PATTERN = re.compile(r"[0-9A-F]{32}\Z")


@sensitive_variables()
def _normalize_code(code: str) -> str:
    return "".join(code.split()).replace("-", "").upper()


@sensitive_variables()
def generate_recovery_codes(user) -> list[str]:
    """Return raw 128-bit codes; persist only Django's salted one-way hashes."""
    values = [secrets.token_hex(16).upper() for _ in range(RECOVERY_CODE_COUNT)]
    digests = [make_password(code) for code in values]
    with transaction.atomic():
        # Serialize regeneration with consumption on PostgreSQL. The conditional
        # consumption update below remains authoritative on SQLite as well.
        get_user_model().objects.select_for_update().get(pk=user.pk)
        if not Authenticator.objects.filter(user=user, type=Authenticator.Type.TOTP).exists():
            raise ValueError("Enable authenticator-app authentication first.")
        RecoveryCode.objects.filter(user=user).delete()
        RecoveryCode.objects.bulk_create(
            [RecoveryCode(user=user, digest=digest) for digest in digests]
        )
    return ["-".join(code[i : i + 8] for i in range(0, 32, 8)) for code in values]


@sensitive_variables()
def consume_recovery_code(user, code: str) -> bool:
    normalized = _normalize_code(code)
    if not RECOVERY_CODE_PATTERN.fullmatch(normalized):
        return False
    # Check hashes outside a write transaction to avoid holding a SQLite lock
    # while doing expensive password hashing. A concurrent regeneration deletes
    # the old row, so the conditional update then correctly fails.
    for recovery_code in RecoveryCode.objects.filter(user=user, used_at__isnull=True):
        if check_password(normalized, recovery_code.digest):
            updated = RecoveryCode.objects.filter(
                pk=recovery_code.pk, user=user, used_at__isnull=True
            ).update(used_at=timezone.now())
            return updated == 1
    return False


class RecoveryCodesForm(forms.Form):
    action = forms.ChoiceField(
        choices=[("generate", "Generate recovery codes")],
        initial="generate",
        widget=forms.HiddenInput,
    )


@method_decorator(verified_email_required, name="dispatch")
@method_decorator(reauthentication_required(allow_get=True), name="dispatch")
@method_decorator(never_cache, name="dispatch")
class RecoveryCodesView(View):
    template_name = "accounts/recovery_codes.html"

    def dispatch(self, request, *args, **kwargs):
        if not Authenticator.objects.filter(
            user=request.user, type=Authenticator.Type.TOTP
        ).exists():
            return redirect("mfa_index")
        return super().dispatch(request, *args, **kwargs)

    @sensitive_variables()
    def _render(self, request, form, codes=None, status=200):
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "codes": codes,
                "count": RecoveryCode.objects.filter(
                    user=request.user, used_at__isnull=True
                ).count(),
            },
            status=status,
        )

    def get(self, request):
        return self._render(request, RecoveryCodesForm())

    @sensitive_variables()
    def post(self, request):
        form = RecoveryCodesForm(request.POST)
        if not form.is_valid():
            return self._render(request, form, status=400)
        if not ratelimit.consume(request, action="reauthenticate", user=request.user):
            return ratelimit.respond_429(request)
        codes = generate_recovery_codes(request.user)
        end_other_sessions(request.user, request.session.session_key)
        record("recovery_codes_generated", user=request.user)
        get_adapter(request).send_notification_mail(
            "mfa/email/recovery_codes_generated", request.user
        )
        # Raw codes never enter the database, session, audit log or email.
        return self._render(request, form, codes=codes)
