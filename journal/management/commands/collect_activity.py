import base64
import json
import multiprocessing
import subprocess
import tempfile
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

from django.core.management.base import BaseCommand

from journal.app_category import resolve_app_category
from journal.activity_store import append_session
from journal.activity_tracker import ActivityTracker
from journal.activity_types import ActivitySession
from journal.hourly_summary import (
    generate_previous_hour_note_if_missing,
    rebuild_hourly_summary_for_date,
)
from journal.privacy import sanitize_text
from journal.timezone_utils import LOCAL_TZ, format_timestamp, local_date_str, parse_timestamp

DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_VISION_MODEL = "qwen2.5vl:7b"
DEFAULT_ACTIVITY_INTERVAL = 10.0
DEFAULT_SCREENSHOT_INTERVAL = 300.0
DEFAULT_VISION_IMAGE_MAX_DIMENSION = 768
JSON_INDENT = 2


def build_screenshot_path(base_dir: str, captured_at: datetime) -> Path:
    local_captured_at = captured_at.astimezone(LOCAL_TZ)
    day_dir = Path(base_dir) / "screenshots" / local_captured_at.date().isoformat()
    filename = local_captured_at.strftime("%H-%M-%S.png")
    return day_dir / filename


def capture_screenshot(base_dir: str, captured_at: datetime) -> Path:
    screenshot_path = build_screenshot_path(base_dir, captured_at)
    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["screencapture", "-x", str(screenshot_path)],
        timeout=10,
        check=True,
    )
    return screenshot_path


def prepare_image_for_vision(source_path: Path) -> Path:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as resized_file:
        resized_path = Path(resized_file.name)

    subprocess.run(
        [
            "sips",
            "-Z",
            str(DEFAULT_VISION_IMAGE_MAX_DIMENSION),
            str(source_path),
            "--out",
            str(resized_path),
        ],
        timeout=20,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return resized_path


def build_vision_summary_path(base_dir: str, date_str: str) -> Path:
    return Path(base_dir) / "vision_summaries" / f"{date_str}.json"


def _load_vision_summary_list(path: Path) -> list[dict[str, str]]:
    try:
        summaries = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    if not isinstance(summaries, list):
        return []

    for summary in summaries:
        if not isinstance(summary, dict):
            return []
        if not {"captured_at", "summary"}.issubset(summary):
            return []

    return summaries


def append_vision_summary(
    base_dir: str,
    captured_at: datetime,
    screenshot_summary: str,
) -> None:
    sanitized_summary = sanitize_text(screenshot_summary)
    local_captured_at = captured_at.astimezone(LOCAL_TZ)
    date_str = local_captured_at.date().isoformat()
    path = build_vision_summary_path(base_dir, date_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        summaries = _load_vision_summary_list(path)
    else:
        summaries = []

    summaries.append(
        {
            "captured_at": local_captured_at.isoformat(),
            "summary": sanitized_summary,
        }
    )

    path.write_text(
        json.dumps(summaries, indent=JSON_INDENT) + "\n",
        encoding="utf-8",
    )


def list_recent_screenshots(
    base_dir: str,
    reference_time: datetime,
    limit: int = 12,
) -> list[Path]:
    screenshot_dir = (
        Path(base_dir)
        / "screenshots"
        / reference_time.astimezone(LOCAL_TZ).date().isoformat()
    )
    if not screenshot_dir.exists():
        return []

    return sorted(screenshot_dir.glob("*.png"))[-limit:]


def _timestamp_from_screenshot_path(path: Path) -> datetime:
    local_time = datetime.strptime(
        f"{path.parent.name} {path.stem}",
        "%Y-%m-%d %H-%M-%S",
    ).replace(tzinfo=LOCAL_TZ)
    return local_time


def request_vision_summary(
    screenshot_paths: list[Path],
) -> str:
    prepared_image_paths = [prepare_image_for_vision(path) for path in screenshot_paths]
    images = [
        base64.b64encode(path.read_bytes()).decode("utf-8")
        for path in prepared_image_paths
    ]
    payload = json.dumps(
        {
            "model": DEFAULT_VISION_MODEL,
            "format": "json",
            "stream": True,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Tell me the fun or interesting things happening in this screenshot. "
                        'Return valid JSON only with exactly this key: {"summary":"..."}. '
                        "Keep the summary short and concrete."
                    ),
                    "images": images,
                }
            ],
        }
    )

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as payload_file:
        payload_file.write(payload)
        payload_path = payload_file.name

    curl_command = [
        "curl",
        "-sS",
        "-N",
        "-X",
        "POST",
        f"{DEFAULT_OLLAMA_BASE_URL}/api/chat",
        "-H",
        "Content-Type: application/json",
        "--data-binary",
        f"@{payload_path}",
    ]

    try:
        response_parts = []
        with subprocess.Popen(
            curl_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ) as process:
            if process.stdout is not None:
                for line in process.stdout:
                    if not line:
                        continue
                    chunk = json.loads(line)
                    message = chunk.get("message") or {}
                    response_text = message.get("content", "")
                    if response_text:
                        print(response_text, end="", flush=True)
                    response_parts.append(response_text)

            return_code = process.wait(timeout=300)
            stderr_text = process.stderr.read() if process.stderr is not None else ""

        if return_code != 0:
            raise RuntimeError(f"curl Ollama request failed: {stderr_text.strip()}")
    finally:
        Path(payload_path).unlink(missing_ok=True)
        for prepared_image_path in prepared_image_paths:
            prepared_image_path.unlink(missing_ok=True)

    response_text = "".join(response_parts)
    if response_text:
        print()
    if not response_text:
        raise ValueError("Ollama response did not include summary content.")

    summary = json.loads(response_text)
    if not isinstance(summary, dict):
        raise ValueError("Ollama vision summary must be a JSON object.")

    summary_text = summary.get("summary")
    if not isinstance(summary_text, str):
        raise ValueError("Ollama vision summary must include a string summary.")

    return summary_text


def generate_minute_summary(
    base_dir: str,
    reference_time: datetime,
) -> tuple[datetime, str] | None:
    screenshot_paths = list_recent_screenshots(base_dir, reference_time, limit=1)
    if len(screenshot_paths) < 1:
        return None

    screenshot_time = _timestamp_from_screenshot_path(screenshot_paths[-1])
    summary = request_vision_summary(screenshot_paths)
    return screenshot_time, summary


def generate_and_persist_minute_summary(
    base_dir: str,
    reference_time_iso: str,
) -> None:
    reference_time = datetime.fromisoformat(reference_time_iso)
    print(f"Starting minute summary for {reference_time_iso}")
    try:
        summary = generate_minute_summary(base_dir, reference_time)
        if summary is not None:
            screenshot_time, summary_text = summary
            append_vision_summary(base_dir, screenshot_time, summary_text)
            print(f"Saved vision summary for {screenshot_time.isoformat()}")
            hourly_note = generate_previous_hour_note_if_missing(base_dir, screenshot_time)
            if hourly_note is not None:
                print(f"Saved hourly note for {(screenshot_time.astimezone(LOCAL_TZ).replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)).isoformat()}")
        else:
            print(f"No screenshots available for minute summary at {reference_time_iso}")
    except Exception as exc:
        print(f"Error generating minute summary: {exc}")


def start_minute_summary_process(
    base_dir: str,
    reference_time: datetime,
) -> multiprocessing.Process:
    process = multiprocessing.Process(
        target=generate_and_persist_minute_summary,
        args=(base_dir, reference_time.isoformat()),
        daemon=False,
    )
    process.start()
    print(f"Dispatched minute summary for {reference_time.isoformat()}")
    return process


def run_screenshot_loop(
    base_dir: str,
    screenshot_interval: float,
    stop_event: threading.Event,
) -> None:
    while not stop_event.is_set():
        captured_at = datetime.now(LOCAL_TZ)
        try:
            capture_screenshot(base_dir, captured_at)
        except Exception as exc:
            print(f"Error capturing screenshot: {exc}")

        if stop_event.wait(screenshot_interval):
            break


def run_minute_summary_loop(
    base_dir: str,
    stop_event: threading.Event,
    summary_interval: float = DEFAULT_SCREENSHOT_INTERVAL,
) -> None:
    active_process = None

    while not stop_event.is_set():
        if active_process is not None and not active_process.is_alive():
            active_process.join()
            active_process = None

        if active_process is None:
            reference_time = datetime.now(LOCAL_TZ)
            active_process = start_minute_summary_process(
                base_dir,
                reference_time,
            )
        else:
            print("Minute summary still running; skipping new request.")

        if stop_event.wait(summary_interval):
            break

    if active_process is not None and not active_process.is_alive():
        active_process.join()


def start_screenshot_worker(
    base_dir: str,
    screenshot_interval: float,
) -> tuple[threading.Event, threading.Thread]:
    stop_event = threading.Event()
    worker = threading.Thread(
        target=run_screenshot_loop,
        args=(base_dir, screenshot_interval, stop_event),
        daemon=True,
    )
    worker.start()
    return stop_event, worker


def start_minute_summary_worker(
    base_dir: str,
    summary_interval: float = DEFAULT_SCREENSHOT_INTERVAL,
) -> tuple[threading.Event, threading.Thread]:
    stop_event = threading.Event()
    worker = threading.Thread(
        target=run_minute_summary_loop,
        args=(base_dir, stop_event, summary_interval),
        daemon=True,
    )
    worker.start()
    return stop_event, worker


def stop_screenshot_worker(
    stop_event: threading.Event,
    worker: threading.Thread,
) -> None:
    stop_event.set()
    worker.join(timeout=1)


def stop_minute_summary_worker(
    stop_event: threading.Event,
    worker: threading.Thread,
) -> None:
    stop_event.set()
    worker.join(timeout=1)


def persist_finished_session(
    base_dir: str,
    ended_at: datetime | str,
    session: ActivitySession,
) -> None:
    date_str = local_date_str(ended_at)
    session.started_at = format_timestamp(parse_timestamp(session.started_at))
    session.ended_at = format_timestamp(parse_timestamp(session.ended_at))
    session.created_at = format_timestamp(parse_timestamp(session.created_at))

    session.category = resolve_app_category(base_dir, session.title)
    append_session(base_dir, date_str, session)
    rebuild_hourly_summary_for_date(base_dir, date_str)


def _finalize_active_session(
    tracker: ActivityTracker,
    base_dir: str,
    ended_at: datetime,
) -> None:
    finished = tracker.finish_active_session(ended_at=ended_at)

    if finished is not None:
        persist_finished_session(base_dir, finished.ended_at, finished)
        print(f"Saved session {finished.title}")

def get_frontmost_app() -> str:
    script = '''
    tell application "System Events"
        set frontApp to first application process whose frontmost is true
        set appName to name of frontApp
        return appName
    end tell
    '''

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("frontmost app read timed out") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("frontmost app read failed") from exc

    app_name = result.stdout.strip()

    if not app_name:
        raise RuntimeError("frontmost app name was empty")

    return app_name

def run_collector(
    base_dir: str = "activity_data",
    interval: float = DEFAULT_ACTIVITY_INTERVAL,
    once: bool = False,
    screenshots: bool = False,
    screenshot_interval: float = DEFAULT_SCREENSHOT_INTERVAL,
    vision_summary: bool = False,
    stop_event: threading.Event | None = None,
) -> None:
    tracker = ActivityTracker()
    screenshot_stop_event = None
    screenshot_worker = None
    minute_summary_stop_event = None
    minute_summary_worker = None
    should_print_stopped = False

    if screenshots:
        screenshot_stop_event, screenshot_worker = start_screenshot_worker(
            base_dir,
            screenshot_interval,
        )
        if vision_summary:
            minute_summary_stop_event, minute_summary_worker = start_minute_summary_worker(
                base_dir,
                screenshot_interval,
            )

    try:
        while True:
            if stop_event is not None and stop_event.is_set():
                should_print_stopped = True
                break

            now = datetime.now(LOCAL_TZ)
            try:
                title = get_frontmost_app()
            except Exception as exc:
                print(f"Error reading frontmost app: {exc}")
                if once:
                    break
                time.sleep(interval)
                continue

            finished = tracker.switch_session(title, now)

            if finished is not None:
                persist_finished_session(base_dir, finished.ended_at, finished)
                print(f"Saved session {finished.title}")

            print(f"Tracking {title}")

            if once:
                _finalize_active_session(tracker, base_dir, now)
                break

            if stop_event is not None:
                if stop_event.wait(interval):
                    should_print_stopped = True
                    break
            else:
                time.sleep(interval)

    except KeyboardInterrupt:
        should_print_stopped = True
    finally:
        if not once:
            _finalize_active_session(tracker, base_dir, datetime.now(LOCAL_TZ))

        if should_print_stopped:
            print("Collector stopped.")

        if minute_summary_stop_event is not None and minute_summary_worker is not None:
            stop_minute_summary_worker(minute_summary_stop_event, minute_summary_worker)
        if screenshot_stop_event is not None and screenshot_worker is not None:
            stop_screenshot_worker(screenshot_stop_event, screenshot_worker)


class Command(BaseCommand):
    help = "Collect frontmost macOS app activity and write daily JSON logs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-dir",
            default="activity_data",
            help="Directory where daily activity JSON files are stored.",
        )
        parser.add_argument(
            "--interval",
            type=float,
            default=DEFAULT_ACTIVITY_INTERVAL,
            help="Polling interval in seconds.",
        )
        parser.add_argument(
            "--once",
            action="store_true",
            help="Read the frontmost app once and exit.",
        )
        parser.add_argument(
            "--screenshots",
            action="store_true",
            help="Capture screenshots in the background while recording runs.",
        )
        parser.add_argument(
            "--screenshot-interval",
            type=float,
            default=DEFAULT_SCREENSHOT_INTERVAL,
            help="Screenshot interval in seconds.",
        )
        parser.add_argument(
            "--vision-summary",
            action="store_true",
            help="Summarize the latest screenshots every minute with a local Ollama vision model.",
        )

    def handle(self, *args, **options):
        run_collector(
            base_dir=options["base_dir"],
            interval=options["interval"],
            once=options["once"],
            screenshots=options["screenshots"],
            screenshot_interval=options["screenshot_interval"],
            vision_summary=options["vision_summary"],
        )
