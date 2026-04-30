from django.db import models


class PetMood(models.TextChoices):
    NEUTRAL = "neutral", "Neutral"
    FOCUSED = "focused", "Focused"
    HAPPY = "happy", "Happy"
    TIRED = "tired", "Tired"
