from rest_framework import serializers

from .choices import PetMood

from .models import Pet


class PetSerializer(serializers.ModelSerializer):
    pet_type_display = serializers.CharField(
        source="get_pet_type_display", read_only=True
    )
    mood_display = serializers.CharField(source="get_mood_display", read_only=True)

    class Meta:
        model = Pet
        fields = (
            "id",
            "pet_type",
            "pet_type_display",
            "level",
            "mood",
            "mood_display",
            "name",
            "svg_path",
        )
        read_only_fields = fields


class PetMoodActionSerializer(serializers.Serializer):
    ACTION_TO_MOOD = {
        "activity_started": PetMood.FOCUSED,
        "activity_completed": PetMood.HAPPY,
        "break_started": PetMood.NEUTRAL,
        "idle": PetMood.TIRED,
    }

    action = serializers.ChoiceField(
        choices=[(action, action.replace("_", " ").title()) for action in ACTION_TO_MOOD]
    )

    def get_mood(self):
        return self.ACTION_TO_MOOD[self.validated_data["action"]]
