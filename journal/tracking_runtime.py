from dataclasses import dataclass

from django.conf import settings
from django.utils import timezone

from journal.activity_ingest import persist_session
from journal.activity_tracker import ActivityTracker
from summary.services import generate_daily_summary


LOCAL_TRACKER_APP_NAME = "Journalise local tracker"
LOCAL_TRACKER_BUNDLE_ID = "journalise.local.tracker"


@dataclass
class TrackingState:
    tracker: ActivityTracker
    started_at: object


_ACTIVE_TRACKERS: dict[int, TrackingState] = {}


def start_tracking(user) -> dict:
    user_key = int(user.pk)
    if user_key in _ACTIVE_TRACKERS:
        state = _ACTIVE_TRACKERS[user_key]
        return {
            "tracking": True,
            "started_at": state.started_at.isoformat(),
            "already_active": True,
        }

    started_at = timezone.now()
    tracker = ActivityTracker()
    tracker.start_session(
        LOCAL_TRACKER_APP_NAME,
        LOCAL_TRACKER_BUNDLE_ID,
        started_at,
    )
    _ACTIVE_TRACKERS[user_key] = TrackingState(
        tracker=tracker,
        started_at=started_at,
    )

    return {
        "tracking": True,
        "started_at": started_at.isoformat(),
        "already_active": False,
    }


def stop_tracking(user) -> dict:
    user_key = int(user.pk)
    state = _ACTIVE_TRACKERS.pop(user_key, None)

    if state is None:
        return {
            "tracking": False,
            "activity": None,
            "summary": None,
            "already_inactive": True,
        }

    finished_session = state.tracker.finish_active_session(timezone.now())
    activity = None
    created = False
    daily_summary = None

    if finished_session is not None:
        activity, created = persist_session(user, finished_session)
        daily_summary = generate_daily_summary(
            timezone.localdate(activity.started_at).isoformat(),
            base_dir=settings.BASE_DIR / "data",
        )

    return {
        "tracking": False,
        "activity": activity,
        "activity_created": created,
        "summary": daily_summary,
        "already_inactive": False,
    }
