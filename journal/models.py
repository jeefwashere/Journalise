from django.db import models
from django.conf import settings


# Create your models here.
class Activity(models.Model):
    class Category(models.TextChoices):
        WORK = "work", "Work"
        STUDY = "study", "Study"
        ENTERTAINMENT = "entertainment", "Entertainment"
        COMMUNICATION = "communication", "Communication"
        OTHER = "other", "Other"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="activities"
    )
    title = models.CharField(max_length=255)
    category = models.CharField(
        max_length=30, choices=Category.choices, default=Category.OTHER
    )
    description = models.TextField(blank=True)
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
