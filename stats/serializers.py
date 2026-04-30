from rest_framework import serializers


class StatsSerializer(serializers.Serializer):
    category = serializers.CharField()
    category_display = serializers.CharField()
    total_minutes = serializers.IntegerField()
    time_range = serializers.CharField()
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()
    activity_count = serializers.IntegerField()
    titles = serializers.ListField(child=serializers.CharField(), required=False)
    notes = serializers.ListField(child=serializers.CharField(), required=False)
