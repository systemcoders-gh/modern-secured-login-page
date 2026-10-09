"""Real browser journeys use disposable Django databases and synthetic mail only."""

import os
import time
from unittest import skipUnless

from allauth.account.models import EmailAddress
from allauth.mfa.totp.internal.auth import format_hotp_value, hotp_value
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from playwright.sync_api import expect, sync_playwright

from accounts.models import User
from tests.helpers import NEW_PASSWORD, PASSWORD, email_path


@skipUnless(
    os.environ.get("SKIP_BROWSER_TESTS", "1") == "0",
    "Run browser suite explicitly with SKIP_BROWSER_TESTS=0",
)
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class BrowserJourneys(StaticLiveServerTestCase):
    def setUp(self):
        cache.clear()
        # Create ORM fixtures before Playwright starts its synchronous event loop.
        # Stop that loop in tearDown before Django flushes the disposable database.
        self.create_verified("existing@example.test")
        self.playwright = sync_playwright().start()
        options = {"headless": True}
        if os.environ.get("BROWSER_EXECUTABLE"):
            options["executable_path"] = os.environ["BROWSER_EXECUTABLE"]
        self.browser = self.playwright.chromium.launch(**options)
        self.context = self.browser.new_context(viewport={"width": 1440, "height": 1000})
        self.page = self.context.new_page()
        self.page.set_default_timeout(5000)
        self.errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.page.on(
            "console",
            lambda message: self.errors.append(message.text) if message.type == "error" else None,
        )
        self.origin_override = override_settings(APP_ORIGIN=self.live_server_url)
        self.origin_override.enable()

    def tearDown(self):
        self.context.close()
        self.browser.close()
        self.playwright.stop()
        self.origin_override.disable()
        self.assertEqual(self.errors, [])

    def screenshot(self, name):
        if os.environ.get("SAVE_SCREENSHOTS") == "1":
            from pathlib import Path

            from django.conf import settings

            target = Path(settings.BASE_DIR) / "docs" / "screenshots" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            self.page.screenshot(path=str(target), full_page=True)

    def create_verified(self, email="browser@example.test"):
        user = User.objects.create_user(email=email, full_name="Browser Learner", password=PASSWORD)
        EmailAddress.objects.create(user=user, email=email, verified=True, primary=True)
        return user

    def sign_in(self, page=None, email="existing@example.test", password=PASSWORD):
        page = page or self.page
        page.goto(self.live_server_url + "/accounts/login/")
        page.get_by_label("Email", exact=True).fill(email)
        page.get_by_label("Password", exact=True).fill(password)
        page.get_by_role("button", name="Sign in", exact=True).click()

    def test_registration_verification_and_password_recovery(self):
        page = self.page
        page.goto(self.live_server_url + "/accounts/signup/")
        page.get_by_label("Full name").fill("Browser Learner")
        page.get_by_label("Email", exact=True).fill("browser@example.test")
        page.locator("#id_password1").fill(PASSWORD)
        page.locator("#id_password2").fill(PASSWORD)
        page.get_by_role("button", name="Create account").click()
        expect(page).to_have_url(self.live_server_url + "/accounts/confirm-email/")
        page.goto(self.live_server_url + email_path(mail.outbox[0], "/accounts/confirm-email/"))
        page.get_by_role("button", name="Verify email", exact=True).click()
        self.sign_in(email="browser@example.test")
        expect(page.get_by_text("You have successfully logged in!", exact=True)).to_be_visible()
        self.screenshot("dashboard-desktop.png")
        page.get_by_role("link", name="Sign out", exact=True).click()
        page.get_by_role("button", name="Sign out", exact=True).click()
        page.goto(self.live_server_url + "/accounts/password/reset/")
        page.get_by_label("Email", exact=True).fill("browser@example.test")
        page.get_by_role("button", name="Send reset link").click()
        expect(page).to_have_url(self.live_server_url + "/accounts/password/reset/done/")
        message = next(
            message
            for message in reversed(mail.outbox)
            if "/accounts/password/reset/key/" in message.body
        )
        page.goto(self.live_server_url + email_path(message, "/accounts/password/reset/key/"))
        page.locator("#id_password1").fill(NEW_PASSWORD)
        page.locator("#id_password2").fill(NEW_PASSWORD)
        page.get_by_role("button", name="Reset password", exact=True).click()
        expect(page.get_by_role("heading", name="You're ready to return.")).to_be_visible()
        self.sign_in(email="browser@example.test", password=NEW_PASSWORD)
        expect(page.get_by_text("You have successfully logged in!", exact=True)).to_be_visible()

    def test_mfa_enrollment_recovery_login_and_session_revocation(self):
        page = self.page
        self.sign_in()
        page.goto(self.live_server_url + "/accounts/2fa/totp/activate/")
        secret = page.locator("#authenticator_secret").input_value()
        # Move away from a boundary so enrollment and submission use the same 30s period.
        if time.time() % 30 > 27:
            time.sleep(3)
        code = format_hotp_value(hotp_value(secret, int(time.time()) // 30))
        page.get_by_label("Authenticator code").fill(code)
        page.get_by_role("button", name="Enable authenticator").click()
        expect(page).to_have_url(self.live_server_url + "/accounts/2fa/")
        page.goto(self.live_server_url + "/security/recovery-codes/")
        page.get_by_role("button", name="Generate recovery codes", exact=True).click()
        expect(page.locator(".recovery-grid li")).to_have_count(10)
        recovery_code = page.locator(".recovery-grid li").first.inner_text()
        second_code = page.locator(".recovery-grid li").nth(1).inner_text()
        sibling_context = self.browser.new_context()
        try:
            sibling = sibling_context.new_page()
            self.sign_in(sibling)
            expect(sibling).to_have_url(self.live_server_url + "/accounts/2fa/authenticate/")
            sibling.get_by_label("Code", exact=True).fill(recovery_code)
            sibling.get_by_role("button", name="Verify & sign in").click()
            expect(
                sibling.get_by_text("You have successfully logged in!", exact=True)
            ).to_be_visible()
            page.goto(self.live_server_url + "/sessions/")
            page.get_by_role("button", name="Sign out other sessions").click()
            expect(page).to_have_url(self.live_server_url + "/sessions/")
            sibling.goto(self.live_server_url + "/")
            expect(sibling).to_have_url(self.live_server_url + "/accounts/login/?next=/")
            self.sign_in(sibling)
            sibling.get_by_label("Code", exact=True).fill(recovery_code)
            sibling.get_by_role("button", name="Verify & sign in").click()
            expect(sibling.locator(".error-summary")).to_be_visible()
            sibling.get_by_label("Code", exact=True).fill(second_code)
            sibling.get_by_role("button", name="Verify & sign in").click()
            expect(
                sibling.get_by_text("You have successfully logged in!", exact=True)
            ).to_be_visible()
        finally:
            sibling_context.close()

    def test_responsive_themes_keyboard_and_accessibility_structure(self):
        page = self.page
        for width in [320, 375, 768, 1440]:
            page.set_viewport_size({"width": width, "height": 900})
            page.goto(self.live_server_url + "/accounts/login/")
            self.assertTrue(page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
            expect(page.get_by_role("heading", level=1)).to_be_visible()
            self.assertEqual(page.get_by_role("main").count(), 1)
            page.get_by_role("button", name="Switch to dark theme").click()
            expect(page.locator("html")).to_have_attribute("data-theme", "dark")
            page.reload()
            expect(page.locator("html")).to_have_attribute("data-theme", "dark")
            page.get_by_role("button", name="Switch to light theme").click()
            for label in ["Email", "Password"]:
                expect(page.get_by_label(label, exact=True)).to_be_visible()
            targets = page.locator(
                ".theme-toggle,.password-toggle,button[type=submit]"
            ).evaluate_all(
                "elements => elements.map(e => ({w:e.getBoundingClientRect().width,h:e.getBoundingClientRect().height}))"
            )
            self.assertTrue(all(size["w"] >= 44 and size["h"] >= 44 for size in targets))
        page.goto(self.live_server_url + "/accounts/login/")
        page.keyboard.press("Tab")
        expect(page.get_by_role("link", name="Skip to content")).to_be_focused()
        page.get_by_label("Password", exact=True).fill("synthetic display sample")
        page.get_by_role("button", name="Show password", exact=True).click()
        expect(page.get_by_label("Password", exact=True)).to_have_attribute("type", "text")
        page.get_by_role("button", name="Hide password", exact=True).click()
        expect(page.get_by_label("Password", exact=True)).to_have_attribute("type", "password")
        page.emulate_media(reduced_motion="reduce")
        self.assertEqual(
            page.locator(".vault-card").evaluate("e => getComputedStyle(e).animationName"), "none"
        )

    def test_browser_csrf_invalid_credentials_and_direct_route_guard(self):
        self.page.goto(self.live_server_url + "/")
        expect(self.page).to_have_url(self.live_server_url + "/accounts/login/?next=/")
        self.sign_in(password="wrong password")
        expect(self.page.locator(".error-summary")).to_be_visible()
        response = self.context.request.post(
            self.live_server_url + "/accounts/login/",
            form={"login": "browser@example.test", "password": PASSWORD},
        )
        self.assertEqual(response.status, 403)
