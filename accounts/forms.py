from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)
from django.template import loader

from .models import User
from .tasks import send_email

INPUT_CLASSES = (
    "flex h-9 w-full rounded-md border border-gray-200 bg-transparent px-3 py-1 "
    "text-sm shadow-sm transition-colors placeholder:text-gray-400 "
    "focus-visible:border-teal-500 focus-visible:ring-2 focus-visible:ring-teal-500/30 "
    "focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50"
)
CHECKBOX_CLASSES = (
    "h-4 w-4 text-teal-600 border-gray-300 rounded focus:ring-teal-500"
)
FILE_CLASSES = (
    "block w-full text-sm text-gray-700 "
    "file:mr-4 file:rounded-md file:border-0 file:bg-teal-600 file:px-4 file:py-2 "
    "file:text-sm file:font-medium file:text-white hover:file:bg-teal-700"
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
            elif isinstance(widget, forms.ClearableFileInput):
                widget.attrs.setdefault("class", FILE_CLASSES)
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

    def send_mail(
        self,
        subject_template_name,
        email_template_name,
        context,
        from_email,
        to_email,
        html_email_template_name=None,
    ):
        subject = "".join(
            loader.render_to_string(subject_template_name, context).splitlines()
        )
        body = loader.render_to_string(email_template_name, context)
        send_email.delay(subject, body, from_email, [to_email])


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


class ProfileForm(StyledFormMixin, forms.ModelForm):
    labels = {
        "username": "Nom d'utilisateur",
        "first_name": "Prénom",
        "last_name": "Nom",
        "email": "Email",
        "avatar": "Photo de profil",
    }

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "avatar")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True

    def save(self, commit=True):
        old_avatar = None
        if self.instance.pk and "avatar" in self.changed_data:
            old_avatar = (
                User.objects.filter(pk=self.instance.pk)
                .values_list("avatar", flat=True)
                .first()
            )

        user = super().save(commit=commit)

        if commit and old_avatar and old_avatar != user.avatar.name:
            user.avatar.storage.delete(old_avatar)

        return user


class DeleteAccountForm(StyledFormMixin, forms.Form):
    password = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput,
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.user.check_password(password):
            raise forms.ValidationError("Mot de passe incorrect.")
        return password
