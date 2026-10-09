import logging
import os
import runpy
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib.sessions.models import Session
from django.test import Client, SimpleTestCase, override_settings

from accounts.middleware import RedactAuthURLsFilter
from accounts.models import SecurityEvent
from accounts.sessions import EncryptedJSONSerializer
from tests.helpers import PASSWORD, AuthTestCase


class SecurityBoundaryTests(AuthTestCase):
    def test_protected_routes_require_authentication(self):
        for path in [
            "/",
            "/settings/",
            "/sessions/",
            "/security/recovery-codes/",
            "/accounts/2fa/",
        ]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 302)
            self.assertNotContains(response, self.user.email, status_code=302)

    def test_csrf_is_enforced_on_state_changes(self):
        client = Client(enforce_csrf_checks=True)
        for path in [
            "/accounts/login/",
            "/accounts/signup/",
            "/accounts/password/reset/",
            "/verification/resend/",
        ]:
            self.assertEqual(client.post(path, {"email": self.user.email}).status_code, 403)
        client.force_login(self.user)
        for path in [
            "/settings/",
            "/sessions/revoke/",
            "/security/recovery-codes/",
            "/accounts/logout/",
        ]:
            self.assertEqual(client.post(path).status_code, 403)

    def test_user_name_is_escaped(self):
        self.user.full_name = '<script>alert("xss")</script>'
        self.user.save()
        self.login()
        response = self.client.get("/")
        self.assertNotContains(response, '<script>alert("xss")</script>')
        self.assertContains(response, "&lt;script&gt;")

    def test_sql_injection_input_is_not_authenticated(self):
        response = self.client.post(
            "/accounts/login/", {"login": "' OR 1=1 --", "password": PASSWORD}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_external_redirect_is_rejected(self):
        response = self.client.post(
            "/accounts/login/?next=https://evil.example/",
            {"login": self.user.email, "password": PASSWORD},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(response.url.startswith("https://evil.example"))

    def test_login_throttle_enforced_on_server(self):
        responses = [
            self.client.post("/accounts/login/", {"login": self.user.email, "password": "wrong"})
            for _ in range(7)
        ]
        self.assertTrue(
            any("too many" in r.content.decode().lower() or r.status_code == 429 for r in responses)
        )
        self.assertNotIn("_auth_user_id", self.client.session)
        self.login()
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_password_reset_throttle_applies_to_target_email(self):
        for index in range(5):
            response = self.client.post(
                "/accounts/password/reset/",
                {"email": self.user.email},
                REMOTE_ADDR=f"192.0.2.{index + 1}",
            )
        self.assertEqual(response.status_code, 429)

    def test_proxy_headers_not_trusted_by_default(self):
        from allauth.account.adapter import get_adapter
        from django.test import RequestFactory

        request = RequestFactory().get(
            "/", REMOTE_ADDR="192.0.2.10", HTTP_X_FORWARDED_FOR="198.51.100.5"
        )
        self.assertEqual(get_adapter(request).get_client_ip(request), "192.0.2.10")

    def test_security_headers_and_cookie_attributes(self):
        response = self.client.get("/accounts/login/")
        self.assertIn("frame-ancestors 'none'", response["Content-Security-Policy"])
        self.assertNotIn("unsafe-inline", response["Content-Security-Policy"])
        self.assertEqual(response["X-Frame-Options"], "DENY")
        self.assertEqual(response["Referrer-Policy"], "strict-origin")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertIn("no-store", response["Cache-Control"])
        with override_settings(SESSION_COOKIE_SECURE=True):
            response = self.login()
        cookie = response.cookies[settings.SESSION_COOKIE_NAME]
        self.assertTrue(cookie["httponly"])
        self.assertTrue(cookie["secure"])
        self.assertEqual(cookie["samesite"], "Lax")

    def test_sessions_encrypted_at_rest(self):
        self.login()
        session = self.client.session
        session["mfa.totp.secret"] = "never-store-plaintext"
        session.save()
        row = Session.objects.get(session_key=session.session_key)
        self.assertNotIn("never-store-plaintext", row.session_data)
        self.assertEqual(row.get_decoded()["mfa.totp.secret"], "never-store-plaintext")
        encoded = EncryptedJSONSerializer().dumps({"enrollment": "never-store-plaintext"})
        self.assertNotIn(b"never-store-plaintext", encoded)

    def test_events_do_not_store_credentials(self):
        self.login()
        self.client.post("/accounts/password/reset/", {"email": self.user.email})
        for event in SecurityEvent.objects.values():
            self.assertNotIn(PASSWORD, str(event))
            self.assertNotIn(self.user.email, str(event))
        self.assertTrue(SecurityEvent.objects.filter(kind="login_succeeded").exists())

    def test_no_alternate_admin_login(self):
        self.assertEqual(self.client.get("/admin/login/").status_code, 404)

    @override_settings(DEBUG=False)
    def test_error_pages_do_not_expose_internals(self):
        response = self.client.get("/not-a-route/")
        self.assertEqual(response.status_code, 404)
        self.assertNotContains(response, "Traceback", status_code=404)
        self.assertNotContains(response, "urlpatterns", status_code=404)

    def test_session_page_exposes_no_session_keys(self):
        self.login()
        response = self.client.get("/sessions/")
        self.assertNotContains(response, self.client.session.session_key)

    def test_stale_session_cannot_add_recovery_email(self):
        from allauth.account.models import EmailAddress

        self.client.force_login(self.user)
        response = self.client.post(
            "/accounts/email/", {"email": "attacker@example.test", "action_add": ""}
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("reauthenticate", response.url)
        self.assertFalse(EmailAddress.objects.filter(email="attacker@example.test").exists())

    def test_all_post_parameters_marked_sensitive(self):
        response = self.client.post(
            "/accounts/login/", {"login": self.user.email, "password": "wrong"}
        )
        self.assertEqual(response.wsgi_request.sensitive_post_parameters, "__ALL__")


class ConfigurationTests(SimpleTestCase):
    def production_env(self):
        return {
            "APP_ENV": "production",
            "DJANGO_DEBUG": "false",
            "DJANGO_SECRET_KEY": "x" * 64,  # secret-scan: synthetic fixture
            "MFA_ENCRYPTION_KEYS": Fernet.generate_key().decode(),
            "APP_ORIGIN": "https://auth.example.test",
            "ALLOWED_HOSTS": "auth.example.test",
            "CSRF_TRUSTED_ORIGINS": "https://auth.example.test",
            "DATABASE_URL": "postgresql://localhost/auth_synthetic",
            "REDIS_URL": "redis://localhost:6379/0",
            "EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
            "EMAIL_HOST": "smtp.example.test",
            "DEFAULT_FROM_EMAIL": "demo@auth.example.test",
            "EMAIL_USE_TLS": "true",
        }

    def test_production_secure_defaults(self):
        with patch.dict(os.environ, self.production_env(), clear=True):
            config = runpy.run_path(str(settings.BASE_DIR / "config/settings.py"))
        self.assertTrue(config["SESSION_COOKIE_SECURE"])
        self.assertTrue(config["CSRF_COOKIE_SECURE"])
        self.assertTrue(config["SECURE_SSL_REDIRECT"])
        self.assertFalse(config["DEBUG"])

    def test_incomplete_production_configuration_is_rejected(self):
        from django.core.exceptions import ImproperlyConfigured

        for field, value in [
            ("DJANGO_SECRET_KEY", ""),
            ("MFA_ENCRYPTION_KEYS", ""),
            ("MFA_ENCRYPTION_KEYS", "invalid"),
            ("ALLOWED_HOSTS", "*"),
            ("ALLOWED_HOSTS", "auth.example.test,.example.test"),
            ("APP_ORIGIN", "http://auth.example.test"),
            ("APP_ORIGIN", "https://auth.example.test/unsafe"),
            ("DATABASE_URL", ""),
            ("REDIS_URL", ""),
            ("EMAIL_HOST", ""),
            ("DJANGO_DEBUG", "true"),
        ]:
            env = self.production_env()
            env[field] = value
            with patch.dict(os.environ, env, clear=True), self.assertRaises(ImproperlyConfigured):
                runpy.run_path(str(settings.BASE_DIR / "config/settings.py"))

    def test_authentication_urls_redacted_from_logs(self):
        record = logging.LogRecord(
            "django.request",
            logging.WARNING,
            "",
            0,
            "Not Found: /accounts/password/reset/key/sensitive-token/",
            (),
            None,
        )
        RedactAuthURLsFilter().filter(record)
        self.assertNotIn("sensitive-token", record.getMessage())
