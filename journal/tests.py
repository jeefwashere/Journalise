import importlib
import json
import tempfile
from datetime import datetime, timedelta, timezone
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

LOCAL_TZ = timezone(timedelta(hours=-4), name="UTC-4")


def make_session(
    *,
    title="Safari",
    started_at="2026-04-29T04:00:00-04:00",
    ended_at="2026-04-29T04:30:00-04:00",
    created_at="2026-04-29T04:30:00-04:00",
):
    return ActivitySession(
        title=title,
        category="work",
        description="",
        started_at=started_at,
        ended_at=ended_at,
        created_at=created_at,
    )


class ActivitySessionTests(SimpleTestCase):
    def test_to_dict_returns_serializable_activity_session_data(self):
        session = make_session()

        self.assertEqual(
            session.to_dict(),
            {
                "title": "Safari",
                "category": "work",
                "description": "",
                "started_at": "2026-04-29T04:00:00-04:00",
                "ended_at": "2026-04-29T04:30:00-04:00",
                "created_at": "2026-04-29T04:30:00-04:00",
            },
        )


class ActivityTitleTests(SimpleTestCase):
    def test_activity_title_to_app_name_uses_browser_tab_title(self):
        from journal.activity_titles import activity_title_to_app_name

        self.assertEqual(
            activity_title_to_app_name(
                "chrome.exe - Page not found at /journal - Google Chrome"
            ),
            "Page not found at /journal",
        )
        self.assertEqual(
            activity_title_to_app_name(
                "chrome.exe - (25) YouTube - Google Chrome"
            ),
            "(25) YouTube",
        )

    def test_activity_title_to_app_name_collapses_non_browser_windows(self):
        from journal.activity_titles import activity_title_to_app_name

        self.assertEqual(
            activity_title_to_app_name(
                "Code.exe - activity_ingest.py - Journalise - Visual Studio Code"
            ),
            "Visual Studio Code",
        )
        self.assertEqual(
            activity_title_to_app_name("WhatsApp.Root.exe - WhatsApp"),
            "WhatsApp",
        )

    def test_activity_title_to_app_name_cleans_bare_executable_names(self):
        from journal.activity_titles import activity_title_to_app_name

        self.assertEqual(activity_title_to_app_name("chrome.exe"), "Google Chrome")
        self.assertEqual(activity_title_to_app_name("Code.exe"), "Visual Studio Code")


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
        session = make_session()

        activity_store.append_session(self.base_dir, self.date_str, session)

        self.assertEqual(
            json.loads(self.day_path.read_text(encoding="utf-8")),
            [session.to_dict()],
        )

    def test_append_session_writes_pretty_printed_json_with_newlines(self):
        activity_store = self._load_store_module()
        session = make_session()

        activity_store.append_session(self.base_dir, self.date_str, session)

        contents = self.day_path.read_text(encoding="utf-8")
        self.assertIn('\n  {\n', contents)
        self.assertTrue(contents.endswith("\n"))

    def test_append_session_preserves_existing_sessions_when_appending(self):
        activity_store = self._load_store_module()
        existing_session = make_session(
            title="Notes",
            started_at="2026-04-29T07:30:00Z",
            ended_at="2026-04-29T07:45:00Z",
            created_at="2026-04-29T07:45:00Z",
        )
        new_session = make_session()
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
        new_session = make_session()
        self.day_path.parent.mkdir(parents=True, exist_ok=True)
        self.day_path.write_text("{not valid json", encoding="utf-8")

        activity_store.append_session(self.base_dir, self.date_str, new_session)

        self.assertEqual(
            json.loads(self.day_path.read_text(encoding="utf-8")),
            [new_session.to_dict()],
        )

    def test_append_session_recovers_from_existing_content_that_is_not_a_list(self):
        activity_store = self._load_store_module()
        new_session = make_session()
        self.day_path.parent.mkdir(parents=True, exist_ok=True)
        self.day_path.write_text(json.dumps({"unexpected": "value"}), encoding="utf-8")

        activity_store.append_session(self.base_dir, self.date_str, new_session)

        self.assertEqual(
            json.loads(self.day_path.read_text(encoding="utf-8")),
            [new_session.to_dict()],
        )

    def test_load_sessions_for_date_returns_the_days_dictionaries(self):
        activity_store = self._load_store_module()
        matching_session = make_session()
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
                        "title": "Safari",
                        "category": "work",
                        "description": "",
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

        tracker.start_session("Safari", started_at)
        finished_session = tracker.finish_active_session(ended_at)

        self.assertEqual(
            finished_session,
            make_session(),
        )

    def test_switch_session_returns_none_when_app_name_is_unchanged(self):
        ActivityTracker = self._load_tracker_class()
        tracker = ActivityTracker()
        started_at = datetime(2026, 4, 29, 8, 0, tzinfo=timezone.utc)
        same_app_polled_at = datetime(2026, 4, 29, 8, 10, tzinfo=timezone.utc)
        ended_at = datetime(2026, 4, 29, 8, 30, tzinfo=timezone.utc)

        tracker.start_session("Safari", started_at)
        switched_session = tracker.switch_session("Safari", same_app_polled_at)
        final_session = tracker.finish_active_session(ended_at)

        self.assertIsNone(switched_session)
        self.assertEqual(final_session, make_session())

    def test_switch_session_finishes_the_previous_session_when_app_name_changes(self):
        ActivityTracker = self._load_tracker_class()
        tracker = ActivityTracker()
        first_started_at = datetime(2026, 4, 29, 8, 0, tzinfo=timezone.utc)
        changed_at = datetime(2026, 4, 29, 8, 45, tzinfo=timezone.utc)
        second_ended_at = datetime(2026, 4, 29, 9, 15, tzinfo=timezone.utc)

        tracker.start_session("Safari", first_started_at)
        switched_session = tracker.switch_session("Notes", changed_at)
        final_session = tracker.finish_active_session(second_ended_at)

        self.assertEqual(
            switched_session,
            make_session(
                title="Safari",
                ended_at="2026-04-29T04:45:00-04:00",
                created_at="2026-04-29T04:45:00-04:00",
            ),
        )
        self.assertEqual(
            final_session,
            make_session(
                title="Notes",
                started_at="2026-04-29T04:45:00-04:00",
                ended_at="2026-04-29T05:15:00-04:00",
                created_at="2026-04-29T05:15:00-04:00",
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
            tracker.start_session("Safari", datetime(2026, 4, 29, 8, 0))

    def test_finish_active_session_raises_value_error_for_naive_ended_at(self):
        ActivityTracker = self._load_tracker_class()
        tracker = ActivityTracker()
        started_at = datetime(2026, 4, 29, 8, 0, tzinfo=timezone.utc)

        tracker.start_session("Safari", started_at)

        with self.assertRaises(ValueError):
            tracker.finish_active_session(datetime(2026, 4, 29, 8, 30))

    def test_switch_session_raises_value_error_for_naive_started_at(self):
        ActivityTracker = self._load_tracker_class()
        tracker = ActivityTracker()
        first_started_at = datetime(2026, 4, 29, 8, 0, tzinfo=timezone.utc)

        tracker.start_session("Safari", first_started_at)

        with self.assertRaises(ValueError):
            tracker.switch_session("Notes", datetime(2026, 4, 29, 8, 45))


class AppCategoryTests(SimpleTestCase):
    def test_resolve_app_category_seeds_common_categories_into_library(self):
        module = importlib.import_module("journal.app_category")
        with tempfile.TemporaryDirectory() as temp_dir:
            category = module.resolve_app_category(temp_dir, "Code")
            saved_library = json.loads(
                (Path(temp_dir) / "category_library.json").read_text(encoding="utf-8")
            )

        self.assertEqual(category, "study")
        self.assertEqual(saved_library["Code"], "study")
        self.assertEqual(saved_library["WhatsApp"], "communication")
        self.assertEqual(saved_library["Spotify"], "relax")

    def test_resolve_app_category_uses_cached_library_value_without_model_call(self):
        module = importlib.import_module("journal.app_category")
        with tempfile.TemporaryDirectory() as temp_dir:
            library_path = Path(temp_dir) / "category_library.json"
            library_path.write_text(
                json.dumps({"Code": "study"}, indent=2) + "\n",
                encoding="utf-8",
            )

            with mock.patch("journal.app_category.request_category_from_model") as mock_request:
                category = module.resolve_app_category(temp_dir, "Code")

        self.assertEqual(category, "study")
        mock_request.assert_not_called()

    def test_resolve_app_category_prefers_manual_library_override_over_common_default(self):
        module = importlib.import_module("journal.app_category")
        with tempfile.TemporaryDirectory() as temp_dir:
            library_path = Path(temp_dir) / "category_library.json"
            library_path.write_text(
                json.dumps({"Code": "work"}, indent=2) + "\n",
                encoding="utf-8",
            )

            with mock.patch("journal.app_category.request_category_from_model") as mock_request:
                category = module.resolve_app_category(temp_dir, "Code")

        self.assertEqual(category, "work")
        mock_request.assert_not_called()

    @mock.patch("journal.app_category.subprocess.run")
    def test_request_category_from_model_retries_invalid_output_then_returns_valid_category(
        self,
        mock_run,
    ):
        module = importlib.import_module("journal.app_category")
        invalid_response = mock.Mock()
        invalid_response.stdout = json.dumps({"message": {"content": "linkedin"}})
        valid_response = mock.Mock()
        valid_response.stdout = json.dumps({"message": {"content": "communication"}})
        mock_run.side_effect = [invalid_response, valid_response]

        category = module.request_category_from_model("LinkedIn")

        self.assertEqual(category, "communication")
        self.assertEqual(mock_run.call_count, 2)

    @mock.patch("journal.app_category.request_category_from_model", return_value="work")
    def test_resolve_app_category_saves_new_model_result_to_library(self, mock_request):
        module = importlib.import_module("journal.app_category")
        with tempfile.TemporaryDirectory() as temp_dir:
            category = module.resolve_app_category(temp_dir, "UnknownApp")
            saved_library = json.loads(
                (Path(temp_dir) / "category_library.json").read_text(encoding="utf-8")
            )

        self.assertEqual(category, "work")
        self.assertEqual(saved_library["UnknownApp"], "work")
        mock_request.assert_called_once_with("UnknownApp")


class PrivacyTests(SimpleTestCase):
    def test_sanitize_text_redacts_obvious_pii_tokens(self):
        module = importlib.import_module("journal.privacy")

        sanitized = module.sanitize_text(
            "Email me at ricardo@example.com or call 416-555-0123. Resume: https://example.com/abc/1234567"
        )

        self.assertNotIn("ricardo@example.com", sanitized)
        self.assertNotIn("416-555-0123", sanitized)
        self.assertNotIn("https://example.com/abc/1234567", sanitized)
        self.assertIn("[redacted-email]", sanitized)
        self.assertIn("[redacted-phone]", sanitized)
        self.assertIn("[redacted-url]", sanitized)


class EnvUtilsTests(SimpleTestCase):
    def test_get_env_value_reads_value_from_dotenv_file(self):
        module = importlib.import_module("journal.env_utils")
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text("GEMINI_API_KEY=test-key\n", encoding="utf-8")

            value = module.get_env_value("GEMINI_API_KEY", env_path=env_path)

        self.assertEqual(value, "test-key")


class HourlySummaryTests(SimpleTestCase):
    @mock.patch("journal.hourly_summary.resolve_app_category")
    def test_reclassify_sessions_for_date_updates_existing_session_categories(
        self,
        mock_resolve_app_category,
    ):
        module = importlib.import_module("journal.hourly_summary")
        mock_resolve_app_category.side_effect = ["study", "communication"]
        with tempfile.TemporaryDirectory() as temp_dir:
            day_path = Path(temp_dir) / "activity_logs" / "2026-04-29.json"
            day_path.parent.mkdir(parents=True, exist_ok=True)
            day_path.write_text(
                json.dumps(
                    [
                        {
                            "title": "Code",
                            "category": "work",
                            "description": "",
                            "started_at": "2026-04-29T17:00:00Z",
                            "ended_at": "2026-04-29T17:30:00Z",
                            "created_at": "2026-04-29T17:30:00Z",
                        },
                        {
                            "title": "WeChat",
                            "category": "work",
                            "description": "",
                            "started_at": "2026-04-29T17:30:00Z",
                            "ended_at": "2026-04-29T17:45:00Z",
                            "created_at": "2026-04-29T17:45:00Z",
                        },
                    ]
                ),
                encoding="utf-8",
            )

            updated_sessions = module.reclassify_sessions_for_date(temp_dir, "2026-04-29")
            saved_sessions = json.loads(day_path.read_text(encoding="utf-8"))

        self.assertEqual(updated_sessions[0]["category"], "study")
        self.assertEqual(updated_sessions[1]["category"], "communication")
        self.assertEqual(saved_sessions, updated_sessions)

    @mock.patch("journal.hourly_summary.resolve_app_category")
    def test_rebuild_hourly_summary_for_date_groups_minutes_by_category_within_hour(
        self,
        mock_resolve_app_category,
    ):
        module = importlib.import_module("journal.hourly_summary")
        mock_resolve_app_category.side_effect = ["study", "communication", "study"]
        with tempfile.TemporaryDirectory() as temp_dir:
            day_path = Path(temp_dir) / "activity_logs" / "2026-04-29.json"
            day_path.parent.mkdir(parents=True, exist_ok=True)
            day_path.write_text(
                json.dumps(
                    [
                        {
                            "title": "Code",
                            "category": "work",
                            "description": "",
                            "started_at": "2026-04-29T17:00:00Z",
                            "ended_at": "2026-04-29T17:30:00Z",
                            "created_at": "2026-04-29T17:30:00Z",
                        },
                        {
                            "title": "WeChat",
                            "category": "work",
                            "description": "",
                            "started_at": "2026-04-29T17:30:00Z",
                            "ended_at": "2026-04-29T17:45:00Z",
                            "created_at": "2026-04-29T17:45:00Z",
                        },
                        {
                            "title": "Google Chrome",
                            "category": "work",
                            "description": "",
                            "started_at": "2026-04-29T17:45:00Z",
                            "ended_at": "2026-04-29T18:00:00Z",
                            "created_at": "2026-04-29T18:00:00Z",
                        },
                    ]
                ),
                encoding="utf-8",
            )

            results = module.rebuild_hourly_summary_for_date(temp_dir, "2026-04-29")
            saved = json.loads(
                (Path(temp_dir) / "hourly_summaries" / "2026-04-29.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(results, saved)
        self.assertEqual(
            saved,
            [
                {
                    "time_range": "01:00 PM - 02:00 PM",
                    "start_time": "2026-04-29T13:00:00-04:00",
                    "end_time": "2026-04-29T14:00:00-04:00",
                    "notes": [],
                    "categories": [
                        {
                            "category": "communication",
                            "category_display": "Communication",
                            "total_minutes": 15,
                            "activity_count": 1,
                            "titles": ["WeChat"],
                        },
                        {
                            "category": "study",
                            "category_display": "Study",
                            "total_minutes": 45,
                            "activity_count": 2,
                            "titles": ["Code", "Google Chrome"],
                        },
                    ],
                }
            ],
        )

    @mock.patch("journal.hourly_summary.resolve_app_category")
    def test_rebuild_hourly_summary_for_date_omits_categories_under_one_minute(
        self,
        mock_resolve_app_category,
    ):
        module = importlib.import_module("journal.hourly_summary")
        mock_resolve_app_category.side_effect = ["study", "work"]
        with tempfile.TemporaryDirectory() as temp_dir:
            day_path = Path(temp_dir) / "activity_logs" / "2026-04-29.json"
            day_path.parent.mkdir(parents=True, exist_ok=True)
            day_path.write_text(
                json.dumps(
                    [
                        {
                            "title": "Code",
                            "category": "work",
                            "description": "",
                            "started_at": "2026-04-29T17:00:00Z",
                            "ended_at": "2026-04-29T17:02:00Z",
                            "created_at": "2026-04-29T17:02:00Z",
                        },
                        {
                            "title": "Microsoft Word",
                            "category": "work",
                            "description": "",
                            "started_at": "2026-04-29T17:02:00Z",
                            "ended_at": "2026-04-29T17:02:20Z",
                            "created_at": "2026-04-29T17:02:20Z",
                        },
                    ]
                ),
                encoding="utf-8",
            )

            saved = module.rebuild_hourly_summary_for_date(temp_dir, "2026-04-29")

        self.assertEqual(
            saved[0]["categories"],
            [
                {
                    "category": "study",
                    "category_display": "Study",
                    "total_minutes": 2,
                    "activity_count": 1,
                    "titles": ["Code"],
                }
            ],
        )

    @mock.patch("journal.hourly_summary.resolve_app_category", return_value="study")
    def test_rebuild_hourly_summary_for_date_supports_est_session_timestamps(
        self,
        mock_resolve_app_category,
    ):
        module = importlib.import_module("journal.hourly_summary")
        with tempfile.TemporaryDirectory() as temp_dir:
            day_path = Path(temp_dir) / "activity_logs" / "2026-04-29.json"
            day_path.parent.mkdir(parents=True, exist_ok=True)
            day_path.write_text(
                json.dumps(
                    [
                        {
                            "title": "Code",
                            "category": "work",
                            "description": "",
                            "started_at": "2026-04-29T20:37:10-04:00",
                            "ended_at": "2026-04-29T20:42:48-04:00",
                            "created_at": "2026-04-29T20:42:48-04:00",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            saved = module.rebuild_hourly_summary_for_date(temp_dir, "2026-04-29")

        self.assertEqual(
            saved,
            [
                {
                    "time_range": "08:00 PM - 09:00 PM",
                    "start_time": "2026-04-29T20:00:00-04:00",
                    "end_time": "2026-04-29T21:00:00-04:00",
                    "notes": [],
                    "categories": [
                        {
                            "category": "study",
                            "category_display": "Study",
                            "total_minutes": 6,
                            "activity_count": 1,
                            "titles": ["Code"],
                        }
                    ],
                }
            ],
        )

    @mock.patch("journal.hourly_summary.resolve_app_category", return_value="study")
    def test_rebuild_hourly_summary_for_date_preserves_existing_hour_notes(
        self,
        mock_resolve_app_category,
    ):
        module = importlib.import_module("journal.hourly_summary")
        with tempfile.TemporaryDirectory() as temp_dir:
            day_path = Path(temp_dir) / "activity_logs" / "2026-04-29.json"
            hourly_path = Path(temp_dir) / "hourly_summaries" / "2026-04-29.json"
            day_path.parent.mkdir(parents=True, exist_ok=True)
            hourly_path.parent.mkdir(parents=True, exist_ok=True)
            day_path.write_text(
                json.dumps(
                    [
                        {
                            "title": "Code",
                            "category": "work",
                            "description": "",
                            "started_at": "2026-04-29T20:37:10-04:00",
                            "ended_at": "2026-04-29T20:42:48-04:00",
                            "created_at": "2026-04-29T20:42:48-04:00",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            hourly_path.write_text(
                json.dumps(
                    [
                        {
                            "time_range": "08:00 PM - 09:00 PM",
                            "start_time": "2026-04-29T20:00:00-04:00",
                            "end_time": "2026-04-29T21:00:00-04:00",
                            "notes": ["Existing note."],
                            "categories": [],
                        }
                    ]
                ),
                encoding="utf-8",
            )

            saved = module.rebuild_hourly_summary_for_date(temp_dir, "2026-04-29")

        self.assertEqual(saved[0]["notes"], ["Existing note."])

    def test_collect_vision_summaries_for_hour_filters_entries_inside_hour_window(self):
        module = importlib.import_module("journal.hourly_summary")
        with tempfile.TemporaryDirectory() as temp_dir:
            vision_path = Path(temp_dir) / "vision_summaries" / "2026-04-29.json"
            vision_path.parent.mkdir(parents=True, exist_ok=True)
            vision_path.write_text(
                json.dumps(
                    [
                        {
                            "captured_at": "2026-04-29T20:28:55-04:00",
                            "summary": "First summary.",
                        },
                        {
                            "captured_at": "2026-04-29T21:09:47-04:00",
                            "summary": "Second summary.",
                        },
                    ]
                ),
                encoding="utf-8",
            )

            summaries = module.collect_vision_summaries_for_hour(
                temp_dir,
                "2026-04-29",
                datetime(2026, 4, 29, 20, 0, tzinfo=LOCAL_TZ),
            )

        self.assertEqual(summaries, ["First summary."])

    @mock.patch("journal.hourly_summary.subprocess.run")
    def test_request_hourly_note_returns_note_string(self, mock_run):
        module = importlib.import_module("journal.hourly_summary")
        response = mock.Mock()
        response.stdout = json.dumps(
            {
                "message": {
                    "content": json.dumps({"note": "Mostly studying in Chrome and Code."})
                }
            }
        )
        mock_run.return_value = response

        note = module.request_hourly_note(
            {
                "time_range": "09:00 PM - 10:00 PM",
                "categories": [
                    {
                        "category": "study",
                        "total_minutes": 4,
                        "titles": ["Google Chrome", "Code"],
                    }
                ],
            },
            ["Reviewed job applications."],
        )

        self.assertEqual(note, "Mostly studying in Chrome and Code.")
        payload = json.loads(mock_run.call_args.args[0][-1])
        self.assertEqual(payload["model"], "qwen3:8b")
        self.assertFalse(payload["stream"])

    @mock.patch(
        "journal.hourly_summary.request_hourly_note",
        return_value="Hourly note. Email ricardo@example.com",
    )
    def test_generate_and_persist_hourly_note_writes_note_into_matching_hour(
        self,
        mock_request_hourly_note,
    ):
        module = importlib.import_module("journal.hourly_summary")
        with tempfile.TemporaryDirectory() as temp_dir:
            hourly_path = Path(temp_dir) / "hourly_summaries" / "2026-04-29.json"
            vision_path = Path(temp_dir) / "vision_summaries" / "2026-04-29.json"
            hourly_path.parent.mkdir(parents=True, exist_ok=True)
            vision_path.parent.mkdir(parents=True, exist_ok=True)
            hourly_path.write_text(
                json.dumps(
                    [
                        {
                            "time_range": "09:00 PM - 10:00 PM",
                            "start_time": "2026-04-29T21:00:00-04:00",
                            "end_time": "2026-04-29T22:00:00-04:00",
                            "notes": [],
                            "categories": [
                                {
                                    "category": "study",
                                    "category_display": "Study",
                                    "total_minutes": 4,
                                    "activity_count": 2,
                                    "titles": ["Code"],
                                }
                            ],
                        }
                    ]
                ),
                encoding="utf-8",
            )
            vision_path.write_text(
                json.dumps(
                    [
                        {
                            "captured_at": "2026-04-29T21:09:47-04:00",
                            "summary": "Reviewed a resume-related chatbot.",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            note = module.generate_and_persist_hourly_note(
                temp_dir,
                "2026-04-29",
                "2026-04-29T21:00:00-04:00",
            )
            saved = json.loads(hourly_path.read_text(encoding="utf-8"))

        self.assertEqual(note, "Hourly note. Email [redacted-email]")
        self.assertEqual(saved[0]["notes"], ["Hourly note. Email [redacted-email]"])
        mock_request_hourly_note.assert_called_once()

    @mock.patch("journal.hourly_summary.generate_and_persist_hourly_note", return_value="Hourly note.")
    def test_generate_previous_hour_note_if_missing_generates_for_completed_previous_hour(
        self,
        mock_generate_and_persist_hourly_note,
    ):
        module = importlib.import_module("journal.hourly_summary")
        with tempfile.TemporaryDirectory() as temp_dir:
            hourly_path = Path(temp_dir) / "hourly_summaries" / "2026-04-29.json"
            hourly_path.parent.mkdir(parents=True, exist_ok=True)
            hourly_path.write_text(
                json.dumps(
                    [
                        {
                            "time_range": "08:00 PM - 09:00 PM",
                            "start_time": "2026-04-29T20:00:00-04:00",
                            "end_time": "2026-04-29T21:00:00-04:00",
                            "notes": [],
                            "categories": [],
                        }
                    ]
                ),
                encoding="utf-8",
            )

            note = module.generate_previous_hour_note_if_missing(
                temp_dir,
                datetime(2026, 4, 29, 21, 9, 47, tzinfo=LOCAL_TZ),
            )

        self.assertEqual(note, "Hourly note.")
        mock_generate_and_persist_hourly_note.assert_called_once_with(
            temp_dir,
            "2026-04-29",
            "2026-04-29T20:00:00-04:00",
        )

    @mock.patch("journal.hourly_summary.generate_and_persist_hourly_note")
    def test_generate_previous_hour_note_if_missing_skips_when_note_already_exists(
        self,
        mock_generate_and_persist_hourly_note,
    ):
        module = importlib.import_module("journal.hourly_summary")
        with tempfile.TemporaryDirectory() as temp_dir:
            hourly_path = Path(temp_dir) / "hourly_summaries" / "2026-04-29.json"
            hourly_path.parent.mkdir(parents=True, exist_ok=True)
            hourly_path.write_text(
                json.dumps(
                    [
                        {
                            "time_range": "08:00 PM - 09:00 PM",
                            "start_time": "2026-04-29T20:00:00-04:00",
                            "end_time": "2026-04-29T21:00:00-04:00",
                            "notes": ["Existing note."],
                            "categories": [],
                        }
                    ]
                ),
                encoding="utf-8",
            )

            note = module.generate_previous_hour_note_if_missing(
                temp_dir,
                datetime(2026, 4, 29, 21, 9, 47, tzinfo=LOCAL_TZ),
            )

        self.assertIsNone(note)
        mock_generate_and_persist_hourly_note.assert_not_called()


class OverallSummaryTests(SimpleTestCase):
    @mock.patch("journal.overall_summary.subprocess.run")
    def test_moderate_text_with_llama_guard3_returns_redacted_text_for_safe_content(
        self,
        mock_run,
    ):
        module = importlib.import_module("journal.overall_summary")
        response = mock.Mock()
        response.stdout = json.dumps({"message": {"content": "safe"}})
        mock_run.return_value = response

        result = module.moderate_text_with_llama_guard3(
            "Contact ricardo@example.com for details."
        )

        self.assertTrue(result["allowed"])
        self.assertEqual(result["label"], "safe")
        self.assertEqual(result["text"], "Contact [redacted-email] for details.")

    @mock.patch("journal.overall_summary.subprocess.run")
    def test_request_gemini_overall_summary_uses_env_key_and_returns_summary_text(
        self,
        mock_run,
    ):
        module = importlib.import_module("journal.overall_summary")
        response = mock.Mock()
        response.stdout = json.dumps(
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": "Most of the day was spent studying and job searching."
                                }
                            ]
                        }
                    }
                ]
            }
        )
        mock_run.return_value = response
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text("GEMINI_API_KEY=test-key\n", encoding="utf-8")

            summary = module.request_gemini_overall_summary(
                [{"captured_at": "2026-04-29T21:09:47-04:00", "summary": "Reviewed jobs."}],
                [{"time_range": "09:00 PM - 10:00 PM", "categories": []}],
                env_path=env_path,
            )

        self.assertEqual(summary, "Most of the day was spent studying and job searching.")
        command = mock_run.call_args.args[0]
        self.assertIn("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent", command)
        self.assertIn("x-goog-api-key: test-key", command)

    @mock.patch(
        "journal.overall_summary.request_gemini_overall_summary",
        return_value="Overall day summary.",
    )
    @mock.patch(
        "journal.overall_summary.moderate_vision_summaries",
        return_value=(
            [{"captured_at": "2026-04-29T21:09:47-04:00", "summary": "Reviewed jobs."}],
            [{"captured_at": "2026-04-29T21:09:47-04:00", "allowed": True, "label": "safe"}],
        ),
    )
    def test_generate_and_persist_overall_summary_writes_output_file(
        self,
        mock_moderate_vision_summaries,
        mock_request_gemini_overall_summary,
    ):
        module = importlib.import_module("journal.overall_summary")
        with tempfile.TemporaryDirectory() as temp_dir:
            vision_path = Path(temp_dir) / "vision_summaries" / "2026-04-29.json"
            hourly_path = Path(temp_dir) / "hourly_summaries" / "2026-04-29.json"
            vision_path.parent.mkdir(parents=True, exist_ok=True)
            hourly_path.parent.mkdir(parents=True, exist_ok=True)
            vision_path.write_text(
                json.dumps(
                    [
                        {
                            "captured_at": "2026-04-29T21:09:47-04:00",
                            "summary": "Reviewed jobs.",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            hourly_path.write_text(
                json.dumps(
                    [
                        {
                            "time_range": "09:00 PM - 10:00 PM",
                            "start_time": "2026-04-29T21:00:00-04:00",
                            "end_time": "2026-04-29T22:00:00-04:00",
                            "notes": [],
                            "categories": [],
                        }
                    ]
                ),
                encoding="utf-8",
            )

            payload = module.generate_and_persist_overall_summary(
                temp_dir,
                "2026-04-29",
                env_path=Path(temp_dir) / ".env",
            )
            saved = json.loads(
                (
                    Path(temp_dir)
                    / "overall_summaries"
                    / "2026-04-29.json"
                ).read_text(encoding="utf-8")
            )

        self.assertEqual(payload["overall_summary"], "Overall day summary.")
        self.assertEqual(saved["overall_summary"], "Overall day summary.")
        mock_moderate_vision_summaries.assert_called_once()
        mock_request_gemini_overall_summary.assert_called_once()

    @mock.patch(
        "journal.overall_summary.moderate_text_with_llama_guard3",
        side_effect=ValueError("Moderation response was empty."),
    )
    def test_moderate_vision_summaries_falls_back_to_sanitize_when_moderation_fails(
        self,
        mock_moderate_text_with_llama_guard3,
    ):
        module = importlib.import_module("journal.overall_summary")

        clean_entries, moderation_results = module.moderate_vision_summaries(
            [
                {
                    "captured_at": "2026-04-29T21:09:47-04:00",
                    "summary": "Contact ricardo@example.com about the resume.",
                }
            ]
        )

        self.assertEqual(
            clean_entries,
            [
                {
                    "captured_at": "2026-04-29T21:09:47-04:00",
                    "summary": "Contact [redacted-email] about the resume.",
                }
            ],
        )
        self.assertEqual(
            moderation_results,
            [
                {
                    "captured_at": "2026-04-29T21:09:47-04:00",
                    "allowed": True,
                    "label": "fallback-sanitize",
                }
            ],
        )
        mock_moderate_text_with_llama_guard3.assert_called_once()

class ActivityIngestTests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.base_dir = Path(self.temp_dir.name)
        self.user = User.objects.create_user(username="tracker", password="secret-pass")

    def test_persist_session_creates_activity_and_local_log(self):
        from journal.activity_ingest import persist_session

        session = ActivitySession(
            title="Visual Studio Code",
            category="work",
            description="Tracked active window from com.microsoft.VSCode.",
            started_at="2026-04-29T08:00:00Z",
            ended_at="2026-04-29T08:30:00Z",
            created_at="2026-04-29T08:30:00Z",
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
            title="Safari",
            category="study",
            description="Tracked active window from Safari.",
            started_at="2026-04-29T08:00:00Z",
            ended_at="2026-04-29T08:30:00Z",
            created_at="2026-04-29T08:30:00Z",
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
                    "category": "communication",
                    "description": "Tracked Zoom meeting.",
                    "started_at": "2026-04-29T09:00:00Z",
                    "ended_at": "2026-04-29T09:15:00Z",
                    "created_at": "2026-04-29T09:15:00Z",
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

    @mock.patch("journal.views.stop_tracking")
    @mock.patch("journal.views.start_tracking")
    def test_tracking_endpoint_starts_and_stops_runtime_tracker(
        self,
        mock_start_tracking,
        mock_stop_tracking,
    ):
        mock_start_tracking.return_value = {
            "tracking": True,
            "started_at": "2026-04-29T09:00:00Z",
            "already_active": False,
            "interval_seconds": 5.0,
        }
        mock_stop_tracking.return_value = {
            "tracking": False,
            "activity": None,
            "summary": None,
            "already_inactive": False,
        }

        with self.settings(BASE_DIR=Path(self.temp_dir.name)):
            start_response = self.client.post(
                reverse("activity-tracking"),
                data={"enabled": True},
                content_type="application/json",
            )
            stop_response = self.client.post(
                reverse("activity-tracking"),
                data={"enabled": False},
                content_type="application/json",
            )

        self.assertEqual(start_response.status_code, status.HTTP_200_OK)
        self.assertTrue(start_response.json()["tracking"])
        self.assertEqual(stop_response.status_code, status.HTTP_200_OK)
        self.assertFalse(stop_response.json()["tracking"])
        self.assertEqual(start_response.json()["interval_seconds"], 5.0)
        mock_start_tracking.assert_called_once_with(self.user)
        mock_stop_tracking.assert_called_once_with(self.user)


class CollectActivityCommandTests(SimpleTestCase):
    @mock.patch("journal.management.commands.collect_activity.subprocess.run")
    def test_prepare_image_for_vision_creates_resized_temp_png(self, mock_run):
        command_module = importlib.import_module(
            "journal.management.commands.collect_activity"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "shot.png"
            source_path.write_bytes(b"img")

            resized_path = command_module.prepare_image_for_vision(source_path)

        self.assertEqual(resized_path.suffix, ".png")
        mock_run.assert_called_once()
        self.assertIn("sips", mock_run.call_args.args[0][0])
        self.assertIn("-Z", mock_run.call_args.args[0])

    def test_list_recent_screenshots_returns_latest_twelve_sorted(self):
        command_module = importlib.import_module(
            "journal.management.commands.collect_activity"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            screenshot_dir = Path(temp_dir) / "screenshots" / "2026-04-29"
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            for second in range(13):
                (screenshot_dir / f"14-00-{second:02d}.png").write_bytes(b"img")

            screenshots = command_module.list_recent_screenshots(
                temp_dir,
                datetime(2026, 4, 29, 14, 1, 0, tzinfo=timezone.utc),
            )

        self.assertEqual(len(screenshots), 12)
        self.assertEqual(screenshots[0].name, "14-00-01.png")
        self.assertEqual(screenshots[-1].name, "14-00-12.png")

    def test_generate_minute_summary_returns_none_when_no_screenshots_exist(self):
        command_module = importlib.import_module(
            "journal.management.commands.collect_activity"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            summary = command_module.generate_minute_summary(
                temp_dir,
                datetime(2026, 4, 29, 14, 1, 0, tzinfo=timezone.utc),
            )

        self.assertIsNone(summary)

    @mock.patch("journal.management.commands.collect_activity.multiprocessing.Process")
    def test_start_minute_summary_process_starts_non_daemon_process(
        self,
        mock_process_class,
    ):
        command_module = importlib.import_module(
            "journal.management.commands.collect_activity"
        )
        process = mock.Mock()
        mock_process_class.return_value = process
        reference_time = datetime(2026, 4, 29, 14, 1, 0, tzinfo=timezone.utc)

        started_process = command_module.start_minute_summary_process(
            "/tmp/journalise",
            reference_time,
        )

        mock_process_class.assert_called_once_with(
            target=command_module.generate_and_persist_minute_summary,
            args=("/tmp/journalise", reference_time.isoformat()),
            daemon=False,
        )
        process.start.assert_called_once_with()
        self.assertIs(started_process, process)

    @mock.patch("journal.management.commands.collect_activity.print")
    @mock.patch("journal.management.commands.collect_activity.multiprocessing.Process")
    def test_start_minute_summary_process_logs_dispatch(
        self,
        mock_process_class,
        mock_print,
    ):
        command_module = importlib.import_module(
            "journal.management.commands.collect_activity"
        )
        process = mock.Mock()
        mock_process_class.return_value = process
        reference_time = datetime(2026, 4, 29, 14, 1, 0, tzinfo=timezone.utc)

        command_module.start_minute_summary_process(
            "/tmp/journalise",
            reference_time,
        )

        mock_print.assert_any_call(
            f"Dispatched minute summary for {reference_time.isoformat()}"
        )

    @mock.patch("journal.management.commands.collect_activity.print")
    @mock.patch("journal.management.commands.collect_activity.start_minute_summary_process")
    def test_run_minute_summary_loop_skips_new_work_while_previous_summary_is_running(
        self,
        mock_start_minute_summary_process,
        mock_print,
    ):
        command_module = importlib.import_module(
            "journal.management.commands.collect_activity"
        )
        stop_event = mock.Mock()
        stop_event.is_set.return_value = False
        stop_event.wait.side_effect = [False, True]
        process = mock.Mock()
        process.is_alive.return_value = True
        mock_start_minute_summary_process.return_value = process

        command_module.run_minute_summary_loop(
            "/tmp/journalise",
            stop_event,
            summary_interval=60.0,
        )

        mock_start_minute_summary_process.assert_called_once()
        process.join.assert_not_called()
        mock_print.assert_any_call("Minute summary still running; skipping new request.")

    @mock.patch("journal.management.commands.collect_activity.start_minute_summary_process")
    def test_run_minute_summary_loop_leaves_started_summary_running_on_stop(
        self,
        mock_start_minute_summary_process,
    ):
        command_module = importlib.import_module(
            "journal.management.commands.collect_activity"
        )
        stop_event = mock.Mock()
        stop_event.is_set.return_value = False
        stop_event.wait.return_value = True
        process = mock.Mock()
        process.is_alive.return_value = True
        mock_start_minute_summary_process.return_value = process

        command_module.run_minute_summary_loop(
            "/tmp/journalise",
            stop_event,
            summary_interval=60.0,
        )

        mock_start_minute_summary_process.assert_called_once()
        process.join.assert_not_called()

    @mock.patch("journal.management.commands.collect_activity.print")
    @mock.patch("journal.management.commands.collect_activity.generate_previous_hour_note_if_missing")
    @mock.patch("journal.management.commands.collect_activity.append_vision_summary")
    @mock.patch("journal.management.commands.collect_activity.generate_minute_summary")
    def test_generate_and_persist_minute_summary_logs_saved_summary(
        self,
        mock_generate_minute_summary,
        mock_append_vision_summary,
        mock_generate_previous_hour_note_if_missing,
        mock_print,
    ):
        command_module = importlib.import_module(
            "journal.management.commands.collect_activity"
        )
        mock_generate_minute_summary.return_value = (
            datetime(2026, 4, 29, 14, 1, 0, tzinfo=timezone.utc),
            "Interesting work is happening.",
        )

        command_module.generate_and_persist_minute_summary(
            "/tmp/journalise",
            "2026-04-29T11:01:00-04:00",
        )

        mock_append_vision_summary.assert_called_once_with(
            "/tmp/journalise",
            datetime(2026, 4, 29, 14, 1, 0, tzinfo=timezone.utc),
            "Interesting work is happening.",
        )
        mock_generate_previous_hour_note_if_missing.assert_called_once_with(
            "/tmp/journalise",
            datetime(2026, 4, 29, 14, 1, 0, tzinfo=timezone.utc),
        )
        mock_print.assert_any_call("Starting minute summary for 2026-04-29T11:01:00-04:00")
        mock_print.assert_any_call("Saved vision summary for 2026-04-29T14:01:00+00:00")

    @mock.patch("journal.management.commands.collect_activity.print")
    @mock.patch(
        "journal.management.commands.collect_activity.generate_previous_hour_note_if_missing",
        return_value="Hourly note.",
    )
    @mock.patch("journal.management.commands.collect_activity.append_vision_summary")
    @mock.patch("journal.management.commands.collect_activity.generate_minute_summary")
    def test_generate_and_persist_minute_summary_logs_saved_hourly_note(
        self,
        mock_generate_minute_summary,
        mock_append_vision_summary,
        mock_generate_previous_hour_note_if_missing,
        mock_print,
    ):
        command_module = importlib.import_module(
            "journal.management.commands.collect_activity"
        )
        screenshot_time = datetime(2026, 4, 29, 21, 9, 47, tzinfo=LOCAL_TZ)
        mock_generate_minute_summary.return_value = (
            screenshot_time,
            "Interesting work is happening.",
        )

        command_module.generate_and_persist_minute_summary(
            "/tmp/journalise",
            "2026-04-29T21:09:47-04:00",
        )

        mock_generate_previous_hour_note_if_missing.assert_called_once_with(
            "/tmp/journalise",
            screenshot_time,
        )
        mock_print.assert_any_call("Saved hourly note for 2026-04-29T20:00:00-04:00")

    @mock.patch("journal.management.commands.collect_activity.prepare_image_for_vision")
    @mock.patch("journal.management.commands.collect_activity.subprocess.Popen")
    @mock.patch("journal.management.commands.collect_activity.tempfile.NamedTemporaryFile")
    def test_request_vision_summary_returns_summary_text(
        self,
        mock_named_temporary_file,
        mock_popen,
        mock_prepare_image_for_vision,
    ):
        command_module = importlib.import_module(
            "journal.management.commands.collect_activity"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            screenshot_paths = []
            for index in range(1):
                path = Path(temp_dir) / f"shot-{index}.png"
                path.write_bytes(b"img")
                screenshot_paths.append(path)
            resized_path = Path(temp_dir) / "shot-resized.png"
            resized_path.write_bytes(b"small-img")
            mock_prepare_image_for_vision.return_value = resized_path

            payload_path = Path(temp_dir) / "ollama-payload.json"
            class FakeTempFile:
                def __init__(self, path):
                    self.name = str(path)

                def write(self, text):
                    payload_path.write_text(text, encoding="utf-8")

            payload_file = FakeTempFile(payload_path)
            temp_file_context = mock.Mock()
            temp_file_context.__enter__ = mock.Mock(return_value=payload_file)
            temp_file_context.__exit__ = mock.Mock(return_value=False)
            mock_named_temporary_file.return_value = temp_file_context

            process = mock.Mock()
            process.stdout = iter(
                [
                    json.dumps(
                        {
                            "message": {
                                "content": '{"summary":"The user was ',
                            },
                            "done": False,
                        }
                    )
                    + "\n",
                    json.dumps(
                        {
                            "message": {
                                "content": 'coding and reading documentation."}',
                            },
                            "done": False,
                        }
                    )
                    + "\n",
                    json.dumps({"message": {"content": ""}, "done": True}) + "\n",
                ]
            )
            process.wait.return_value = 0
            process.stderr.read.return_value = ""
            mock_popen.return_value.__enter__.return_value = process

            with mock.patch("journal.management.commands.collect_activity.Path.unlink") as mock_unlink:
                summary = command_module.request_vision_summary(screenshot_paths)
            curl_command = mock_popen.call_args.args[0]
            request_payload = json.loads(payload_path.read_text(encoding="utf-8"))

        self.assertEqual(summary, "The user was coding and reading documentation.")
        mock_prepare_image_for_vision.assert_called_once_with(screenshot_paths[0])
        mock_unlink.assert_any_call(missing_ok=True)
        self.assertEqual(request_payload["model"], "qwen2.5vl:7b")
        self.assertTrue(request_payload["stream"])
        self.assertIn("active or most prominent window/screen", request_payload["messages"][0]["content"])
        self.assertIn("activity-tracking sentence", request_payload["messages"][0]["content"])
        self.assertNotIn("window_start", request_payload["messages"][0]["content"])
        self.assertEqual(len(request_payload["messages"][0]["images"]), 1)
        self.assertEqual(curl_command[:5], ["curl", "-sS", "-N", "-X", "POST"])
        self.assertIn("/api/chat", curl_command[5])

    def test_append_vision_summary_persists_screenshot_summary_event(self):
        command_module = importlib.import_module(
            "journal.management.commands.collect_activity"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            summary = "The user was coding and reading documentation. Contact: ricardo@example.com"
            reference_time = datetime(2026, 4, 29, 13, 14, 0, tzinfo=LOCAL_TZ)

            command_module.append_vision_summary(
                temp_dir,
                reference_time,
                summary,
            )

            saved = json.loads(
                (
                    Path(temp_dir)
                    / "vision_summaries"
                    / "2026-04-29.json"
                ).read_text(encoding="utf-8")
            )

        self.assertEqual(
            saved,
            [
                {
                    "captured_at": "2026-04-29T13:14:00-04:00",
                    "summary": "The user was coding and reading documentation. Contact: [redacted-email]",
                }
            ],
        )

    def test_append_vision_summary_appends_multiple_summaries(self):
        command_module = importlib.import_module(
            "journal.management.commands.collect_activity"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            first_summary = "First screenshot summary."
            second_summary = "Second screenshot summary."
            first_time = datetime(2026, 4, 29, 13, 14, 0, tzinfo=LOCAL_TZ)
            second_time = datetime(2026, 4, 29, 13, 39, 0, tzinfo=LOCAL_TZ)

            command_module.append_vision_summary(
                temp_dir,
                first_time,
                first_summary,
            )
            command_module.append_vision_summary(
                temp_dir,
                second_time,
                second_summary,
            )

            saved = json.loads(
                (
                    Path(temp_dir)
                    / "vision_summaries"
                    / "2026-04-29.json"
                ).read_text(encoding="utf-8")
            )

        self.assertEqual(len(saved), 2)
        self.assertEqual(saved[0]["summary"], first_summary)
        self.assertEqual(saved[1]["summary"], second_summary)

    def test_append_vision_summary_writes_pretty_printed_json_with_newlines(self):
        command_module = importlib.import_module(
            "journal.management.commands.collect_activity"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            summary = "The user was coding and reading documentation."
            reference_time = datetime(2026, 4, 29, 13, 14, 0, tzinfo=LOCAL_TZ)

            command_module.append_vision_summary(
                temp_dir,
                reference_time,
                summary,
            )

            contents = (
                Path(temp_dir)
                / "vision_summaries"
                / "2026-04-29.json"
            ).read_text(encoding="utf-8")

        self.assertIn('\n  {\n', contents)
        self.assertIn('\n    "summary": "The user was coding and reading documentation."\n', contents)
        self.assertTrue(contents.endswith("\n"))

    def test_build_screenshot_path_uses_day_directory_and_timestamp_filename(self):
        command_module = importlib.import_module(
            "journal.management.commands.collect_activity"
        )
        captured_at = datetime(2026, 4, 29, 14, 30, 5, tzinfo=LOCAL_TZ)

        screenshot_path = command_module.build_screenshot_path(
            "/tmp/journalise",
            captured_at,
        )

        self.assertEqual(screenshot_path.name, "14-30-05.png")
        self.assertEqual(screenshot_path.parent.name, "2026-04-29")
        self.assertEqual(screenshot_path.parent.parent.name, "screenshots")

    @mock.patch("journal.management.commands.collect_activity.capture_screenshot")
    @mock.patch("journal.management.commands.collect_activity.datetime")
    def test_run_screenshot_loop_captures_screenshot_and_waits_for_interval(
        self,
        mock_datetime,
        mock_capture_screenshot,
    ):
        command_module = importlib.import_module(
            "journal.management.commands.collect_activity"
        )
        stop_event = mock.Mock()
        stop_event.is_set.return_value = False
        stop_event.wait.return_value = True
        captured_at = datetime(2026, 4, 29, 14, 30, 5, tzinfo=timezone.utc)
        mock_datetime.now.return_value = captured_at

        command_module.run_screenshot_loop(
            "/tmp/journalise",
            5.0,
            stop_event,
        )

        mock_capture_screenshot.assert_called_once_with("/tmp/journalise", captured_at)
        stop_event.wait.assert_called_once_with(5.0)

    @mock.patch("journal.management.commands.collect_activity.print")
    @mock.patch(
        "journal.management.commands.collect_activity.capture_screenshot",
        side_effect=RuntimeError("screen capture failed"),
    )
    @mock.patch("journal.management.commands.collect_activity.datetime")
    def test_run_screenshot_loop_logs_failure_and_keeps_running(
        self,
        mock_datetime,
        mock_capture_screenshot,
        mock_print,
    ):
        command_module = importlib.import_module(
            "journal.management.commands.collect_activity"
        )
        stop_event = mock.Mock()
        stop_event.is_set.return_value = False
        stop_event.wait.return_value = True
        captured_at = datetime(2026, 4, 29, 14, 30, 5, tzinfo=timezone.utc)
        mock_datetime.now.return_value = captured_at

        command_module.run_screenshot_loop(
            "/tmp/journalise",
            5.0,
            stop_event,
        )

        mock_capture_screenshot.assert_called_once_with("/tmp/journalise", captured_at)
        mock_print.assert_any_call("Error capturing screenshot: screen capture failed")

    @mock.patch("journal.management.commands.collect_activity.rebuild_hourly_summary_for_date")
    @mock.patch("journal.management.commands.collect_activity.resolve_app_category", return_value="study")
    @mock.patch("journal.management.commands.collect_activity.append_session")
    def test_persist_finished_session_appends_session_for_end_date(
        self,
        mock_append_session,
        mock_resolve_app_category,
        mock_rebuild_hourly_summary,
    ):
        command_module = importlib.import_module(
            "journal.management.commands.collect_activity"
        )
        ended_at = datetime(2026, 4, 29, 21, 15, tzinfo=timezone.utc)
        session = make_session(
            started_at="2026-04-29T20:45:00Z",
            ended_at="2026-04-29T21:15:00Z",
            created_at="2026-04-29T21:15:00Z",
        )

        command_module.persist_finished_session("/tmp/journalise", ended_at, session)

        mock_resolve_app_category.assert_called_once_with("/tmp/journalise", "Safari")
        self.assertEqual(session.category, "study")
        mock_append_session.assert_called_once_with(
            "/tmp/journalise",
            "2026-04-29",
            session,
        )
        mock_rebuild_hourly_summary.assert_called_once_with("/tmp/journalise", "2026-04-29")

    @mock.patch("journal.management.commands.collect_activity.rebuild_hourly_summary_for_date")
    @mock.patch("journal.management.commands.collect_activity.resolve_app_category", return_value="study")
    @mock.patch("journal.management.commands.collect_activity.append_session")
    def test_persist_finished_session_uses_est_date_for_utc_timestamp_string(
        self,
        mock_append_session,
        mock_resolve_app_category,
        mock_rebuild_hourly_summary,
    ):
        command_module = importlib.import_module(
            "journal.management.commands.collect_activity"
        )
        session = make_session(
            title="Code",
            ended_at="2026-04-30T00:28:55Z",
            created_at="2026-04-30T00:28:55Z",
        )

        command_module.persist_finished_session(
            "/tmp/journalise",
            "2026-04-30T00:28:55Z",
            session,
        )

        mock_resolve_app_category.assert_called_once_with("/tmp/journalise", "Code")
        mock_append_session.assert_called_once_with(
            "/tmp/journalise",
            "2026-04-29",
            session,
        )
        mock_rebuild_hourly_summary.assert_called_once_with("/tmp/journalise", "2026-04-29")

    @mock.patch("journal.management.commands.collect_activity.rebuild_hourly_summary_for_date")
    @mock.patch("journal.management.commands.collect_activity.resolve_app_category", return_value="study")
    @mock.patch("journal.management.commands.collect_activity.append_session")
    def test_persist_finished_session_uses_est_date_for_est_timestamp_string(
        self,
        mock_append_session,
        mock_resolve_app_category,
        mock_rebuild_hourly_summary,
    ):
        command_module = importlib.import_module(
            "journal.management.commands.collect_activity"
        )
        session = make_session(
            title="Code",
            ended_at="2026-04-29T20:28:55-04:00",
            created_at="2026-04-29T20:28:55-04:00",
        )

        command_module.persist_finished_session(
            "/tmp/journalise",
            "2026-04-29T20:28:55-04:00",
            session,
        )

        mock_resolve_app_category.assert_called_once_with("/tmp/journalise", "Code")
        mock_append_session.assert_called_once_with(
            "/tmp/journalise",
            "2026-04-29",
            session,
        )
        mock_rebuild_hourly_summary.assert_called_once_with("/tmp/journalise", "2026-04-29")

    @mock.patch("journal.management.commands.collect_activity.print")
    @mock.patch("journal.management.commands.collect_activity.time.sleep")
    @mock.patch("journal.management.commands.collect_activity.persist_finished_session")
    @mock.patch("journal.management.commands.collect_activity.get_frontmost_app")
    @mock.patch("journal.management.commands.collect_activity.datetime")
    def test_run_collector_skips_writing_when_foreground_app_is_unchanged(
        self,
        mock_datetime,
        mock_get_frontmost_app,
        mock_persist_finished_session,
        mock_sleep,
        mock_print,
    ):
        command_module = importlib.import_module(
            "journal.management.commands.collect_activity"
        )
        first_now = datetime(2026, 4, 29, 8, 0, tzinfo=timezone.utc)
        second_now = datetime(2026, 4, 29, 8, 10, tzinfo=timezone.utc)
        stopped_now = datetime(2026, 4, 29, 8, 30, tzinfo=timezone.utc)
        mock_datetime.now.side_effect = [first_now, second_now, stopped_now]
        mock_get_frontmost_app.side_effect = ["Code", "Code"]
        mock_sleep.side_effect = [None, KeyboardInterrupt()]

        command_module.run_collector(base_dir="/tmp/journalise", interval=2.0)

        mock_persist_finished_session.assert_called_once()
        persisted_session = mock_persist_finished_session.call_args.args[2]
        self.assertEqual(
            persisted_session,
            make_session(
                title="Code",
                started_at="2026-04-29T04:00:00-04:00",
                ended_at="2026-04-29T04:30:00-04:00",
                created_at="2026-04-29T04:30:00-04:00",
            ),
        )
        mock_print.assert_any_call("Collector stopped.")

    @mock.patch("journal.management.commands.collect_activity.print")
    @mock.patch("journal.management.commands.collect_activity.time.sleep")
    @mock.patch("journal.management.commands.collect_activity.persist_finished_session")
    @mock.patch("journal.management.commands.collect_activity.get_frontmost_app")
    @mock.patch("journal.management.commands.collect_activity.datetime")
    def test_run_collector_persists_previous_session_when_foreground_app_changes(
        self,
        mock_datetime,
        mock_get_frontmost_app,
        mock_persist_finished_session,
        mock_sleep,
        mock_print,
    ):
        command_module = importlib.import_module(
            "journal.management.commands.collect_activity"
        )
        first_now = datetime(2026, 4, 29, 8, 0, tzinfo=timezone.utc)
        changed_now = datetime(2026, 4, 29, 8, 45, tzinfo=timezone.utc)
        stopped_now = datetime(2026, 4, 29, 9, 15, tzinfo=timezone.utc)
        mock_datetime.now.side_effect = [first_now, changed_now, stopped_now]
        mock_get_frontmost_app.side_effect = ["Code", "Notes"]
        mock_sleep.side_effect = [None, KeyboardInterrupt()]

        command_module.run_collector(base_dir="/tmp/journalise", interval=2.0)

        self.assertEqual(mock_persist_finished_session.call_count, 2)
        first_session = mock_persist_finished_session.call_args_list[0].args[2]
        second_session = mock_persist_finished_session.call_args_list[1].args[2]
        self.assertEqual(
            first_session,
            make_session(
                title="Code",
                started_at="2026-04-29T04:00:00-04:00",
                ended_at="2026-04-29T04:45:00-04:00",
                created_at="2026-04-29T04:45:00-04:00",
            ),
        )
        self.assertEqual(
            second_session,
            make_session(
                title="Notes",
                started_at="2026-04-29T04:45:00-04:00",
                ended_at="2026-04-29T05:15:00-04:00",
                created_at="2026-04-29T05:15:00-04:00",
            ),
        )
        mock_print.assert_any_call("Collector stopped.")

    @mock.patch("journal.management.commands.collect_activity.print")
    @mock.patch("journal.management.commands.collect_activity.persist_finished_session")
    @mock.patch(
        "journal.management.commands.collect_activity.get_frontmost_app",
        side_effect=RuntimeError("frontmost read failed"),
    )
    def test_run_collector_logs_and_skips_failed_foreground_app_reads(
        self,
        mock_get_frontmost_app,
        mock_persist_finished_session,
        mock_print,
    ):
        command_module = importlib.import_module(
            "journal.management.commands.collect_activity"
        )

        command_module.run_collector(base_dir="/tmp/journalise", once=True)

        mock_persist_finished_session.assert_not_called()
        mock_print.assert_any_call("Error reading frontmost app: frontmost read failed")

    @mock.patch("journal.management.commands.collect_activity.stop_screenshot_worker")
    @mock.patch("journal.management.commands.collect_activity.start_screenshot_worker")
    @mock.patch("journal.management.commands.collect_activity.stop_minute_summary_worker")
    @mock.patch("journal.management.commands.collect_activity.start_minute_summary_worker")
    @mock.patch("journal.management.commands.collect_activity.persist_finished_session")
    @mock.patch("journal.management.commands.collect_activity.get_frontmost_app")
    @mock.patch("journal.management.commands.collect_activity.datetime")
    def test_run_collector_starts_and_stops_screenshot_and_minute_summary_workers_when_enabled(
        self,
        mock_datetime,
        mock_get_frontmost_app,
        mock_persist_finished_session,
        mock_start_minute_summary_worker,
        mock_stop_minute_summary_worker,
        mock_start_screenshot_worker,
        mock_stop_screenshot_worker,
    ):
        command_module = importlib.import_module(
            "journal.management.commands.collect_activity"
        )
        stop_event = object()
        worker = object()
        minute_stop_event = object()
        minute_worker = object()
        mock_start_screenshot_worker.return_value = (stop_event, worker)
        mock_start_minute_summary_worker.return_value = (minute_stop_event, minute_worker)
        mock_datetime.now.return_value = datetime(2026, 4, 29, 8, 0, tzinfo=timezone.utc)
        mock_get_frontmost_app.return_value = "Code"

        command_module.run_collector(
            base_dir="/tmp/journalise",
            once=True,
            screenshots=True,
            screenshot_interval=5.0,
            vision_summary=True,
        )

        mock_start_screenshot_worker.assert_called_once_with("/tmp/journalise", 5.0)
        mock_start_minute_summary_worker.assert_called_once_with("/tmp/journalise", 5.0)
        mock_stop_screenshot_worker.assert_called_once_with(stop_event, worker)
        mock_stop_minute_summary_worker.assert_called_once_with(
            minute_stop_event,
            minute_worker,
        )

    @mock.patch("journal.management.commands.collect_activity.run_collector")
    def test_collect_activity_command_delegates_to_run_collector(self, mock_run_collector):
        call_command("collect_activity")

        mock_run_collector.assert_called_once_with(
            base_dir="activity_data",
            interval=10.0,
            once=False,
            screenshots=False,
            screenshot_interval=300.0,
            vision_summary=False,
        )

    @mock.patch("journal.management.commands.collect_activity.print")
    @mock.patch("journal.management.commands.collect_activity.persist_finished_session")
    @mock.patch("journal.management.commands.collect_activity.get_frontmost_app", return_value="Code")
    @mock.patch("journal.management.commands.collect_activity.datetime")
    def test_run_collector_finalizes_active_session_when_stop_event_is_set(
        self,
        mock_datetime,
        mock_get_frontmost_app,
        mock_persist_finished_session,
        mock_print,
    ):
        command_module = importlib.import_module(
            "journal.management.commands.collect_activity"
        )
        stop_event = mock.Mock()
        stop_event.is_set.side_effect = [False, True]
        started_now = datetime(2026, 4, 29, 8, 0, tzinfo=timezone.utc)
        stopped_now = datetime(2026, 4, 29, 8, 30, tzinfo=timezone.utc)
        mock_datetime.now.side_effect = [started_now, stopped_now]

        command_module.run_collector(
            base_dir="/tmp/journalise",
            interval=2.0,
            stop_event=stop_event,
        )

        mock_persist_finished_session.assert_called_once()
        persisted_session = mock_persist_finished_session.call_args.args[2]
        self.assertEqual(
            persisted_session,
            make_session(
                title="Code",
                started_at="2026-04-29T04:00:00-04:00",
                ended_at="2026-04-29T04:30:00-04:00",
                created_at="2026-04-29T04:30:00-04:00",
            ),
        )
        mock_print.assert_any_call("Collector stopped.")


class RuntimeAPITests(SimpleTestCase):
    @mock.patch("journal.runtime.threading.Thread")
    def test_start_activity_tracking_starts_background_collector_thread(
        self,
        mock_thread_class,
    ):
        module = importlib.import_module("journal.runtime")
        worker = mock.Mock()
        mock_thread_class.return_value = worker

        handle = module.start_activity_tracking("/tmp/journalise", interval=15.0)

        kwargs = mock_thread_class.call_args.kwargs
        self.assertIs(kwargs["target"], importlib.import_module("journal.management.commands.collect_activity").run_collector)
        self.assertEqual(kwargs["kwargs"]["base_dir"], "/tmp/journalise")
        self.assertEqual(kwargs["kwargs"]["interval"], 15.0)
        self.assertFalse(kwargs["kwargs"]["screenshots"])
        self.assertFalse(kwargs["kwargs"]["vision_summary"])
        self.assertTrue(kwargs["daemon"])
        worker.start.assert_called_once_with()
        self.assertIs(handle.worker, worker)

    @mock.patch("journal.runtime.stop_screenshot_worker")
    @mock.patch("journal.runtime.stop_minute_summary_worker")
    @mock.patch("journal.runtime.start_minute_summary_worker")
    @mock.patch("journal.runtime.start_screenshot_worker")
    def test_start_screenshot_capture_supports_optional_vision_summary(
        self,
        mock_start_screenshot_worker,
        mock_start_minute_summary_worker,
        mock_stop_minute_summary_worker,
        mock_stop_screenshot_worker,
    ):
        module = importlib.import_module("journal.runtime")
        screenshot_stop_event = object()
        screenshot_worker = object()
        summary_stop_event = object()
        summary_worker = object()
        mock_start_screenshot_worker.return_value = (screenshot_stop_event, screenshot_worker)
        mock_start_minute_summary_worker.return_value = (summary_stop_event, summary_worker)

        handle = module.start_screenshot_capture(
            "/tmp/journalise",
            screenshot_interval=55.0,
            vision_summary=True,
        )
        handle.stop()

        mock_start_screenshot_worker.assert_called_once_with("/tmp/journalise", 55.0)
        mock_start_minute_summary_worker.assert_called_once_with("/tmp/journalise", 55.0)
        mock_stop_minute_summary_worker.assert_called_once_with(summary_stop_event, summary_worker)
        mock_stop_screenshot_worker.assert_called_once_with(screenshot_stop_event, screenshot_worker)
