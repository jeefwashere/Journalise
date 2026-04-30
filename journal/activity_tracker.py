from datetime import datetime

from journal.activity_types import ActivitySession
from journal.timezone_utils import format_timestamp


def _require_aware_datetime(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")


class ActivityTracker:
    def __init__(self):
        self._active_session: dict[str, str | datetime] | None = None

    def start_session(self, title: str, started_at: datetime) -> None:
        _require_aware_datetime(started_at)
        self._active_session = {
            "title": title,
            "started_at": started_at,
        }

    def switch_session(self, title: str, started_at: datetime) -> ActivitySession | None:
        _require_aware_datetime(started_at)
        if self._active_session is None:
            self.start_session(title, started_at)
            return None

        if str(self._active_session["title"]) == title:
            return None

        completed_session = self.finish_active_session(started_at)
        self.start_session(title, started_at)
        return completed_session

    def finish_active_session(self, ended_at: datetime) -> ActivitySession | None:
        _require_aware_datetime(ended_at)
        if self._active_session is None:
            return None

        active_session = self._active_session
        started_at = active_session["started_at"]
        completed_session = ActivitySession(
            title=str(active_session["title"]),
            category="work",
            description="",
            started_at=format_timestamp(started_at),
            ended_at=format_timestamp(ended_at),
            created_at=format_timestamp(ended_at),
        )
        self._active_session = None
        return completed_session
