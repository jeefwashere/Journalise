from django.test import SimpleTestCase


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
