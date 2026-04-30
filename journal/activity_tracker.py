from datetime import datetime, timezone

from journal.activity_types import ActivitySession


def _format_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _require_aware_datetime(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")


class ActivityTracker:
    def __init__(self):
        self._active_session: dict[str, str | datetime] | None = None

    def start_session(self, app_name: str, bundle_id: str, started_at: datetime) -> None:
        _require_aware_datetime(started_at)
        self._active_session = {
            "app_name": app_name,
            "bundle_id": bundle_id,
            "started_at": started_at,
        }

    def switch_session(
        self,
        app_name: str,
        bundle_id: str,
        started_at: datetime,
    ) -> ActivitySession | None:
        _require_aware_datetime(started_at)
        completed_session = self.finish_active_session(started_at)
        self.start_session(app_name, bundle_id, started_at)
        return completed_session

    def finish_active_session(self, ended_at: datetime) -> ActivitySession | None:
        _require_aware_datetime(ended_at)
        if self._active_session is None:
            return None

        active_session = self._active_session
        started_at = active_session["started_at"]
        completed_session = ActivitySession(
            app_name=str(active_session["app_name"]),
            bundle_id=str(active_session["bundle_id"]),
            started_at=_format_timestamp(started_at),
            ended_at=_format_timestamp(ended_at),
            duration_seconds=max(int((ended_at - started_at).total_seconds()), 0),
        )
        self._active_session = None
        return completed_session
