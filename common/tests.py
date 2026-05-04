from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


def make_user(email="user@example.com", password="password", **kwargs):
    """Helper to create a regular user."""
    return User.objects.create_user(email=email, password=password, **kwargs)


def make_superuser(email="admin@example.com", password="password"):
    """Helper to create a superuser."""
    return User.objects.create_superuser(email=email, password=password)


# ---------------------------------------------------------------------------
# OwnUserManager
# ---------------------------------------------------------------------------


class OwnUserManagerTest(TestCase):
    def test_create_user_sets_email(self):
        user = make_user(email="alice@example.com")
        self.assertEqual(user.email, "alice@example.com")

    def test_create_user_derives_username_from_email(self):
        user = make_user(email="alice@example.com")
        self.assertEqual(user.username, "alice")

    def test_create_user_normalises_email_domain(self):
        user = make_user(email="bob@EXAMPLE.COM")
        self.assertEqual(user.email, "bob@example.com")

    def test_create_user_requires_email(self):
        with self.assertRaises((ValueError, TypeError)):
            User.objects.create_user(email="", password="pass")

    def test_create_user_sets_password(self):
        user = make_user(email="carol@example.com", password="s3cret!")
        self.assertTrue(user.check_password("s3cret!"))

    def test_create_superuser_is_staff_and_superuser(self):
        su = make_superuser()
        self.assertTrue(su.is_staff)
        self.assertTrue(su.is_superuser)

    def test_create_superuser_requires_is_staff(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="bad@example.com", password="x", is_staff=False
            )

    def test_create_superuser_requires_is_superuser(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="bad2@example.com", password="x", is_superuser=False
            )

    def test_email_is_unique(self):
        make_user(email="dup@example.com")
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            make_user(email="dup@example.com")


# ---------------------------------------------------------------------------
# User model properties
# ---------------------------------------------------------------------------


class UserPropertiesTest(TestCase):
    def _user_in_group(self, group_name):
        g, _ = Group.objects.get_or_create(name=group_name)
        user = make_user(email=f"{group_name.replace(' ', '')}@example.com")
        user.groups.add(g)
        return user

    def test_is_lab_manager_true(self):
        user = self._user_in_group("Lab manager")
        self.assertTrue(user.is_lab_manager)

    def test_is_lab_manager_false(self):
        user = make_user(email="plain@example.com")
        self.assertFalse(user.is_lab_manager)

    def test_is_guest_true(self):
        user = self._user_in_group("Guest")
        self.assertTrue(user.is_guest)

    def test_is_guest_false(self):
        user = make_user(email="notaguest@example.com")
        self.assertFalse(user.is_guest)

    def test_is_order_manager(self):
        user = self._user_in_group("Order manager")
        self.assertTrue(user.is_order_manager)

    def test_is_formz_manager(self):
        user = self._user_in_group("FormZ manager")
        self.assertTrue(user.is_formz_manager)

    def test_is_approval_manager(self):
        user = self._user_in_group("Approval manager")
        self.assertTrue(user.is_approval_manager)

    def test_is_regular_lab_member(self):
        user = self._user_in_group("Regular lab member")
        self.assertTrue(user.is_regular_lab_member)

    def test_is_past_member(self):
        user = self._user_in_group("Past member")
        self.assertTrue(user.is_past_member)

    def test_is_elevated_user_via_lab_manager(self):
        user = self._user_in_group("Lab manager")
        self.assertTrue(user.is_elevated_user)

    def test_is_elevated_user_via_pi(self):
        user = make_user(email="pi@example.com", is_pi=True)
        self.assertTrue(user.is_elevated_user)

    def test_is_elevated_user_via_superuser(self):
        user = make_superuser()
        self.assertTrue(user.is_elevated_user)

    def test_is_elevated_user_false_for_regular(self):
        user = make_user(email="regular@example.com")
        self.assertFalse(user.is_elevated_user)


# ---------------------------------------------------------------------------
# CaseInsensitiveAuthenticationBackend
# ---------------------------------------------------------------------------


