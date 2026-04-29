from django.test import SimpleTestCase
from journal.activity_types import ActivitySession


class ActivitySessionTests(SimpleTestCase):
    def test_to_dict_returns_serializable_activity_session_data(self):
        session = ActivitySession(
            app_name="Safari",
            bundle_id="com.apple.Safari",
            started_at="2026-04-29T08:00:00Z",
            ended_at="2026-04-29T08:30:00Z",
            duration_seconds=1800,
        )

        self.assertEqual(
            session.to_dict(),
            {
                "app_name": "Safari",
                "bundle_id": "com.apple.Safari",
                "started_at": "2026-04-29T08:00:00Z",
                "ended_at": "2026-04-29T08:30:00Z",
                "duration_seconds": 1800,
            },
        )
