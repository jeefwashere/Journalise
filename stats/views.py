from datetime import datetime, time, timedelta

from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import permissions
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.authentication import BearerTokenAuthentication
from journal.models import Activity
from .serializers import StatsSerializer


def get_hour_start(value):
    return value.replace(minute=0, second=0, microsecond=0)


def format_time_range(start_time, end_time):
    return f"{start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p')}"


class ActivityStatsView(APIView):
    authentication_classes = [BearerTokenAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        current_timezone = timezone.get_current_timezone()
        activities = Activity.objects.filter(
            user=request.user,
            ended_at__isnull=False,
        )

        date = request.query_params.get("date")
        day_start = None
        day_end = None

        if date:
            parsed_date = parse_date(date)
            if parsed_date is None:
                return Response(
                    {"date": "Use YYYY-MM-DD format."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            day_start = timezone.make_aware(
                datetime.combine(parsed_date, time.min),
                current_timezone,
            )
            day_end = day_start + timedelta(days=1)
            activities = activities.filter(
                started_at__lt=day_end,
                ended_at__gt=day_start,
            )

        category_labels = dict(Activity.Category.choices)
        buckets = {}

        for activity in activities.order_by("started_at", "id"):
            activity_start = timezone.localtime(activity.started_at, current_timezone)
            activity_end = timezone.localtime(activity.ended_at, current_timezone)

            if day_start is not None and day_end is not None:
                activity_start = max(activity_start, day_start)
                activity_end = min(activity_end, day_end)

            if activity_end <= activity_start:
                continue

            current_hour = get_hour_start(activity_start)

            while current_hour < activity_end:
                next_hour = current_hour + timedelta(hours=1)
                segment_start = max(activity_start, current_hour)
                segment_end = min(activity_end, next_hour)

                if segment_end <= segment_start:
                    current_hour = next_hour
                    continue

                key = (current_hour, activity.category)
                bucket = buckets.setdefault(
                    key,
                    {
                        "category": activity.category,
                        "category_display": category_labels.get(
                            activity.category,
                            activity.category,
                        ),
                        "total_seconds": 0,
                        "start_time": current_hour,
                        "end_time": next_hour,
                        "activity_ids": set(),
                        "titles": set(),
                        "notes": set(),
                    },
                )
                bucket["total_seconds"] += (segment_end - segment_start).total_seconds()
                bucket["activity_ids"].add(activity.pk)

                if activity.title:
                    bucket["titles"].add(activity.title)

                if activity.description:
                    bucket["notes"].add(activity.description)

                current_hour = next_hour

        data = [
            {
                "category": bucket["category"],
                "category_display": bucket["category_display"],
                "total_minutes": int(bucket["total_seconds"] // 60),
                "time_range": format_time_range(
                    bucket["start_time"],
                    bucket["end_time"],
                ),
                "start_time": bucket["start_time"],
                "end_time": bucket["end_time"],
                "activity_count": len(bucket["activity_ids"]),
                "titles": list(bucket["titles"]),
                "notes": list(bucket["notes"]),
            }
            for bucket in sorted(
                buckets.values(),
                key=lambda item: (item["start_time"], item["category"]),
            )
        ]

        serializer = StatsSerializer(data, many=True)
        return Response(serializer.data)
