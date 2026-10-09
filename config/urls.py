from django.urls import include, path

from accounts import views
from accounts.recovery import RecoveryCodesView

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("settings/", views.profile, name="profile"),
    path("sessions/", views.sessions, name="sessions"),
    path("sessions/revoke/", views.revoke_sessions, name="sessions_revoke"),
    path("security/recovery-codes/", RecoveryCodesView.as_view(), name="recovery_codes"),
    path("about/", views.about, name="about"),
    path("verification/resend/", views.resend_verification, name="resend_verification"),
    path("health/", views.health, name="health"),
    path("accounts/signup/", views.SafeSignupView.as_view(), name="account_signup"),
    path("accounts/sessions/", views.sessions, name="usersessions_list"),
    path("accounts/", include("allauth.urls")),
]
handler403 = "accounts.views.error403"
handler404 = "accounts.views.error404"
handler500 = "accounts.views.error500"
handler429 = "accounts.views.error429"
