from allauth.account.forms import LoginForm as AllauthLoginForm
from allauth.account.forms import ResetPasswordForm as AllauthResetPasswordForm
from allauth.account.forms import SignupForm as AllauthSignupForm
from django import forms

from .audit import record
from .models import User


class SignupForm(AllauthSignupForm):
    full_name = forms.CharField(
        label="Full name", max_length=100, widget=forms.TextInput(attrs={"autocomplete": "name"})
    )
    field_order = ["full_name", "email", "password1", "password2"]

    def clean_email(self):
        self.cleaned_data["email"] = User.objects.normalize_email(self.cleaned_data["email"])
        return super().clean_email()

    def signup(self, request, user):
        user.full_name = self.cleaned_data["full_name"].strip()
        user.save(update_fields=["full_name"])


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["full_name"]
        widgets = {"full_name": forms.TextInput(attrs={"autocomplete": "name"})}


class LoginForm(AllauthLoginForm):
    def login(self, request, redirect_url=None):
        response = super().login(request, redirect_url=redirect_url)
        if not self.cleaned_data.get("remember"):
            request.session.set_expiry(3600)
        return response


class ResetPasswordForm(AllauthResetPasswordForm):
    def save(self, request, **kwargs):
        record("password_reset_requested")
        return super().save(request, **kwargs)


class ResendVerificationForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={"autocomplete": "email"}))
