import logging
import re

from django.views.debug import SafeExceptionReporterFilter


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.sensitive_post_parameters = "__ALL__"
        response = self.get_response(request)
        # Framework view decorators can replace this attribute with a narrower list.
        request.sensitive_post_parameters = "__ALL__"
        response["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; font-src 'self'; connect-src 'self'; "
            "object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )
        # Origin-only referrers never disclose token paths. Unlike no-referrer,
        # this also preserves Chromium's Origin header for CSRF-protected forms.
        response["Referrer-Policy"] = "strict-origin"
        response["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response["Cross-Origin-Opener-Policy"] = "same-origin"
        if not request.path.startswith("/static/"):
            response["Cache-Control"] = "no-store, private"
        return response


class RedactAuthURLsFilter(logging.Filter):
    def filter(self, record):
        message = record.getMessage()
        record.msg = re.sub(
            r"(/accounts/(?:confirm-email|password/reset/key)/)[^\s'\"<>]+",
            r"\1[redacted]",
            message,
        )
        record.args = ()
        return True


class AllPostParametersFilter(SafeExceptionReporterFilter):
    def get_post_parameters(self, request):
        if request is not None:
            request.sensitive_post_parameters = "__ALL__"
        return super().get_post_parameters(request)
