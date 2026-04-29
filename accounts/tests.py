from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import UserProfile
from .serializers import UserSerializer

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
