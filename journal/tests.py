from datetime import datetime, timezone as dt_timezone

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import include, path
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from .models import Activity


urlpatterns = [
    path("", include("journal.urls")),
]

User = get_user_model()


@override_settings(ROOT_URLCONF=__name__)
class ActivityViewTests(APITestCase):
    list_url = "/activities/"

    def setUp(self):
        self.user = User.objects.create_user(
            username="journal-user",
            email="journal@example.com",
            password="secret-pass",
        )
        self.other_user = User.objects.create_user(
            username="other-user",
            email="other@example.com",
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
        started_at=None,
        ended_at=None,
    ):
        return Activity.objects.create(
            user=user or self.user,
            title=title,
            category=category,
            description=description,
            started_at=started_at
            or datetime(2026, 4, 29, 9, 0, tzinfo=dt_timezone.utc),
            ended_at=ended_at,
        )

    def detail_url(self, activity):
        return f"/activities/{activity.pk}/"

    def test_list_view_requires_authentication(self):
        response = APIClient().get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_view_returns_only_authenticated_users_activities_ordered_newest_first(
        self,
    ):
        earlier = self.create_activity(
            title="Morning reading",
            started_at=datetime(2026, 4, 29, 8, 0, tzinfo=dt_timezone.utc),
        )
        later = self.create_activity(
            title="Afternoon build",
            started_at=datetime(2026, 4, 29, 14, 0, tzinfo=dt_timezone.utc),
        )
        self.create_activity(
            user=self.other_user,
            title="Someone else's activity",
            started_at=datetime(2026, 4, 29, 15, 0, tzinfo=dt_timezone.utc),
        )

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in response.data], [later.pk, earlier.pk])
        self.assertEqual(
            [item["title"] for item in response.data],
            ["Afternoon build", "Morning reading"],
        )

    def test_list_view_filters_activities_by_started_at_date(self):
        target = self.create_activity(
            title="Target day",
            started_at=datetime(2026, 4, 29, 10, 0, tzinfo=dt_timezone.utc),
        )
        self.create_activity(
            title="Previous day",
            started_at=datetime(2026, 4, 28, 10, 0, tzinfo=dt_timezone.utc),
        )
        self.create_activity(
            user=self.other_user,
            title="Other user's target day",
            started_at=datetime(2026, 4, 29, 11, 0, tzinfo=dt_timezone.utc),
        )

        response = self.client.get(self.list_url, {"date": "2026-04-29"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in response.data], [target.pk])

    def test_create_view_assigns_the_authenticated_user(self):
        response = self.client.post(
            self.list_url,
            {
                "title": "Write journal tests",
                "category": Activity.Category.STUDY,
                "description": "Cover the API views",
                "started_at": "2026-04-29T14:30:00Z",
                "ended_at": "2026-04-29T15:00:00Z",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        activity = Activity.objects.get(pk=response.data["id"])
        self.assertEqual(activity.user, self.user)
        self.assertEqual(activity.title, "Write journal tests")
        self.assertEqual(activity.category, Activity.Category.STUDY)
        self.assertEqual(response.data["category_display"], "Study")

    def test_detail_view_returns_authenticated_users_activity(self):
        activity = self.create_activity(title="Private activity")

        response = self.client.get(self.detail_url(activity))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], activity.pk)
        self.assertEqual(response.data["title"], "Private activity")

    def test_detail_view_does_not_expose_other_users_activity(self):
        activity = self.create_activity(
            user=self.other_user,
            title="Other user's activity",
        )

        response = self.client.get(self.detail_url(activity))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_view_updates_authenticated_users_activity(self):
        activity = self.create_activity(
            title="Old title",
            category=Activity.Category.OTHER,
        )

        response = self.client.patch(
            self.detail_url(activity),
            {
                "title": "Updated title",
                "category": Activity.Category.COMMUNICATION,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        activity.refresh_from_db()
        self.assertEqual(activity.title, "Updated title")
        self.assertEqual(activity.category, Activity.Category.COMMUNICATION)

    def test_delete_view_deletes_authenticated_users_activity(self):
        activity = self.create_activity(title="Delete me")

        response = self.client.delete(self.detail_url(activity))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Activity.objects.filter(pk=activity.pk).exists())
