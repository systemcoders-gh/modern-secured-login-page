"""Real MFA routes, storage boundaries, replay resistance and code lifecycle."""

import time
from unittest.mock import patch

from allauth.account.forms import default_token_generator
from allauth.account.models import EmailAddress, EmailConfirmationHMAC
from allauth.account.utils import user_pk_to_url_str
from allauth.mfa.models import Authenticator
from allauth.mfa.totp.internal.auth import TOTP, format_hotp_value, hotp_value
from cryptography.fernet import Fernet, InvalidToken
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from accounts.mfa import EncryptedMFAAdapter
from accounts.models import RecoveryCode
from accounts.recovery import consume_recovery_code, generate_recovery_codes

PASSWORD = "A long autumn passphrase for this account 2026"
NEW_PASSWORD = "A second unique lighthouse passphrase for this account 2026"
TOTP_SECRET = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"


class MFATests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(
            email="mfa@example.test", password=PASSWORD, full_name="MFA Learner"
        )
        EmailAddress.objects.create(
            user=self.user, email=self.user.email, verified=True, primary=True
        )

    def login(self, client=None):
        return (client or self.client).post(
            reverse("account_login"),
            {"login": self.user.email, "password": PASSWORD},
        )

    def enroll(self):
        self.login()
        response = self.client.get(reverse("mfa_activate_totp"))
        self.assertEqual(response.status_code, 200)
        secret = response.context["form"].secret
        code = self.totp_code(secret)
        response = self.client.post(reverse("mfa_activate_totp"), {"code": code})
        self.assertEqual(response.status_code, 302)
        return secret

    @staticmethod
    def totp_code(secret=TOTP_SECRET):
        return format_hotp_value(hotp_value(secret, int(time.time()) // 30))

    def activate(self):
        return TOTP.activate(self.user, TOTP_SECRET).instance

    def test_incorrect_code_cannot_activate_totp(self):
        self.login()
        response = self.client.get(reverse("mfa_activate_totp"))
        self.assertEqual(response.status_code, 200)
        wrong = "000000"
        if wrong == self.totp_code(response.context["form"].secret):
            wrong = "999999"
        response = self.client.post(reverse("mfa_activate_totp"), {"code": wrong})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Authenticator.objects.filter(user=self.user).exists())

    def test_enrollment_stores_encrypted_secret_and_no_seed_based_recovery_codes(self):
        secret = self.enroll()
        authenticator = Authenticator.objects.get(user=self.user, type=Authenticator.Type.TOTP)
        self.assertNotEqual(authenticator.data["secret"], secret)
        self.assertEqual(EncryptedMFAAdapter().decrypt(authenticator.data["secret"]), secret)
        self.assertFalse(
            Authenticator.objects.filter(
                user=self.user, type=Authenticator.Type.RECOVERY_CODES
            ).exists()
        )

    def test_password_login_does_not_bypass_totp_challenge(self):
        self.activate()
        response = self.login()
        self.assertRedirects(response, reverse("mfa_authenticate"), fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 302)
        response = self.client.post(reverse("mfa_authenticate"), {"code": self.totp_code()})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_password_reset_invalidates_pending_first_factor(self):
        self.activate()
        self.login()
        self.assertNotIn("_auth_user_id", self.client.session)
        reset = Client()
        token = default_token_generator.make_token(self.user)
        reset_path = reverse(
            "account_reset_password_from_key",
            kwargs={"uidb36": user_pk_to_url_str(self.user), "key": token},
        )
        response = reset.get(reset_path, follow=True)
        response = reset.post(
            response.request["PATH_INFO"],
            {"password1": NEW_PASSWORD, "password2": NEW_PASSWORD},
        )
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))
        response = self.client.post(reverse("mfa_authenticate"), {"code": self.totp_code()})
        self.assertRedirects(response, reverse("account_login"), fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertNotIn("account_login", self.client.session)

    def test_password_change_invalidates_pending_first_factor(self):
        self.activate()
        recovery_code = generate_recovery_codes(self.user)[0]
        self.login()
        owner = Client()
        self.login(owner)
        owner.post(reverse("mfa_authenticate"), {"code": recovery_code})
        response = owner.post(
            reverse("account_change_password"),
            {"oldpassword": PASSWORD, "password1": NEW_PASSWORD, "password2": NEW_PASSWORD},
        )
        self.assertEqual(response.status_code, 302)
        response = self.client.post(reverse("mfa_authenticate"), {"code": self.totp_code()})
        self.assertRedirects(response, reverse("account_login"), fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_reset_during_pending_email_verification_requires_new_password(self):
        address = EmailAddress.objects.get(user=self.user)
        address.verified = False
        address.save(update_fields=["verified"])
        verification = EmailConfirmationHMAC(address).key
        self.login()
        self.assertNotIn("_auth_user_id", self.client.session)
        token = default_token_generator.make_token(self.user)
        reset_path = reverse(
            "account_reset_password_from_key",
            kwargs={"uidb36": user_pk_to_url_str(self.user), "key": token},
        )
        reset = Client()
        response = reset.get(reset_path, follow=True)
        reset.post(
            response.request["PATH_INFO"],
            {"password1": NEW_PASSWORD, "password2": NEW_PASSWORD},
        )
        self.client.post(reverse("account_confirm_email", kwargs={"key": verification}))
        address.refresh_from_db()
        self.assertTrue(address.verified)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.login()
        self.assertNotIn("_auth_user_id", self.client.session)
        self.client.post(
            reverse("account_login"), {"login": self.user.email, "password": NEW_PASSWORD}
        )
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_challenge_without_password_stage_cannot_authenticate(self):
        self.activate()
        response = self.client.post(reverse("mfa_authenticate"), {"code": self.totp_code()})
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_totp_code_cannot_be_replayed(self):
        self.activate()
        fixed_time = 1800000000
        with patch("allauth.mfa.totp.internal.auth.time.time", return_value=fixed_time):
            code = format_hotp_value(hotp_value(TOTP_SECRET, fixed_time // 30))
            self.login()
            self.client.post(reverse("mfa_authenticate"), {"code": code})
            self.client.post(reverse("account_logout"))
            self.login()
            response = self.client.post(reverse("mfa_authenticate"), {"code": code})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_recovery_generation_shows_once_stores_only_hashes_and_regenerates(self):
        self.activate()
        self.login()
        self.client.post(reverse("mfa_authenticate"), {"code": self.totp_code()})
        response = self.client.post(reverse("recovery_codes"), {"action": "generate"})
        self.assertEqual(response.status_code, 200)
        codes = response.context["codes"]
        self.assertEqual(len(codes), 10)
        self.assertEqual(RecoveryCode.objects.filter(user=self.user).count(), 10)
        stored = list(RecoveryCode.objects.filter(user=self.user).values_list("digest", flat=True))
        for raw, digest in zip(codes, stored, strict=True):
            self.assertTrue(check_password(raw.replace("-", ""), digest))
            self.assertNotIn(raw, digest)
        self.assertNotIn(codes[0], str(dict(self.client.session)))
        get_response = self.client.get(reverse("recovery_codes"))
        self.assertIsNone(get_response.context["codes"])
        self.assertNotContains(get_response, codes[0])
        self.client.post(reverse("recovery_codes"), {"action": "generate"})
        self.assertFalse(consume_recovery_code(self.user, codes[0]))

    def test_recovery_code_authenticates_once_and_remains_user_scoped(self):
        self.activate()
        codes = generate_recovery_codes(self.user)
        other = get_user_model().objects.create_user(email="other@example.test", password=PASSWORD)
        self.assertFalse(consume_recovery_code(other, codes[0]))
        self.login()
        response = self.client.post(reverse("mfa_authenticate"), {"code": codes[0]})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)
        self.assertEqual(
            RecoveryCode.objects.filter(user=self.user, used_at__isnull=False).count(),
            1,
        )
        self.client.post(reverse("account_logout"))
        self.login()
        response = self.client.post(reverse("mfa_authenticate"), {"code": codes[0]})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_regeneration_between_hash_check_and_consumption_invalidates_old_code(self):
        self.activate()
        raw = generate_recovery_codes(self.user)[0]

        def delete_before_consume(*_args):
            RecoveryCode.objects.filter(user=self.user).delete()
            return True

        with patch("accounts.recovery.check_password", side_effect=delete_before_consume):
            self.assertFalse(consume_recovery_code(self.user, raw))

    def test_recovery_generation_requires_recent_authentication(self):
        self.activate()
        self.client.force_login(self.user)
        response = self.client.post(reverse("recovery_codes"), {"action": "generate"})
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("account_reauthenticate"), response["Location"])
        self.assertFalse(RecoveryCode.objects.filter(user=self.user).exists())

    def test_regeneration_revokes_other_sessions_and_preserves_current_session(self):
        self.activate()
        original = generate_recovery_codes(self.user)
        self.login()
        self.client.post(reverse("mfa_authenticate"), {"code": original[0]})
        other_client = Client()
        self.login(other_client)
        other_client.post(reverse("mfa_authenticate"), {"code": original[1]})
        response = self.client.post(reverse("recovery_codes"), {"action": "generate"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)
        self.assertEqual(other_client.get(reverse("dashboard")).status_code, 302)

    def test_recovery_code_can_reauthenticate_but_cannot_be_reused(self):
        self.activate()
        raw = generate_recovery_codes(self.user)[0]
        self.client.force_login(self.user)
        response = self.client.post(reverse("mfa_reauthenticate"), {"code": raw})
        self.assertEqual(response.status_code, 302)
        records = self.client.session["account_authentication_methods"]
        self.assertEqual(records[-1]["method"], "mfa")
        self.assertTrue(records[-1]["reauthenticated"])
        self.assertFalse(consume_recovery_code(self.user, raw))

    def test_disabling_totp_invalidates_recovery_codes(self):
        self.activate()
        raw = generate_recovery_codes(self.user)[0]
        self.login()
        self.client.post(reverse("mfa_authenticate"), {"code": self.totp_code()})
        response = self.client.post(reverse("mfa_deactivate_totp"))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Authenticator.objects.filter(user=self.user).exists())
        self.assertFalse(consume_recovery_code(self.user, raw))

    def test_recovery_generation_requires_totp(self):
        with self.assertRaises(ValueError):
            generate_recovery_codes(self.user)

    @override_settings(ACCOUNT_RATE_LIMITS={"login_failed": "3/m/key"})
    def test_mfa_challenge_rate_limit_blocks_correct_code_after_failures(self):
        self.activate()
        self.login()
        for _ in range(3):
            self.client.post(reverse("mfa_authenticate"), {"code": "incorrect"})
        response = self.client.post(reverse("mfa_authenticate"), {"code": self.totp_code()})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_encryption_key_rotation_decrypts_previous_key_and_rejects_plaintext(self):
        previous, current = (
            Fernet.generate_key().decode(),
            Fernet.generate_key().decode(),
        )
        with override_settings(MFA_ENCRYPTION_KEYS=[previous]):
            encrypted = EncryptedMFAAdapter().encrypt(TOTP_SECRET)
        with override_settings(MFA_ENCRYPTION_KEYS=[current, previous]):
            self.assertEqual(EncryptedMFAAdapter().decrypt(encrypted), TOTP_SECRET)
            new_encrypted = EncryptedMFAAdapter().encrypt(TOTP_SECRET)
            self.assertEqual(
                Fernet(current.encode()).decrypt(new_encrypted.encode()).decode(),
                TOTP_SECRET,
            )
        with self.assertRaises(InvalidToken):
            EncryptedMFAAdapter().decrypt(TOTP_SECRET)
