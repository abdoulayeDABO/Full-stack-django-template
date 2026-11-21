import io
import shutil
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

User = get_user_model()

PASSWORD = "SuperSecret123!"


class SignupTests(TestCase):
    def test_page_renders(self):
        response = self.client.get(reverse("signup"))
        self.assertEqual(response.status_code, 200)

    def test_creates_user_and_logs_in(self):
        response = self.client.post(
            reverse("signup"),
            {
                "username": "alice",
                "email": "alice@example.com",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )
        self.assertRedirects(response, reverse("index"))
        user = User.objects.get(username="alice")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)


class LoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("bob", password=PASSWORD)

    def test_page_renders(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)

    def test_valid_credentials(self):
        response = self.client.post(
            reverse("login"), {"username": "bob", "password": PASSWORD}
        )
        self.assertRedirects(response, reverse("profile"))


class ProfileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("erin", password=PASSWORD)

    def test_requires_login(self):
        response = self.client.get(reverse("profile"))
        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('profile')}",
        )

    def test_page_renders(self):
        self.client.login(username="erin", password=PASSWORD)
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mon profil")
        self.assertContains(response, "Modifier le profil")
        self.assertContains(response, "Zone de danger")
        self.assertNotContains(response, "Currently:")

    def test_updates_profile(self):
        self.client.login(username="erin", password=PASSWORD)
        response = self.client.post(
            reverse("profile"),
            {
                "username": "erin",
                "first_name": "Erin",
                "last_name": "Doe",
                "email": "erin@example.com",
            },
        )
        self.assertRedirects(response, reverse("profile"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Erin")
        self.assertEqual(self.user.last_name, "Doe")
        self.assertEqual(self.user.email, "erin@example.com")


class ProfileImageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("gina", password=PASSWORD)
        self.client.login(username="gina", password=PASSWORD)
        self.media_dir = tempfile.mkdtemp()
        self.override = override_settings(
            MEDIA_ROOT=self.media_dir,
            STORAGES={
                "default": {
                    "BACKEND": "django.core.files.storage.FileSystemStorage",
                    "OPTIONS": {"location": self.media_dir},
                },
                "staticfiles": {
                    "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
                },
            },
        )
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(shutil.rmtree, self.media_dir, True)

    def _png(self):
        buffer = io.BytesIO()
        Image.new("RGB", (10, 10), "teal").save(buffer, format="PNG")
        return SimpleUploadedFile(
            "avatar.png", buffer.getvalue(), content_type="image/png"
        )

    def _post_avatar(self):
        return self.client.post(
            reverse("profile"),
            {
                "username": "gina",
                "first_name": "",
                "last_name": "",
                "email": "gina@example.com",
                "avatar": self._png(),
            },
        )

    def test_upload_avatar(self):
        response = self._post_avatar()
        self.assertRedirects(response, reverse("profile"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.avatar)

    def test_replacing_avatar_deletes_old_file(self):
        self._post_avatar()
        self.user.refresh_from_db()
        storage = self.user.avatar.storage
        old_name = self.user.avatar.name
        self.assertTrue(storage.exists(old_name))

        self._post_avatar()
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.avatar.name, old_name)
        self.assertFalse(storage.exists(old_name))
        self.assertTrue(storage.exists(self.user.avatar.name))


class DeleteAccountTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("frank", password=PASSWORD)
        self.client.login(username="frank", password=PASSWORD)

    def test_wrong_password_keeps_account(self):
        response = self.client.post(
            reverse("delete_account"), {"password": "WrongPass123!"}
        )
        self.assertRedirects(response, reverse("profile"))
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_deleted)
        self.assertTrue(self.user.is_active)

    def test_soft_deletes_account(self):
        response = self.client.post(reverse("delete_account"), {"password": PASSWORD})
        self.assertRedirects(response, reverse("index"))

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_deleted)
        self.assertFalse(self.user.is_active)

        login_response = self.client.post(
            reverse("login"), {"username": "frank", "password": PASSWORD}
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_get_not_allowed(self):
        response = self.client.get(reverse("delete_account"))
        self.assertEqual(response.status_code, 405)


class PasswordResetTests(TestCase):
    def setUp(self):
        User.objects.create_user(
            "carol", email="carol@example.com", password=PASSWORD
        )

    @patch("accounts.forms.send_email.delay")
    def test_enqueues_reset_email(self, delay):
        response = self.client.post(
            reverse("password_reset"), {"email": "carol@example.com"}
        )
        self.assertRedirects(response, reverse("password_reset_done"))
        delay.assert_called_once()
        subject, body, from_email, recipients = delay.call_args.args
        self.assertIn("/accounts/reset/", body)
        self.assertEqual(recipients, ["carol@example.com"])


class CeleryEmailTaskTests(TestCase):
    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"
    )
    def test_send_email_task_sends_mail(self):
        from accounts.tasks import send_email

        result = send_email.apply(
            args=("Sujet", "Corps", "from@example.com", ["to@example.com"])
        )
        self.assertTrue(result.successful())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Sujet")


class PasswordChangeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("dave", password=PASSWORD)

    def test_requires_login(self):
        response = self.client.get(reverse("password_change"))
        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('password_change')}",
        )

    def test_changes_password(self):
        self.client.login(username="dave", password=PASSWORD)
        response = self.client.post(
            reverse("password_change"),
            {
                "old_password": PASSWORD,
                "new_password1": "NewSecret456!",
                "new_password2": "NewSecret456!",
            },
        )
        self.assertRedirects(response, reverse("password_change_done"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewSecret456!"))
