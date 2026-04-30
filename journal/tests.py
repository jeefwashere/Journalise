import importlib
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from journal.activity_types import ActivitySession
from journal.models import Activity
from rest_framework import status

User = get_user_model()


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


class ActivityStoreTests(SimpleTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.base_dir = Path(self.temp_dir.name)
        self.date_str = "2026-04-29"
        self.day_path = self.base_dir / "activity_logs" / f"{self.date_str}.json"

    def _load_store_module(self):
        try:
            return importlib.import_module("journal.activity_store")
        except ModuleNotFoundError:
            self.fail("journal.activity_store is not implemented yet")

    def test_append_session_appends_to_the_days_json_array(self):
        activity_store = self._load_store_module()
        session = ActivitySession(
            app_name="Safari",
            bundle_id="com.apple.Safari",
            started_at="2026-04-29T08:00:00Z",
            ended_at="2026-04-29T08:30:00Z",
            duration_seconds=1800,
        )

        activity_store.append_session(self.base_dir, self.date_str, session)

        self.assertEqual(
            json.loads(self.day_path.read_text(encoding="utf-8")),
            [session.to_dict()],
        )

    def test_append_session_preserves_existing_sessions_when_appending(self):
        activity_store = self._load_store_module()
        existing_session = ActivitySession(
            app_name="Notes",
            bundle_id="com.apple.Notes",
            started_at="2026-04-29T07:30:00Z",
            ended_at="2026-04-29T07:45:00Z",
            duration_seconds=900,
        )
        new_session = ActivitySession(
            app_name="Safari",
            bundle_id="com.apple.Safari",
            started_at="2026-04-29T08:00:00Z",
            ended_at="2026-04-29T08:30:00Z",
            duration_seconds=1800,
        )
        self.day_path.parent.mkdir(parents=True, exist_ok=True)
        self.day_path.write_text(
            json.dumps([existing_session.to_dict()]),
            encoding="utf-8",
        )

        activity_store.append_session(self.base_dir, self.date_str, new_session)

        self.assertEqual(
            json.loads(self.day_path.read_text(encoding="utf-8")),
            [existing_session.to_dict(), new_session.to_dict()],
        )

    def test_append_session_recovers_from_malformed_existing_content(self):
        activity_store = self._load_store_module()
        new_session = ActivitySession(
            app_name="Safari",
            bundle_id="com.apple.Safari",
            started_at="2026-04-29T08:00:00Z",
            ended_at="2026-04-29T08:30:00Z",
            duration_seconds=1800,
        )
        self.day_path.parent.mkdir(parents=True, exist_ok=True)
        self.day_path.write_text("{not valid json", encoding="utf-8")

        activity_store.append_session(self.base_dir, self.date_str, new_session)

        self.assertEqual(
            json.loads(self.day_path.read_text(encoding="utf-8")),
            [new_session.to_dict()],
        )

    def test_append_session_recovers_from_existing_content_that_is_not_a_list(self):
        activity_store = self._load_store_module()
        new_session = ActivitySession(
            app_name="Safari",
            bundle_id="com.apple.Safari",
            started_at="2026-04-29T08:00:00Z",
            ended_at="2026-04-29T08:30:00Z",
            duration_seconds=1800,
        )
        self.day_path.parent.mkdir(parents=True, exist_ok=True)
        self.day_path.write_text(json.dumps({"unexpected": "value"}), encoding="utf-8")

        activity_store.append_session(self.base_dir, self.date_str, new_session)

        self.assertEqual(
            json.loads(self.day_path.read_text(encoding="utf-8")),
            [new_session.to_dict()],
        )

    def test_load_sessions_for_date_returns_the_days_dictionaries(self):
        activity_store = self._load_store_module()
        matching_session = ActivitySession(
            app_name="Safari",
            bundle_id="com.apple.Safari",
            started_at="2026-04-29T08:00:00Z",
            ended_at="2026-04-29T08:30:00Z",
            duration_seconds=1800,
        )
        self.day_path.parent.mkdir(parents=True, exist_ok=True)
        self.day_path.write_text(
            json.dumps([matching_session.to_dict()]),
            encoding="utf-8",
        )

        sessions = activity_store.load_sessions_for_date(self.base_dir, self.date_str)

        self.assertEqual(sessions, [matching_session.to_dict()])

    def test_load_sessions_for_date_returns_empty_list_when_day_file_is_missing(self):
        activity_store = self._load_store_module()

        sessions = activity_store.load_sessions_for_date(self.base_dir, self.date_str)

        self.assertEqual(sessions, [])

    def test_load_sessions_for_date_returns_empty_list_for_malformed_json(self):
        activity_store = self._load_store_module()
        self.day_path.parent.mkdir(parents=True, exist_ok=True)
        self.day_path.write_text("{not valid json", encoding="utf-8")

        sessions = activity_store.load_sessions_for_date(self.base_dir, self.date_str)

        self.assertEqual(sessions, [])

    def test_load_sessions_for_date_returns_empty_list_when_json_is_not_a_list(self):
        activity_store = self._load_store_module()
        self.day_path.parent.mkdir(parents=True, exist_ok=True)
        self.day_path.write_text(json.dumps({"app_name": "Safari"}), encoding="utf-8")

        sessions = activity_store.load_sessions_for_date(self.base_dir, self.date_str)

        self.assertEqual(sessions, [])

    def test_load_sessions_for_date_returns_empty_list_when_any_item_is_invalid(self):
        activity_store = self._load_store_module()
        self.day_path.parent.mkdir(parents=True, exist_ok=True)
        self.day_path.write_text(
            json.dumps(
                [
                    {
                        "app_name": "Safari",
                        "bundle_id": "com.apple.Safari",
                        "started_at": "2026-04-29T08:00:00Z",
                        "ended_at": "2026-04-29T08:30:00Z",
                    }
                ]
            ),
            encoding="utf-8",
        )

        sessions = activity_store.load_sessions_for_date(self.base_dir, self.date_str)

        self.assertEqual(sessions, [])


class ActivityTrackerTests(SimpleTestCase):
    def _load_tracker_class(self):
        try:
            module = importlib.import_module("journal.activity_tracker")
        except ModuleNotFoundError:
            self.fail("journal.activity_tracker is not implemented yet")

        return module.ActivityTracker

    def test_start_session_begins_a_session_that_can_be_finished(self):
        ActivityTracker = self._load_tracker_class()
        tracker = ActivityTracker()
        started_at = datetime(2026, 4, 29, 8, 0, tzinfo=timezone.utc)
        ended_at = datetime(2026, 4, 29, 8, 30, tzinfo=timezone.utc)

        tracker.start_session("Safari", "com.apple.Safari", started_at)
        finished_session = tracker.finish_active_session(ended_at)

        self.assertEqual(
            finished_session,
            ActivitySession(
                app_name="Safari",
                bundle_id="com.apple.Safari",
                started_at="2026-04-29T08:00:00Z",
                ended_at="2026-04-29T08:30:00Z",
                duration_seconds=1800,
            ),
        )

    def test_switch_session_finishes_the_previous_session_and_starts_the_next_one(self):
        ActivityTracker = self._load_tracker_class()
        tracker = ActivityTracker()
        first_started_at = datetime(2026, 4, 29, 8, 0, tzinfo=timezone.utc)
        second_started_at = datetime(2026, 4, 29, 8, 45, tzinfo=timezone.utc)
        second_ended_at = datetime(2026, 4, 29, 9, 15, tzinfo=timezone.utc)

        tracker.start_session("Safari", "com.apple.Safari", first_started_at)
        switched_session = tracker.switch_session(
            "Notes",
            "com.apple.Notes",
            second_started_at,
        )
        final_session = tracker.finish_active_session(second_ended_at)

        self.assertEqual(
            switched_session,
            ActivitySession(
                app_name="Safari",
                bundle_id="com.apple.Safari",
                started_at="2026-04-29T08:00:00Z",
                ended_at="2026-04-29T08:45:00Z",
                duration_seconds=2700,
            ),
        )
        self.assertEqual(
            final_session,
            ActivitySession(
                app_name="Notes",
                bundle_id="com.apple.Notes",
                started_at="2026-04-29T08:45:00Z",
                ended_at="2026-04-29T09:15:00Z",
                duration_seconds=1800,
            ),
        )

    def test_finish_active_session_returns_none_when_no_session_is_active(self):
        ActivityTracker = self._load_tracker_class()
        tracker = ActivityTracker()
        ended_at = datetime(2026, 4, 29, 8, 30, tzinfo=timezone.utc)

        self.assertIsNone(tracker.finish_active_session(ended_at))

    def test_start_session_raises_value_error_for_naive_started_at(self):
        ActivityTracker = self._load_tracker_class()
        tracker = ActivityTracker()

        with self.assertRaises(ValueError):
            tracker.start_session(
                "Safari",
                "com.apple.Safari",
                datetime(2026, 4, 29, 8, 0),
            )

    def test_finish_active_session_raises_value_error_for_naive_ended_at(self):
        ActivityTracker = self._load_tracker_class()
        tracker = ActivityTracker()
        started_at = datetime(2026, 4, 29, 8, 0, tzinfo=timezone.utc)

        tracker.start_session("Safari", "com.apple.Safari", started_at)

        with self.assertRaises(ValueError):
            tracker.finish_active_session(datetime(2026, 4, 29, 8, 30))

    def test_switch_session_raises_value_error_for_naive_started_at(self):
        ActivityTracker = self._load_tracker_class()
        tracker = ActivityTracker()
        first_started_at = datetime(2026, 4, 29, 8, 0, tzinfo=timezone.utc)

        tracker.start_session("Safari", "com.apple.Safari", first_started_at)

        with self.assertRaises(ValueError):
            tracker.switch_session(
                "Notes",
                "com.apple.Notes",
                datetime(2026, 4, 29, 8, 45),
            )

    def test_finish_active_session_clamps_duration_to_zero_when_ended_at_is_earlier(self):
        ActivityTracker = self._load_tracker_class()
        tracker = ActivityTracker()
        started_at = datetime(2026, 4, 29, 8, 30, tzinfo=timezone.utc)
        ended_at = datetime(2026, 4, 29, 8, 0, tzinfo=timezone.utc)

        tracker.start_session("Safari", "com.apple.Safari", started_at)
        finished_session = tracker.finish_active_session(ended_at)

        self.assertEqual(finished_session.duration_seconds, 0)

    def test_start_session_replaces_existing_active_session(self):
        ActivityTracker = self._load_tracker_class()
        tracker = ActivityTracker()
        first_started_at = datetime(2026, 4, 29, 8, 0, tzinfo=timezone.utc)
        second_started_at = datetime(2026, 4, 29, 8, 45, tzinfo=timezone.utc)
        ended_at = datetime(2026, 4, 29, 9, 0, tzinfo=timezone.utc)

        tracker.start_session("Safari", "com.apple.Safari", first_started_at)
        tracker.start_session("Notes", "com.apple.Notes", second_started_at)
        finished_session = tracker.finish_active_session(ended_at)

        self.assertEqual(
            finished_session,
            ActivitySession(
                app_name="Notes",
                bundle_id="com.apple.Notes",
                started_at="2026-04-29T08:45:00Z",
                ended_at="2026-04-29T09:00:00Z",
                duration_seconds=900,
            ),
        )

    def test_finish_active_session_keeps_active_session_when_validation_fails(self):
        ActivityTracker = self._load_tracker_class()
        tracker = ActivityTracker()
        started_at = datetime(2026, 4, 29, 8, 0, tzinfo=timezone.utc)
        valid_ended_at = datetime(2026, 4, 29, 8, 30, tzinfo=timezone.utc)

        tracker.start_session("Safari", "com.apple.Safari", started_at)

        with self.assertRaises(ValueError):
            tracker.finish_active_session(datetime(2026, 4, 29, 8, 15))

        self.assertEqual(
            tracker.finish_active_session(valid_ended_at),
            ActivitySession(
                app_name="Safari",
                bundle_id="com.apple.Safari",
                started_at="2026-04-29T08:00:00Z",
                ended_at="2026-04-29T08:30:00Z",
                duration_seconds=1800,
            ),
        )
    def test_switch_session_keeps_active_session_when_new_started_at_is_invalid(self):
        ActivityTracker = self._load_tracker_class()
        tracker = ActivityTracker()
        first_started_at = datetime(2026, 4, 29, 8, 0, tzinfo=timezone.utc)
        valid_ended_at = datetime(2026, 4, 29, 8, 30, tzinfo=timezone.utc)

        tracker.start_session("Safari", "com.apple.Safari", first_started_at)

        with self.assertRaises(ValueError):
            tracker.switch_session(
                "Notes",
                "com.apple.Notes",
                datetime(2026, 4, 29, 8, 15),
            )

        self.assertEqual(
            tracker.finish_active_session(valid_ended_at),
            ActivitySession(
                app_name="Safari",
                bundle_id="com.apple.Safari",
                started_at="2026-04-29T08:00:00Z",
                ended_at="2026-04-29T08:30:00Z",
                duration_seconds=1800,
            ),
        )


class ActivityIngestTests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.base_dir = Path(self.temp_dir.name)
        self.user = User.objects.create_user(username="tracker", password="secret-pass")

    def test_persist_session_creates_activity_and_local_log(self):
        from journal.activity_ingest import persist_session

        session = ActivitySession(
            app_name="Visual Studio Code",
            bundle_id="com.microsoft.VSCode",
            started_at="2026-04-29T08:00:00Z",
            ended_at="2026-04-29T08:30:00Z",
            duration_seconds=1800,
        )

        activity, created = persist_session(
            self.user,
            session,
            base_dir=self.base_dir,
        )

        self.assertTrue(created)
        self.assertEqual(activity.user, self.user)
        self.assertEqual(activity.title, "Visual Studio Code")
        self.assertEqual(activity.category, Activity.Category.WORK)
        self.assertIn("com.microsoft.VSCode", activity.description)

        day_path = self.base_dir / "activity_logs" / "2026-04-29.json"
        self.assertEqual(
            json.loads(day_path.read_text(encoding="utf-8")),
            [session.to_dict()],
        )

    def test_persist_session_is_idempotent_for_existing_activity(self):
        from journal.activity_ingest import persist_session

        session = ActivitySession(
            app_name="Safari",
            bundle_id="com.apple.Safari",
            started_at="2026-04-29T08:00:00Z",
            ended_at="2026-04-29T08:30:00Z",
            duration_seconds=1800,
        )

        persist_session(self.user, session, base_dir=self.base_dir)
        activity, created = persist_session(self.user, session, base_dir=self.base_dir)

        self.assertFalse(created)
        self.assertEqual(Activity.objects.filter(pk=activity.pk).count(), 1)


class ActivityTrackingViewTests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.user = User.objects.create_user(
            username="api-tracker",
            password="secret-pass",
        )
        self.client.force_login(self.user)

    def test_tracking_endpoint_persists_session_as_activity(self):
        payload = {
            "enabled": True,
            "sessions": [
                {
                    "app_name": "Zoom",
                    "bundle_id": "us.zoom.xos",
                    "started_at": "2026-04-29T09:00:00Z",
                    "ended_at": "2026-04-29T09:15:00Z",
                    "duration_seconds": 900,
                }
            ],
        }

        with self.settings(BASE_DIR=Path(self.temp_dir.name)):
            response = self.client.post(
                reverse("activity-tracking"),
                data=payload,
                content_type="application/json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["created"], 1)

        activity = Activity.objects.get(user=self.user)
        self.assertEqual(activity.title, "Zoom")
        self.assertEqual(activity.category, Activity.Category.COMMUNICATION)

    def test_tracking_endpoint_rejects_invalid_sessions_shape(self):
        response = self.client.post(
            reverse("activity-tracking"),
            data={"sessions": {"app_name": "Safari"}},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class CollectActivityCommandTests(SimpleTestCase):
    @mock.patch("journal.management.commands.collect_activity.run_collector")
    def test_collect_activity_command_delegates_to_run_collector(self, mock_run_collector):
        call_command("collect_activity")

        mock_run_collector.assert_called_once_with()
