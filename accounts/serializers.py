from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from pets.models import Pet
from pets.serializers import PetSerializer

from .models import UserProfile

User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    current_pet = PetSerializer(read_only=True)
    current_pet_id = serializers.PrimaryKeyRelatedField(
        source="current_pet",
        queryset=Pet.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
    )
    pet_mood_display = serializers.CharField(
        source="get_pet_mood_display", read_only=True
    )

    class Meta:
        model = UserProfile
        fields = (
            "display_name",
            "pet_level",
            "current_pet",
            "current_pet_id",
            "pet_mood",
            "pet_mood_display",
            "avatar_url",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "pet_level",
            "current_pet",
            "pet_mood",
            "pet_mood_display",
            "created_at",
            "updated_at",
        )


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

    def validate(self, attrs):
        profile_data = attrs.get("profile")
        selected_pet = None

        if profile_data:
            selected_pet = profile_data.get("current_pet")

        if selected_pet is not None:
            profile = getattr(self.instance, "profile", None)
            pet_level = (
                profile.pet_level
                if profile is not None
                else UserProfile._meta.get_field("pet_level").default
            )

            if selected_pet.level > pet_level:
                raise serializers.ValidationError(
                    {
                        "profile": {
                            "current_pet_id": "Selected pet is above the user's pet level."
                        }
                    }
                )

        return attrs

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", None)

        instance = super().update(instance, validated_data)

        if profile_data is not None:
            profile, _ = UserProfile.objects.get_or_create(user=instance)
            for field, value in profile_data.items():
                setattr(profile, field, value)
            profile.save()

        return instance


class GoogleLoginSerializer(serializers.Serializer):
    id_token = serializers.CharField(required=False)
    code = serializers.CharField(required=False)

    def validate(self, attrs):
        if not attrs.get("id_token") and not attrs.get("code"):
            raise serializers.ValidationError(
                {"id_token": "Provide either a Google ID token or authorization code."}
            )
        return attrs


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=255, allow_blank=False)
    password = serializers.CharField(write_only=True)


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=255, allow_blank=False)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists")
        return value

    def validate_email(self, value):
        value = value.lower().strip()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already in use")
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
        )
        UserProfile.objects.get_or_create(
            user=user,
            defaults={"display_name": validated_data["username"]},
        )
        return user
