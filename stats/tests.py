from datetime import datetime, timezone as dt_timezone

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import include, path
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from journal.models import Activity

urlpatterns = [
    path("", include("stats.urls")),
]

User = get_user_model()


@override_settings(ROOT_URLCONF=__name__)
class ActivityStatsViewTests(APITestCase):
    stats_url = "/stats/"

    def setUp(self):
        self.user = User.objects.create_user(
            username="stats-user",
            email="stats@example.com",
            password="secret-pass",
        )
        self.other_user = User.objects.create_user(
            username="other-stats-user",
            email="other-stats@example.com",
            password="secret-pass",
        )
        self.client.force_authenticate(user=self.user)

    def create_activity(
        self,
        *,
        user=None,
        title="Focused work",
        category=Activity.Category.WORK,
        description="",
        started_at,
        ended_at,
    ):
        return Activity.objects.create(
            user=user or self.user,
            title=title,
            category=category,
            description=description,
            started_at=started_at,
            ended_at=ended_at,
        )

    def test_stats_view_requires_authentication(self):
        response = APIClient().get(self.stats_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_splits_activity_across_hourly_buckets(self):
        self.create_activity(
            title="Evening build",
            category=Activity.Category.WORK,
            description="Shipped stats",
            started_at=datetime(2026, 4, 29, 20, 45, tzinfo=dt_timezone.utc),
            ended_at=datetime(2026, 4, 29, 21, 15, tzinfo=dt_timezone.utc),
        )

        response = self.client.get(self.stats_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]["time_range"], "08:00 PM - 09:00 PM")
        self.assertEqual(response.data[0]["total_minutes"], 15)
        self.assertEqual(response.data[0]["category"], Activity.Category.WORK)
        self.assertEqual(response.data[0]["titles"], ["Evening build"])
        self.assertEqual(response.data[0]["notes"], ["Shipped stats"])
        self.assertEqual(response.data[1]["time_range"], "09:00 PM - 10:00 PM")
        self.assertEqual(response.data[1]["total_minutes"], 15)

    def test_groups_same_hour_by_category(self):
        self.create_activity(
            title="Focused work",
            category=Activity.Category.WORK,
            started_at=datetime(2026, 4, 29, 20, 0, tzinfo=dt_timezone.utc),
            ended_at=datetime(2026, 4, 29, 20, 30, tzinfo=dt_timezone.utc),
        )
        self.create_activity(
            title="Reading",
            category=Activity.Category.STUDY,
            started_at=datetime(2026, 4, 29, 20, 15, tzinfo=dt_timezone.utc),
            ended_at=datetime(2026, 4, 29, 20, 45, tzinfo=dt_timezone.utc),
        )
        self.create_activity(
            title="More work",
            category=Activity.Category.WORK,
            started_at=datetime(2026, 4, 29, 20, 30, tzinfo=dt_timezone.utc),
            ended_at=datetime(2026, 4, 29, 21, 0, tzinfo=dt_timezone.utc),
        )
        self.create_activity(
            user=self.other_user,
            title="Other user work",
            category=Activity.Category.WORK,
            started_at=datetime(2026, 4, 29, 20, 0, tzinfo=dt_timezone.utc),
            ended_at=datetime(2026, 4, 29, 21, 0, tzinfo=dt_timezone.utc),
        )

        response = self.client.get(self.stats_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        bucket_summary = [
            (item["time_range"], item["category"], item["total_minutes"])
            for item in response.data
        ]
        self.assertEqual(
            bucket_summary,
            [
                ("08:00 PM - 09:00 PM", Activity.Category.STUDY, 30),
                ("08:00 PM - 09:00 PM", Activity.Category.WORK, 60),
            ],
        )
        work_bucket = response.data[1]
        self.assertEqual(work_bucket["activity_count"], 2)
        self.assertEqual(work_bucket["titles"], ["More work", "Focused work"])

    def test_date_filter_includes_overlapping_activity_segment(self):
        self.create_activity(
            title="Midnight handoff",
            category=Activity.Category.WORK,
            started_at=datetime(2026, 4, 28, 23, 30, tzinfo=dt_timezone.utc),
            ended_at=datetime(2026, 4, 29, 0, 30, tzinfo=dt_timezone.utc),
        )
        self.create_activity(
            title="Wrong day",
            category=Activity.Category.WORK,
            started_at=datetime(2026, 4, 28, 22, 0, tzinfo=dt_timezone.utc),
            ended_at=datetime(2026, 4, 28, 23, 0, tzinfo=dt_timezone.utc),
        )

        response = self.client.get(self.stats_url, {"date": "2026-04-29"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["time_range"], "12:00 AM - 01:00 AM")
        self.assertEqual(response.data[0]["total_minutes"], 30)
        self.assertEqual(response.data[0]["titles"], ["Midnight handoff"])

    def test_rejects_invalid_date_filter(self):
        response = self.client.get(self.stats_url, {"date": "04/29/2026"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["date"], "Use YYYY-MM-DD format.")
