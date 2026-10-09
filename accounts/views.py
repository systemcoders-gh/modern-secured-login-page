from allauth.account.adapter import get_adapter
from allauth.account.decorators import reauthentication_required, verified_email_required
from allauth.account.models import EmailAddress
from allauth.account.views import SignupView
from allauth.core import ratelimit
from allauth.mfa.models import Authenticator
from allauth.usersessions.models import UserSession
from django.contrib import messages
from django.core.cache import cache
from django.db import IntegrityError, connection, transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from .audit import record
from .forms import ProfileForm, ResendVerificationForm
from .models import RecoveryCode, User
from .signals import end_other_sessions


class SafeSignupView(SignupView):
    def form_valid(self, form):
        if form.account_already_exists:
            # Match the principal hashing work on the new-account path.
            User().set_password(form.cleaned_data["password1"])
        # A uniqueness race must not expose a 500 or disclose account existence.
        try:
            with transaction.atomic():
                return super().form_valid(form)
        except IntegrityError:
            if not EmailAddress.objects.filter(email__iexact=form.cleaned_data["email"]).exists():
                raise
            return redirect("account_email_verification_sent")


@verified_email_required
@require_GET
def dashboard(request):
    return render(
        request,
        "accounts/dashboard.html",
        {
            "mfa_enabled": Authenticator.objects.filter(
                user=request.user, type=Authenticator.Type.TOTP
            ).exists(),
            "recovery_count": RecoveryCode.objects.filter(
                user=request.user, used_at__isnull=True
            ).count(),
            "active_session_count": len(UserSession.objects.purge_and_list(request.user)),
            "recent_events": request.user.security_events.all()[:6],
        },
    )


@verified_email_required
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        record("profile_updated", request.user)
        messages.success(request, "Your profile has been updated.")
        return redirect("profile")
    return render(request, "accounts/profile.html", {"form": form})


@verified_email_required
@require_GET
def sessions(request):
    records = UserSession.objects.purge_and_list(request.user)
    for session in records:
        ua = session.user_agent
        session.label = (
            "Edge"
            if "Edg/" in ua
            else "Firefox"
            if "Firefox/" in ua
            else "Chrome"
            if "Chrome/" in ua
            else "Safari"
            if "Safari/" in ua
            else "Browser"
        )
        session.current = session.session_key == request.session.session_key
    return render(request, "accounts/sessions.html", {"sessions": records})


@verified_email_required
@require_POST
@reauthentication_required
def revoke_sessions(request):
    end_other_sessions(request.user, request.session.session_key)
    record("sessions_revoked", request.user)
    messages.success(request, "You have been signed out of all other sessions.")
    return redirect("sessions")


def resend_verification(request):
    form = ResendVerificationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].strip().lower()
        if not ratelimit.consume(request, action="resend_verification", key=email):
            return ratelimit.respond_429(request)
        address = EmailAddress.objects.filter(email__iexact=email, verified=False).first()
        if address:
            address.send_confirmation(request)
        else:
            get_adapter(request).send_mail("account/email/verification_requested", email, {})
        return redirect("account_email_verification_sent")
    return render(request, "accounts/resend_verification.html", {"form": form})


@require_GET
def health(request):
    # No environment, provider or version details exposed on a public probe.
    try:
        connection.ensure_connection()
        cache.get("health-probe")
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})


@require_GET
def about(request):
    return render(request, "accounts/about.html")


def csrf_failure(request, reason=""):
    return render(request, "403.html", status=403)


def error403(request, exception):
    return render(request, "403.html", status=403)


def error404(request, exception):
    return render(request, "404.html", status=404)


def error500(request):
    return render(request, "500.html", status=500)


def error429(request):
    response = render(request, "429.html", status=429)
    response["Retry-After"] = "300"
    return response
