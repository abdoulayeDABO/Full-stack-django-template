from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

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
        self.assertContains(response, "Zone de danger")

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

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"
    )
    def test_sends_reset_email(self):
        response = self.client.post(
            reverse("password_reset"), {"email": "carol@example.com"}
        )
        self.assertRedirects(response, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/accounts/reset/", mail.outbox[0].body)


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
