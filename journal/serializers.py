from rest_framework import serializers

from .models import Activity


class ActivitySerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(
        source="get_category_display", read_only=True
    )

    class Meta:
        model = Activity
        fields = [
            "id",
            "title",
            "category",
            "category_display",
            "description",
            "started_at",
            "ended_at",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
        ]
