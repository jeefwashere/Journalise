from django.test import SimpleTestCase
from unittest.mock import patch


class CalculateStatsTests(SimpleTestCase):
    def test_calculate_stats_returns_session_based_metrics(self):
        from summary.stats import calculate_stats

        activity_logs = [
            {
                "app_name": "Safari",
                "duration_seconds": 1800,
            },
            {
                "app_name": "Notes",
                "duration_seconds": 900,
            },
            {
                "app_name": "Safari",
                "duration_seconds": 1200,
            },
        ]

        self.assertEqual(
            calculate_stats(activity_logs),
            {
                "total_tracked_seconds": 3900,
                "session_count": 3,
                "top_apps": [
                    {"app_name": "Safari", "duration_seconds": 3000},
                    {"app_name": "Notes", "duration_seconds": 900},
                ],
                "productivity_score": 65,
            },
        )

    def test_calculate_stats_returns_zeroed_metrics_for_empty_logs(self):
        from summary.stats import calculate_stats

        self.assertEqual(
            calculate_stats([]),
            {
                "total_tracked_seconds": 0,
                "session_count": 0,
                "top_apps": [],
                "productivity_score": 0,
            },
        )

    def test_calculate_stats_caps_productivity_score_at_100(self):
        from summary.stats import calculate_stats

        self.assertEqual(
            calculate_stats(
                [
                    {
                        "app_name": "Cursor",
                        "duration_seconds": 7200,
                    }
                ]
            )["productivity_score"],
            100,
        )

    def test_calculate_stats_treats_invalid_durations_as_zero_and_uses_unknown_app(self):
        from summary.stats import calculate_stats

        self.assertEqual(
            calculate_stats(
                [
                    {
                        "duration_seconds": "bad",
                    },
                    {
                        "app_name": "Safari",
                        "duration_seconds": None,
                    },
                    {
                        "app_name": None,
                        "duration_seconds": 120,
                    },
                    {
                        "app_name": "Safari",
                    },
                ]
            ),
            {
                "total_tracked_seconds": 120,
                "session_count": 4,
                "top_apps": [
                    {"app_name": "Unknown", "duration_seconds": 120},
                ],
                "productivity_score": 2,
            },
        )

    def test_calculate_stats_treats_negative_durations_as_zero(self):
        from summary.stats import calculate_stats

        self.assertEqual(
            calculate_stats(
                [
                    {
                        "app_name": "Safari",
                        "duration_seconds": -60,
                    },
                    {
                        "app_name": "Notes",
                        "duration_seconds": 30,
                    },
                ]
            ),
            {
                "total_tracked_seconds": 30,
                "session_count": 2,
                "top_apps": [
                    {"app_name": "Notes", "duration_seconds": 30},
                ],
                "productivity_score": 0,
            },
        )


