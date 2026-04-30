import threading
from dataclasses import dataclass

from django.conf import settings
from django.db import close_old_connections
from django.utils import timezone

from journal.active_window import get_active_window
from journal.activity_ingest import create_activity_from_window_for_user_id
from summary.services import generate_daily_summary


TRACKING_INTERVAL_SECONDS = 5.0


@dataclass
class TrackingState:
    stop_event: threading.Event
    worker: threading.Thread
    started_at: object


_ACTIVE_TRACKERS: dict[int, TrackingState] = {}
_TRACKERS_LOCK = threading.Lock()


def get_tracking_status(user) -> dict:
    user_key = int(user.pk)
    with _TRACKERS_LOCK:
        state = _ACTIVE_TRACKERS.get(user_key)

    if state is None or not state.worker.is_alive():
        return {
            "tracking": False,
            "started_at": None,
            "interval_seconds": TRACKING_INTERVAL_SECONDS,
        }

    return {
        "tracking": True,
        "started_at": state.started_at.isoformat(),
        "interval_seconds": TRACKING_INTERVAL_SECONDS,
    }


def _tracking_loop(user_id: int, interval: float, stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        started_at = timezone.now()
        try:
            active_window = get_active_window()
            if stop_event.wait(interval):
                ended_at = timezone.now()
            else:
                ended_at = timezone.now()

            close_old_connections()
            create_activity_from_window_for_user_id(
                user_id,
                active_window.app_name,
                active_window.window_title,
                started_at,
                ended_at,
            )
        except Exception as exc:
            print(f"Error tracking active window: {exc}")
            if stop_event.wait(interval):
                break
        finally:
            close_old_connections()


def start_tracking(user, interval: float = TRACKING_INTERVAL_SECONDS) -> dict:
    user_key = int(user.pk)
    with _TRACKERS_LOCK:
        existing = _ACTIVE_TRACKERS.get(user_key)
        if existing is not None and existing.worker.is_alive():
            return {
                "tracking": True,
                "started_at": existing.started_at.isoformat(),
                "already_active": True,
                "interval_seconds": interval,
            }

        stop_event = threading.Event()
        started_at = timezone.now()
        worker = threading.Thread(
            target=_tracking_loop,
            args=(user_key, interval, stop_event),
            daemon=True,
        )
        _ACTIVE_TRACKERS[user_key] = TrackingState(
            stop_event=stop_event,
            worker=worker,
            started_at=started_at,
        )
        worker.start()

    return {
        "tracking": True,
        "started_at": started_at.isoformat(),
        "already_active": False,
        "interval_seconds": interval,
    }


def stop_tracking(user) -> dict:
    user_key = int(user.pk)
    with _TRACKERS_LOCK:
        state = _ACTIVE_TRACKERS.pop(user_key, None)

    if state is None:
        return {
            "tracking": False,
            "activity": None,
            "summary": None,
            "already_inactive": True,
        }

    state.stop_event.set()
    state.worker.join(timeout=TRACKING_INTERVAL_SECONDS + 2.0)

    summary = None
    try:
        summary = generate_daily_summary(
            timezone.localdate(timezone.now()).isoformat(),
            base_dir=settings.BASE_DIR / "data",
        )
    except Exception as exc:
        print(f"Error generating tracking summary: {exc}")

    return {
        "tracking": False,
        "activity": None,
        "summary": summary,
        "already_inactive": False,
    }
