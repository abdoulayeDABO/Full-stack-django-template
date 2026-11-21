from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)

from .models import User

INPUT_CLASSES = (
    "flex h-9 w-full rounded-md border border-gray-200 bg-transparent px-3 py-1 "
    "text-sm shadow-sm transition-colors placeholder:text-gray-400 "
    "focus-visible:border-teal-500 focus-visible:ring-2 focus-visible:ring-teal-500/30 "
    "focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50"
)
CHECKBOX_CLASSES = (
    "h-4 w-4 text-teal-600 border-gray-300 rounded focus:ring-teal-500"
)


class StyledFormMixin:
    labels = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, label in self.labels.items():
            if name in self.fields:
                self.fields[name].label = label
        for name, field in self.fields.items():
            widget = field.widget
            if name == "username" or getattr(widget, "input_type", None) == "password":
                field.help_text = ""
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", CHECKBOX_CLASSES)
            else:
                widget.attrs.setdefault("class", INPUT_CLASSES)


class SignupForm(StyledFormMixin, UserCreationForm):
    email = forms.EmailField(required=True)
    labels = {
        "username": "Nom d'utilisateur",
        "email": "Email",
        "password1": "Mot de passe",
        "password2": "Confirmation du mot de passe",
    }

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")


class StyledAuthenticationForm(StyledFormMixin, AuthenticationForm):
    labels = {"username": "Nom d'utilisateur", "password": "Mot de passe"}


class StyledPasswordResetForm(StyledFormMixin, PasswordResetForm):
    labels = {"email": "Email"}


class StyledSetPasswordForm(StyledFormMixin, SetPasswordForm):
    labels = {
        "new_password1": "Nouveau mot de passe",
        "new_password2": "Confirmation du nouveau mot de passe",
    }


class StyledPasswordChangeForm(StyledFormMixin, PasswordChangeForm):
    labels = {
        "old_password": "Mot de passe actuel",
        "new_password1": "Nouveau mot de passe",
        "new_password2": "Confirmation du nouveau mot de passe",
    }
