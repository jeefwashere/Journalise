# pets/models.py

from django.db import models

from .choices import PetMood


class Pet(models.Model):
    class PetType(models.TextChoices):
        CAT = "cat", "Cat"
        DOG = "dog", "Dog"
        FROG = "frog", "Frog"

    pet_type = models.CharField(max_length=20, choices=PetType.choices)
    level = models.PositiveSmallIntegerField()
    mood = models.CharField(
        max_length=20,
        choices=PetMood.choices,
        default=PetMood.NEUTRAL,
    )
    name = models.CharField(max_length=100)
    svg_path = models.CharField(max_length=255)

    class Meta:
        unique_together = ["pet_type", "level", "mood"]
        ordering = ["pet_type", "level", "mood"]

    def __str__(self):
        return f"{self.get_pet_type_display()} Level {self.level} ({self.get_mood_display()})"
