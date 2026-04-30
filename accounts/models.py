from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User

from pets.choices import PetMood


# Create your models here.
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    display_name = models.CharField(max_length=100, blank=True)
    pet_name = models.CharField(max_length=100, blank=True)
    pet_level = models.PositiveSmallIntegerField(
        default=1,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(3),
        ],
    )
    current_pet = models.ForeignKey(
        "pets.Pet", on_delete=models.SET_NULL, null=True, blank=True
    )
    pet_mood = models.CharField(
        max_length=20,
        choices=PetMood.choices,
        default=PetMood.NEUTRAL,
    )
    avatar_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
