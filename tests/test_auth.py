from datetime import timedelta
from unittest.mock import patch

from allauth.account.forms import default_token_generator
from allauth.account.models import EmailAddress, EmailConfirmationHMAC
from allauth.account.utils import user_pk_to_url_str
from allauth.mfa.models import Authenticator
from django.contrib.sessions.models import Session
from django.core import mail
from django.db import IntegrityError, transaction
from django.test import Client
from django.utils import timezone

from accounts.models import SecurityEvent, User
from tests.helpers import NEW_PASSWORD, PASSWORD, AuthTestCase, email_path


class AuthenticationTests(AuthTestCase):
    def test_registration_verification_and_login(self):
        response = self.client.post(
            "/accounts/signup/",
            {
                "full_name": "Grace Learner",
                "email": " GRACE@example.test ",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )
        self.assertRedirects(response, "/accounts/confirm-email/")
        user = User.objects.get(email="grace@example.test")
        self.assertEqual(user.full_name, "Grace Learner")
        self.assertTrue(user.password.startswith("argon2$argon2id$"))
        self.assertNotIn("_auth_user_id", self.client.session)
        confirmation_path = email_path(mail.outbox[0], "/accounts/confirm-email/")
        self.client.get(confirmation_path)
        self.assertFalse(EmailAddress.objects.get(user=user).verified)
        self.client.post(confirmation_path)
        self.assertTrue(EmailAddress.objects.get(user=user).verified)
        self.assertNotIn("_auth_user_id", self.client.session)
        response = self.client.post(
            "/accounts/login/", {"login": "GRACE@example.test", "password": PASSWORD}, follow=True
        )
        self.assertContains(response, "You have successfully logged in!")
        self.assertContains(response, "Grace Learner")

    def test_duplicate_registration_matches_generic_completion(self):
        response = self.client.post(
            "/accounts/signup/",
            {
                "full_name": "Someone",
                "email": "LEARNER@example.test",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )
        self.assertRedirects(response, "/accounts/confirm-email/")
        self.assertEqual(User.objects.count(), 1)

    def test_database_prevents_case_variant_duplicate(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.bulk_create([User(email="LEARNER@example.test", full_name="duplicate")])

    def test_registration_race_has_generic_response(self):
        with patch("allauth.account.forms.SignupForm.try_save", side_effect=IntegrityError):
            response = self.client.post(
                "/accounts/signup/",
                {
                    "full_name": "Someone",
                    "email": self.user.email,
                    "password1": PASSWORD,
                    "password2": PASSWORD,
                },
            )
        self.assertEqual(response.status_code, 302)

    def test_unverified_cannot_sign_in_or_bypass_dashboard(self):
        EmailAddress.objects.filter(user=self.user).update(verified=False)
        self.login()
        self.assertNotIn("_auth_user_id", self.client.session)
        self.client.force_login(self.user)
        for path in ["/", "/settings/", "/sessions/", "/security/recovery-codes/"]:
            response = self.client.get(path)
            self.assertNotContains(
                response, "You have successfully logged in!", status_code=response.status_code
            )
            self.assertNotEqual(response.status_code, 500)

    def test_email_link_expiry_and_single_use(self):
        address = EmailAddress.objects.get(user=self.user)
        address.verified = False
        address.save()
        with patch(
            "django.core.signing.time.time", return_value=timezone.now().timestamp() - 172800
        ):
            key = EmailConfirmationHMAC(address).key
        self.client.post(f"/accounts/confirm-email/{key}/")
        address.refresh_from_db()
        self.assertFalse(address.verified)
        key = EmailConfirmationHMAC(address).key
        self.client.post(f"/accounts/confirm-email/{key}/")
        self.client.post(f"/accounts/confirm-email/{key}/")
        self.assertEqual(SecurityEvent.objects.filter(kind="email_verified").count(), 1)

    def test_verification_resend_is_generic_and_limited(self):
        response = self.client.post("/verification/resend/", {"email": "unknown@example.test"})
        self.assertRedirects(response, "/accounts/confirm-email/")
        for _ in range(4):
            response = self.client.post("/verification/resend/", {"email": "unknown@example.test"})
        self.assertEqual(response.status_code, 429)

    def test_incorrect_credentials_same_for_known_and_unknown_user(self):
        known = self.client.post(
            "/accounts/login/", {"login": self.user.email, "password": "wrong"}
        )
        unknown = self.client.post(
            "/accounts/login/", {"login": "unknown@example.test", "password": "wrong"}
        )
        self.assertEqual(known.status_code, unknown.status_code)
        self.assertEqual(known.context["form"].errors, unknown.context["form"].errors)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_rotates_session_and_logout_deletes_server_session(self):
        session = self.client.session
        session["before_login"] = True
        session.save()
        before = session.session_key
        self.login()
        after = self.client.session.session_key
        self.assertNotEqual(before, after)
        self.assertFalse(Session.objects.filter(session_key=before).exists())
        self.assertContains(self.client.get("/accounts/logout/"), "Sign out")
        self.assertIn("_auth_user_id", self.client.session)
        self.client.post("/accounts/logout/")
        self.assertFalse(Session.objects.filter(session_key=after).exists())
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_remember_me_is_bounded(self):
        self.login()
        self.assertEqual(self.client.session.get_expiry_age(), 3600)
        self.client.post("/accounts/logout/")
        self.login(remember=True)
        self.assertEqual(self.client.session.get_expiry_age(), 14 * 86400)

    def test_short_and_common_passwords_rejected(self):
        for password in ["short", "123456789012345", "password"]:
            response = self.client.post(
                "/accounts/signup/",
                {
                    "full_name": "New User",
                    "email": "new@example.test",
                    "password1": password,
                    "password2": password,
                },
            )
            self.assertEqual(response.status_code, 200)
            self.assertFalse(User.objects.filter(email="new@example.test").exists())

    def test_long_unicode_passphrase_allowed(self):
        password = "A lighthouse and quiet waters 🌊 " * 8
        response = self.client.post(
            "/accounts/signup/",
            {
                "full_name": "New User",
                "email": "new@example.test",
                "password1": password,
                "password2": password,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.get(email="new@example.test").check_password(password))

    def test_profile_update_cannot_target_other_user(self):
        other = self.create_user("other@example.test", "Other Account")
        self.login()
        self.client.post(
            "/settings/", {"full_name": "Updated Name", "user_id": other.pk, "email": other.email}
        )
        self.user.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(self.user.full_name, "Updated Name")
        self.assertEqual(self.user.email, "learner@example.test")
        self.assertEqual(other.full_name, "Other Account")


class RecoveryAndSessionTests(AuthTestCase):
    def test_reset_requests_match_and_email_uses_trusted_origin(self):
        known = self.client.post(
            "/accounts/password/reset/", {"email": self.user.email}, HTTP_HOST="localhost"
        )
        unknown = self.client.post("/accounts/password/reset/", {"email": "unknown@example.test"})
        self.assertEqual(known.status_code, unknown.status_code)
        self.assertEqual(known.url, unknown.url)
        self.assertIn("http://127.0.0.1:8000/accounts/password/reset/key/", mail.outbox[0].body)
        self.assertNotIn("http://localhost/", mail.outbox[0].body)
        self.assertEqual(SecurityEvent.objects.filter(kind="password_reset_requested").count(), 2)

    def test_reset_end_to_end_revokes_sessions_requires_login_and_preserves_mfa(self):
        first, second, recovery = Client(), Client(), Client()
        self.login(first)
        self.login(second)
        first_key, second_key = first.session.session_key, second.session.session_key
        authenticator = Authenticator.objects.create(
            user=self.user, type="totp", data={"secret": "encrypted-test-fixture"}
        )
        recovery.post("/accounts/password/reset/", {"email": self.user.email})
        path = email_path(mail.outbox[-1], "/accounts/password/reset/key/")
        response = recovery.get(path, follow=True)
        safe_path = response.request["PATH_INFO"]
        response = recovery.post(
            safe_path, {"password1": NEW_PASSWORD, "password2": NEW_PASSWORD}, follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))
        self.assertNotIn("_auth_user_id", recovery.session)
        self.assertFalse(Session.objects.filter(session_key__in=[first_key, second_key]).exists())
        self.assertEqual(first.get("/").status_code, 302)
        self.assertTrue(Authenticator.objects.filter(pk=authenticator.pk).exists())
        response = Client().get(path, follow=True)
        self.assertContains(response, "invalid", status_code=200)
        self.assertTrue(
            any(
                "changed" in message.subject.lower() or "reset" in message.subject.lower()
                for message in mail.outbox
            )
        )

    def test_expired_password_token_rejected(self):
        user = self.user
        with patch.object(
            default_token_generator,
            "_now",
            return_value=timezone.now().replace(tzinfo=None) - timedelta(hours=1),
        ):
            key = default_token_generator.make_token(user)
        path = f"/accounts/password/reset/key/{user_pk_to_url_str(user)}-{key}/"
        response = self.client.get(path, follow=True)
        self.assertContains(response, "invalid", status_code=200)
        user.refresh_from_db()
        self.assertTrue(user.check_password(PASSWORD))

    def test_password_change_revokes_other_devices(self):
        other = Client()
        self.login(other)
        self.login()
        other_key = other.session.session_key
        response = self.client.post(
            "/accounts/password/change/",
            {"oldpassword": PASSWORD, "password1": NEW_PASSWORD, "password2": NEW_PASSWORD},
        )
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))
        self.assertFalse(Session.objects.filter(session_key=other_key).exists())

    def test_revocation_scoped_to_user(self):
        other = self.create_user("other@example.test", "Other User")
        sibling = Client()
        second = Client()
        sibling.post("/accounts/login/", {"login": other.email, "password": PASSWORD})
        self.login(second)
        self.login()
        sibling_key, second_key = sibling.session.session_key, second.session.session_key
        response = self.client.post("/sessions/revoke/", {"user_id": other.pk})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Session.objects.filter(session_key=second_key).exists())
        self.assertTrue(Session.objects.filter(session_key=sibling_key).exists())
        self.assertEqual(sibling.get("/").status_code, 200)

    def test_session_revocation_requires_fresh_authentication(self):
        self.login()
        session = self.client.session
        session["account_authentication_methods"] = []
        session.save()
        response = self.client.post("/sessions/revoke/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("reauthenticate", response.url)
