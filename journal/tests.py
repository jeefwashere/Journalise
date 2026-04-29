import importlib
import json
import tempfile
from pathlib import Path

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
