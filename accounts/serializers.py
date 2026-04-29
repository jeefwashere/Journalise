from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import UserProfile


User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ("display_name", "avatar_url", "created_at", "updated_at")
        read_only_fields = ("created_at", "updated_at")


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(required=False)
    sub = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    picture = serializers.SerializerMethodField()
    preferred_username = serializers.CharField(source="username", read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "sub",
            "username",
            "preferred_username",
            "email",
            "first_name",
            "last_name",
            "name",
            "picture",
            "profile",
            "date_joined",
            "last_login",
        )
        read_only_fields = (
            "id",
            "sub",
            "username",
            "preferred_username",
            "email",
            "name",
            "picture",
            "date_joined",
            "last_login",
        )

    def get_sub(self, user):
        return str(user.pk)

    def get_name(self, user):
        if hasattr(user, "profile") and user.profile.display_name:
            return user.profile.display_name

        full_name = user.get_full_name()
        return full_name or user.username

    def get_picture(self, user):
        if hasattr(user, "profile"):
            return user.profile.avatar_url

        return ""

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", None)

        instance = super().update(instance, validated_data)

        if profile_data is not None:
            profile, _ = UserProfile.objects.get_or_create(user=instance)
            for field, value in profile_data.items():
                setattr(profile, field, value)
            profile.save()

        return instance
