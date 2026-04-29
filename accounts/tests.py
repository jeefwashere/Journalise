from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from unittest.mock import patch

from .models import UserProfile
from .serializers import UserSerializer
from .tokens import create_access_token

User = get_user_model()


class UserSerializerTests(TestCase):
    def test_serializes_oauth_safe_user_fields(self):
        user = User.objects.create_user(
            username="test",
            email="test@example.com",
            first_name="Test",
            last_name="Subject",
            password="secret-pass",
        )
        UserProfile.objects.create(
            user=user,
            display_name="Test S.",
            avatar_url="https://example.com/avatar.png",
        )

        data = UserSerializer(user).data

        self.assertEqual(data["sub"], str(user.pk))
        self.assertEqual(data["preferred_username"], "test")
        self.assertEqual(data["name"], "Test S.")
        self.assertEqual(data["picture"], "https://example.com/avatar.png")
        self.assertNotIn("password", data)
        self.assertNotIn("is_staff", data)
        self.assertNotIn("is_superuser", data)

    def test_updates_nested_profile(self):
        user = User.objects.create_user(username="sam", password="secret-pass")

        serializer = UserSerializer(
            user,
            data={
                "first_name": "Sam",
                "profile": {
                    "display_name": "Sammy",
                    "avatar_url": "https://example.com/sam.png",
                },
            },
            partial=True,
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

        user.refresh_from_db()
        self.assertEqual(user.first_name, "Sam")
        self.assertEqual(user.profile.display_name, "Sammy")
        self.assertEqual(user.profile.avatar_url, "https://example.com/sam.png")


class CurrentUserViewTests(TestCase):
    def test_returns_authenticated_user_for_react_page_with_session(self):
        user = User.objects.create_user(
            username="react-user",
            email="react@example.com",
            password="secret-pass",
        )
        UserProfile.objects.create(
            user=user,
            display_name="React User",
            avatar_url="https://example.com/react.png",
        )

        self.client.force_login(user)

        response = self.client.get(reverse("current-user"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["sub"], str(user.pk))
        self.assertEqual(response.json()["preferred_username"], "react-user")
        self.assertEqual(response.json()["email"], "react@example.com")
        self.assertEqual(response.json()["name"], "React User")
        self.assertEqual(response.json()["picture"], "https://example.com/react.png")
        self.assertEqual(response.json()["profile"]["display_name"], "React User")

    def test_returns_authenticated_user_for_desktop_app_with_bearer_token(self):
        user = User.objects.create_user(
            username="desktop-user",
            email="desktop@example.com",
            password="secret-pass",
        )
        access_token, _ = create_access_token(user)

        response = self.client.get(
            reverse("current-user"),
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["sub"], str(user.pk))
        self.assertEqual(response.json()["preferred_username"], "desktop-user")

    def test_current_user_view_requires_authentication(self):
        response = self.client.get(reverse("current-user"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@override_settings(GOOGLE_OAUTH_CLIENT_ID="google-client-id")
class GoogleLoginViewTests(TestCase):
    @patch("accounts.views.verify_google_id_token")
    def test_google_login_creates_user_and_returns_access_token(self, verify_token):
        verify_token.return_value = {
            "sub": "google-subject",
            "email": "google@example.com",
            "email_verified": True,
            "given_name": "Google",
            "family_name": "User",
            "name": "Google User",
            "picture": "https://example.com/google.png",
        }

        response = self.client.post(
            reverse("google-login"),
            data={"id_token": "google-id-token"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        user = User.objects.get(email="google@example.com")

        self.assertEqual(data["token_type"], "Bearer")
        self.assertIn("access_token", response.cookies)

        cookie = response.cookies["access_token"]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")

        self.assertEqual(data["expires_in"], 1800)
        self.assertEqual(data["user"]["sub"], str(user.pk))
        self.assertEqual(user.username, "google")
        self.assertEqual(user.first_name, "Google")
        self.assertEqual(user.last_name, "User")
        self.assertEqual(user.profile.display_name, "Google User")
        self.assertEqual(user.profile.avatar_url, "https://example.com/google.png")

    @patch("accounts.views.verify_google_id_token")
    def test_google_login_reuses_existing_user_by_email(self, verify_token):
        existing_user = User.objects.create_user(
            username="existing",
            email="google@example.com",
            password="secret-pass",
        )
        verify_token.return_value = {
            "sub": "google-subject",
            "email": "google@example.com",
            "email_verified": True,
            "name": "Google User",
        }

        response = self.client.post(
            reverse("google-login"),
            data={"id_token": "google-id-token"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["user"]["sub"], str(existing_user.pk))
        self.assertEqual(User.objects.count(), 1)