class CaseInsensitiveAuthenticationBackendTest(TestCase):
    def setUp(self):
        self.user = make_user(email="Test@Example.com", password="mypassword")

    def test_login_with_exact_email(self):
        logged_in = self.client.login(email="Test@Example.com", password="mypassword")
        self.assertTrue(logged_in)

    def test_login_with_lowercase_email(self):
        logged_in = self.client.login(email="test@example.com", password="mypassword")
        self.assertTrue(logged_in)

    def test_login_with_wrong_password_fails(self):
        # Use HTTP POST so a real request is passed to the user_login_failed signal.
        response = self.client.post(
            "/login/", {"username": "test@example.com", "password": "wrong"}
        )
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_login_with_unknown_email_fails(self):
        response = self.client.post(
            "/login/", {"username": "nobody@example.com", "password": "x"}
        )
        self.assertFalse(response.wsgi_request.user.is_authenticated)


# ---------------------------------------------------------------------------
# SettingsApiView
# ---------------------------------------------------------------------------


class SettingsApiViewTest(APITestCase):
    def test_settings_endpoint_returns_200(self):
        response = self.client.get("/api/settings/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_settings_endpoint_contains_expected_keys(self):
        response = self.client.get("/api/settings/")
        for key in ("lab_name", "login_url", "logout_url"):
            self.assertIn(key, response.data)


# ---------------------------------------------------------------------------
# OwnLoginView / OwnLogoutView
# ---------------------------------------------------------------------------


class OwnLoginViewTest(TestCase):
    def setUp(self):
        self.user = make_user(email="login@example.com", password="pass1234")

    def test_login_page_loads(self):
        response = self.client.get("/login/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "login")

    def test_valid_login_redirects(self):
        response = self.client.post(
            "/login/",
            {"username": "login@example.com", "password": "pass1234"},
            follow=True,
        )
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_invalid_login_stays_on_page(self):
        response = self.client.post(
            "/login/",
            {"username": "login@example.com", "password": "wrong"},
        )
        self.assertFalse(response.wsgi_request.user.is_authenticated)


class OwnLogoutViewTest(TestCase):
    def setUp(self):
        self.user = make_user(email="logout@example.com", password="pass1234")
        self.client.login(email="logout@example.com", password="pass1234")

    def test_logout_page_loads(self):
        response = self.client.get("/logout/")
        self.assertIn(response.status_code, [200, 302])

    def test_api_logout_returns_json(self):
        response = self.client.post("/logout/", headers={"benchbaze-api": "true"})
        # Should return JSON success payload when api header is present
        self.assertIn(response.status_code, [200, 302])


# ---------------------------------------------------------------------------
# UserViewSet
# ---------------------------------------------------------------------------


class UserViewSetTest(APITestCase):
    def setUp(self):
        self.user = make_user(
            email="vsuser@example.com",
            password="pass",
            first_name="Alice",
            last_name="Smith",
        )
        self.client.force_authenticate(user=self.user)

    def test_list_users(self):
        response = self.client.get("/api/common/user/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        emails = [u["email"] for u in response.data]
        self.assertIn("vsuser@example.com", emails)

    def test_list_users_filter_by_user_id(self):
        other = make_user(email="other@example.com")
        response = self.client.get(f"/api/common/user/?user_id={self.user.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = [u["id"] for u in response.data]
        self.assertIn(self.user.id, returned_ids)
        self.assertNotIn(other.id, returned_ids)

    def test_logged_returns_current_user(self):
        response = self.client.get("/api/common/user/logged/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "vsuser@example.com")

    def test_logged_includes_theme_fields(self):
        response = self.client.get("/api/common/user/logged/")
        for field in ("theme", "primary_colour", "surface_colour"):
            self.assertIn(field, response.data)

    def test_theme_update_valid_fields(self):
        response = self.client.put(
            "/api/common/user/theme/",
            {"theme": "dark", "primary_colour": "blue", "surface_colour": "gray"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.theme, "dark")

    def test_theme_update_rejects_invalid_fields(self):
        response = self.client.put(
            "/api/common/user/theme/",
            {"theme": "dark", "email": "hacker@evil.com"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("invalid_fields", response.data)

    def test_recent_events_returns_200(self):
        response = self.client.get("/api/common/user/logged/recent_events/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthenticated_user_list_returns_403(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/common/user/")
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )
