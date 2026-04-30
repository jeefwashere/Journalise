import threading
from dataclasses import dataclass

from journal.management.commands.collect_activity import (
    DEFAULT_ACTIVITY_INTERVAL,
    DEFAULT_SCREENSHOT_INTERVAL,
    run_collector,
    start_minute_summary_worker,
    start_screenshot_worker,
    stop_minute_summary_worker,
    stop_screenshot_worker,
)
from journal.overall_summary import generate_and_persist_overall_summary


@dataclass
class ActivityTrackingHandle:
    stop_event: threading.Event
    worker: threading.Thread

    def stop(self, timeout: float = 2.0) -> None:
        self.stop_event.set()
        self.worker.join(timeout=timeout)


@dataclass
class ScreenshotCaptureHandle:
    screenshot_stop_event: threading.Event
    screenshot_worker: threading.Thread
    summary_stop_event: threading.Event | None = None
    summary_worker: threading.Thread | None = None

    def stop(self) -> None:
        if self.summary_stop_event is not None and self.summary_worker is not None:
            stop_minute_summary_worker(self.summary_stop_event, self.summary_worker)
        stop_screenshot_worker(self.screenshot_stop_event, self.screenshot_worker)


def start_activity_tracking(
    base_dir: str = "activity_data",
    interval: float = DEFAULT_ACTIVITY_INTERVAL,
) -> ActivityTrackingHandle:
    stop_event = threading.Event()
    worker = threading.Thread(
        target=run_collector,
        kwargs={
            "base_dir": base_dir,
            "interval": interval,
            "once": False,
            "screenshots": False,
            "vision_summary": False,
            "stop_event": stop_event,
        },
        daemon=True,
    )
    worker.start()
    return ActivityTrackingHandle(stop_event=stop_event, worker=worker)


def start_screenshot_capture(
    base_dir: str = "activity_data",
    screenshot_interval: float = DEFAULT_SCREENSHOT_INTERVAL,
    vision_summary: bool = False,
) -> ScreenshotCaptureHandle:
    screenshot_stop_event, screenshot_worker = start_screenshot_worker(
        base_dir,
        screenshot_interval,
    )

    if not vision_summary:
        return ScreenshotCaptureHandle(
            screenshot_stop_event=screenshot_stop_event,
            screenshot_worker=screenshot_worker,
        )

    summary_stop_event, summary_worker = start_minute_summary_worker(
        base_dir,
        screenshot_interval,
    )
    return ScreenshotCaptureHandle(
        screenshot_stop_event=screenshot_stop_event,
        screenshot_worker=screenshot_worker,
        summary_stop_event=summary_stop_event,
        summary_worker=summary_worker,
    )


def generate_daily_overall_summary(
    date_str: str,
    base_dir: str = "activity_data",
    env_path: str = ".env",
) -> dict[str, object]:
    return generate_and_persist_overall_summary(
        base_dir=base_dir,
        date_str=date_str,
        env_path=env_path,
    )
