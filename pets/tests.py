from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from accounts.models import UserProfile

from .choices import PetMood
from .models import Pet

User = get_user_model()


class PetViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="pet-user",
            email="pet@example.com",
            password="secret-pass",
        )
        self.client.force_authenticate(user=self.user)

    def test_pet_list_requires_authentication(self):
        response = APIClient().get(reverse("pet-list"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_pet_list_returns_available_pets_in_model_order(self):
        response = self.client.get(reverse("pet-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 36)
        neutral_cat = next(
            item
            for item in response.data
            if item["pet_type"] == Pet.PetType.CAT
            and item["level"] == 1
            and item["mood"] == PetMood.NEUTRAL
        )
        self.assertEqual(neutral_cat["pet_type_display"], "Cat")
        self.assertEqual(neutral_cat["mood_display"], "Neutral")
        self.assertEqual(neutral_cat["svg_path"], "pets/cat-1-neutral.svg")

    def test_pet_detail_returns_pet(self):
        pet, _ = Pet.objects.get_or_create(
            pet_type=Pet.PetType.FROG,
            level=1,
            mood=PetMood.NEUTRAL,
            defaults={"name": "Bunny", "svg_path": "pets/frog-1-neutral.svg"},
        )

        response = self.client.get(reverse("pet-detail", kwargs={"pk": pet.pk}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], pet.pk)
        self.assertEqual(response.data["pet_type"], Pet.PetType.FROG)
        self.assertEqual(response.data["pet_type_display"], "Bunny")
        self.assertEqual(response.data["mood"], PetMood.NEUTRAL)
        self.assertEqual(response.data["name"], "Bunny")

    def test_pet_mood_view_requires_authentication(self):
        response = APIClient().post(
            reverse("pet-mood"),
            {"action": "activity_completed"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_pet_mood_view_updates_mood_from_user_action(self):
        neutral_pet = Pet.objects.get(
            pet_type=Pet.PetType.CAT,
            level=1,
            mood=PetMood.NEUTRAL,
        )
        happy_pet = Pet.objects.get(
            pet_type=Pet.PetType.CAT,
            level=1,
            mood=PetMood.HAPPY,
        )
        UserProfile.objects.create(user=self.user, current_pet=neutral_pet)

        response = self.client.post(
            reverse("pet-mood"),
            {"action": "activity_completed"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["pet_mood"], PetMood.HAPPY)
        self.assertEqual(response.data["pet_mood_display"], "Happy")
        self.assertEqual(response.data["current_pet"]["id"], happy_pet.pk)
        self.assertEqual(response.data["current_pet"]["mood"], PetMood.HAPPY)
        self.assertEqual(response.data["current_pet"]["svg_path"], "pets/cat-1-happy.svg")

        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.pet_mood, PetMood.HAPPY)
        self.assertEqual(profile.current_pet, happy_pet)

    def test_pet_mood_view_rejects_unknown_action(self):
        response = self.client.post(
            reverse("pet-mood"),
            {"action": "unknown"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