class SummaryServiceTests(SimpleTestCase):
    def test_generate_daily_summary_uses_ollama_when_available(self):
        from summary.services import generate_daily_summary

        activity_logs = [
            {
                "app_name": "Cursor",
                "duration_seconds": 1800,
            }
        ]
        ollama_response = {
            "accomplishments": ["Finished Task 6"],
            "journal": "Spent focused time coding in Cursor.",
            "productivity_score": 88,
        }

        with (
            patch(
                "summary.services.load_sessions_for_date",
                return_value=activity_logs,
            ) as mock_load_sessions,
            patch(
                "summary.services._generate_ollama_summary",
                return_value=ollama_response,
            ) as mock_generate,
        ):
            summary = generate_daily_summary("2026-04-29", base_dir="/tmp/journalise")

        self.assertEqual(
            summary,
            {
                "date": "2026-04-29",
                "stats": {
                    "total_tracked_seconds": 1800,
                    "session_count": 1,
                    "top_apps": [
                        {"app_name": "Cursor", "duration_seconds": 1800},
                    ],
                    "productivity_score": 30,
                },
                "accomplishments": ["Finished Task 6"],
                "journal": "Spent focused time coding in Cursor.",
                "productivity_score": 88,
                "source": "ollama",
            },
        )
        mock_load_sessions.assert_called_once_with("/tmp/journalise", "2026-04-29")
        mock_generate.assert_called_once_with(
            "2026-04-29",
            {
                "total_tracked_seconds": 1800,
                "session_count": 1,
                "top_apps": [
                    {"app_name": "Cursor", "duration_seconds": 1800},
                ],
                "productivity_score": 30,
            },
            activity_logs,
        )

    def test_build_fallback_summary_returns_stable_shape(self):
        from summary.services import build_fallback_summary

        activity_logs = [
            {
                "app_name": "Cursor",
                "duration_seconds": 1800,
            }
        ]
        stats = {
            "total_tracked_seconds": 1800,
            "session_count": 1,
            "top_apps": [
                {"app_name": "Cursor", "duration_seconds": 1800},
            ],
            "productivity_score": 30,
        }

        self.assertEqual(
            build_fallback_summary("2026-04-29", stats, activity_logs),
            {
                "date": "2026-04-29",
                "stats": stats,
                "accomplishments": ["Tracked 1 activity session."],
                "journal": "Recorded 1 activity session across 30 minutes.",
                "productivity_score": 30,
                "source": "fallback",
            },
        )

    def test_generate_daily_summary_falls_back_when_ollama_fails(self):
        from summary.services import generate_daily_summary

        activity_logs = [
            {
                "app_name": "Safari",
                "duration_seconds": 1200,
            }
        ]

        with (
            patch(
                "summary.services.load_sessions_for_date",
                return_value=activity_logs,
            ) as mock_load_sessions,
            patch(
                "summary.services._generate_ollama_summary",
                side_effect=RuntimeError("Ollama unavailable"),
            ) as mock_generate,
        ):
            summary = generate_daily_summary("2026-04-29", base_dir="/tmp/journalise")

        mock_load_sessions.assert_called_once_with("/tmp/journalise", "2026-04-29")
        mock_generate.assert_called_once_with(
            "2026-04-29",
            {
                "total_tracked_seconds": 1200,
                "session_count": 1,
                "top_apps": [
                    {"app_name": "Safari", "duration_seconds": 1200},
                ],
                "productivity_score": 20,
            },
            activity_logs,
        )
        self.assertEqual(summary["date"], "2026-04-29")
        self.assertEqual(summary["source"], "fallback")
        self.assertEqual(summary["stats"]["total_tracked_seconds"], 1200)
        self.assertEqual(summary["stats"]["session_count"], 1)
        self.assertEqual(summary["productivity_score"], 20)
        self.assertEqual(summary["accomplishments"], ["Tracked 1 activity session."])

    def test_generate_daily_summary_uses_default_data_dir_for_empty_logs(self):
        from django.conf import settings
        from summary.services import generate_daily_summary

        with (
            patch(
                "summary.services.load_sessions_for_date",
                return_value=[],
            ) as mock_load_sessions,
            patch(
                "summary.services._generate_ollama_summary",
                side_effect=RuntimeError("Ollama unavailable"),
            ) as mock_generate,
        ):
            summary = generate_daily_summary("2026-04-29")

        mock_load_sessions.assert_called_once_with(settings.BASE_DIR / "data", "2026-04-29")
        mock_generate.assert_called_once_with(
            "2026-04-29",
            {
                "total_tracked_seconds": 0,
                "session_count": 0,
                "top_apps": [],
                "productivity_score": 0,
            },
            [],
        )
        self.assertEqual(
            summary,
            {
                "date": "2026-04-29",
                "stats": {
                    "total_tracked_seconds": 0,
                    "session_count": 0,
                    "top_apps": [],
                    "productivity_score": 0,
                },
                "accomplishments": ["Tracked 0 activity sessions."],
                "journal": "Recorded 0 activity sessions across 0 minutes.",
                "productivity_score": 0,
                "source": "fallback",
            },
        )

    def test_generate_daily_summary_falls_back_for_malformed_json_fields(self):
        from summary.services import generate_daily_summary

        activity_logs = [
            {
                "app_name": "Terminal",
                "duration_seconds": 600,
            }
        ]
        malformed_summary = {
            "accomplishments": "not-a-list",
            "journal": ["not", "a", "string"],
            "productivity_score": "not-a-number",
        }

        with (
            patch(
                "summary.services.load_sessions_for_date",
                return_value=activity_logs,
            ) as mock_load_sessions,
            patch(
                "summary.services._generate_ollama_summary",
                return_value=malformed_summary,
            ) as mock_generate,
        ):
            summary = generate_daily_summary("2026-04-29", base_dir="/tmp/journalise")

        mock_load_sessions.assert_called_once_with("/tmp/journalise", "2026-04-29")
        mock_generate.assert_called_once_with(
            "2026-04-29",
            {
                "total_tracked_seconds": 600,
                "session_count": 1,
                "top_apps": [
                    {"app_name": "Terminal", "duration_seconds": 600},
                ],
                "productivity_score": 10,
            },
            activity_logs,
        )
        self.assertEqual(
            summary,
            {
                "date": "2026-04-29",
                "stats": {
                    "total_tracked_seconds": 600,
                    "session_count": 1,
                    "top_apps": [
                        {"app_name": "Terminal", "duration_seconds": 600},
                    ],
                    "productivity_score": 10,
                },
                "accomplishments": ["Tracked 1 activity session."],
                "journal": "Recorded 1 activity session across 10 minutes.",
                "productivity_score": 10,
                "source": "fallback",
            },
        )
