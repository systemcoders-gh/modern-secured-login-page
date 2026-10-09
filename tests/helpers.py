import re
from urllib.parse import urlsplit

from allauth.account.models import EmailAddress
from django.core.cache import cache
from django.test import TestCase, override_settings

from accounts.models import User

PASSWORD = "Lanterns above the quiet harbor at sunrise 2026"
NEW_PASSWORD = "Paper airplanes drifting over the autumn orchard 2026"


def email_path(message, fragment):
    url = re.search(r"https?://[^\s<>]+" + fragment + r"[^\s<>]+", message.body)
    if not url:
        raise AssertionError("Expected authentication link in email.")
    return urlsplit(url.group(0)).path


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AuthTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.user = self.create_user("learner@example.test", "Ada Learner")

    def create_user(self, email, name, verified=True):
        user = User.objects.create_user(email=email, full_name=name, password=PASSWORD)
        EmailAddress.objects.create(user=user, email=user.email, primary=True, verified=verified)
        return user

    def login(self, client=None, remember=False):
        return (client or self.client).post(
            "/accounts/login/",
            {"login": self.user.email, "password": PASSWORD, "remember": remember},
        )
