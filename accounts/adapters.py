from urllib.parse import quote

from allauth.account.adapter import DefaultAccountAdapter
from allauth.core.exceptions import ImmediateHttpResponse
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.crypto import constant_time_compare
from django.views.decorators.debug import sensitive_variables

from .models import User

PENDING_AUTH_STATE = "pending_credential_binding"


class AccountAdapter(DefaultAccountAdapter):
    @sensitive_variables()
    def pre_login(self, request, user, **kwargs):
        response = super().pre_login(request, user, **kwargs)
        if response is None:
            # This hook runs only when authentication starts. Allauth resumes
            # suspended verification/MFA stages without calling pre_login again.
            request.session[PENDING_AUTH_STATE] = {
                "user_pk": str(user.pk),
                "auth_hash": user.get_session_auth_hash(),
            }
        return response

    @sensitive_variables()
    def login(self, request, user):
        binding = request.session.pop(PENDING_AUTH_STATE, None)
        current = User.objects.filter(pk=user.pk).first()
        if (
            not current
            or not current.is_active
            or not isinstance(binding, dict)
            or binding.get("user_pk") != str(current.pk)
            or not constant_time_compare(
                binding.get("auth_hash", ""), current.get_session_auth_hash()
            )
        ):
            # A pending MFA session is anonymous and is absent from UserSession.
            # Password changes must invalidate its previous first-factor proof.
            request.session.flush()
            raise ImmediateHttpResponse(redirect("account_login"))
        return super().login(request, current)

    def clean_email(self, email):
        return User.objects.normalize_email(email)

    def get_email_confirmation_url(self, request, emailconfirmation):
        return settings.APP_ORIGIN + reverse(
            "account_confirm_email", kwargs={"key": emailconfirmation.key}
        )

    def get_reset_password_from_key_url(self, key):
        path = reverse("account_reset_password_from_key", kwargs={"uidb36": "UID", "key": "KEY"})
        return settings.APP_ORIGIN + path.replace("UID-KEY", quote(key))
