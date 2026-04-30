import json
import subprocess
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from journal.activity_store import load_sessions_for_date, save_sessions_for_date
from journal.app_category import resolve_app_category
from journal.privacy import sanitize_text
from journal.timezone_utils import LOCAL_TZ, parse_timestamp

JSON_INDENT = 2
DEFAULT_HOURLY_NOTE_MODEL = "qwen3:8b"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"


def build_hourly_summary_path(base_dir: str | Path, date_str: str) -> Path:
    return Path(base_dir) / "hourly_summaries" / f"{date_str}.json"


def build_vision_summary_path(base_dir: str | Path, date_str: str) -> Path:
    return Path(base_dir) / "vision_summaries" / f"{date_str}.json"


def _load_hourly_summary_list(path: Path) -> list[dict[str, object]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    if not isinstance(data, list):
        return []

    return [item for item in data if isinstance(item, dict)]


def _load_vision_summary_list(path: Path) -> list[dict[str, str]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    if not isinstance(data, list):
        return []

    summaries: list[dict[str, str]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        captured_at = item.get("captured_at")
        summary = item.get("summary")
        if isinstance(captured_at, str) and isinstance(summary, str):
            summaries.append(
                {
                    "captured_at": captured_at,
                    "summary": summary,
                }
            )

    return summaries


def _existing_notes_by_start_time(path: Path) -> dict[str, list[str]]:
    if not path.exists():
        return {}
    existing = _load_hourly_summary_list(path)
    notes_by_start_time: dict[str, list[str]] = {}
    for hour in existing:
        start_time = hour.get("start_time")
        notes = hour.get("notes")
        if not isinstance(start_time, str):
            continue
        if not isinstance(notes, list):
            continue
        normalized_notes = [note for note in notes if isinstance(note, str)]
        notes_by_start_time[start_time] = normalized_notes
    return notes_by_start_time


def _format_time_range(hour_start: datetime, hour_end: datetime) -> str:
    return f"{hour_start.strftime('%I:%M %p')} - {hour_end.strftime('%I:%M %p')}"


def _split_session_by_hour(session: dict[str, str]) -> list[tuple[datetime, datetime]]:
    started_at = parse_timestamp(session["started_at"]).astimezone(LOCAL_TZ)
    ended_at = parse_timestamp(session["ended_at"]).astimezone(LOCAL_TZ)
    if ended_at <= started_at:
        return []

    segments = []
    current_start = started_at
    while current_start < ended_at:
        hour_start = current_start.replace(minute=0, second=0, microsecond=0)
        next_hour = hour_start + timedelta(hours=1)
        current_end = min(ended_at, next_hour)
        segments.append((current_start, current_end))
        current_start = current_end

    return segments


def reclassify_sessions_for_date(base_dir: str | Path, date_str: str) -> list[dict[str, str]]:
    sessions = load_sessions_for_date(base_dir, date_str)
    updated_sessions: list[dict[str, str]] = []
    changed = False

    for session in sessions:
        updated_session = dict(session)
        category = resolve_app_category(base_dir, updated_session["title"])
        if updated_session.get("category") != category:
            updated_session["category"] = category
            changed = True
        updated_sessions.append(updated_session)

    if changed:
        save_sessions_for_date(base_dir, date_str, updated_sessions)

    return updated_sessions


def rebuild_hourly_summary_for_date(base_dir: str | Path, date_str: str) -> list[dict[str, object]]:
    sessions = reclassify_sessions_for_date(base_dir, date_str)
    path = build_hourly_summary_path(base_dir, date_str)
    notes_by_start_time = _existing_notes_by_start_time(path)

    buckets: dict[datetime, dict[str, dict[str, object]]] = defaultdict(dict)
    for session in sessions:
        for segment_start, segment_end in _split_session_by_hour(session):
            hour_start = segment_start.replace(minute=0, second=0, microsecond=0)
            category = session["category"]
            category_bucket = buckets[hour_start].setdefault(
                category,
                {
                    "category": category,
                    "category_display": category.capitalize(),
                    "total_seconds": 0.0,
                    "titles": [],
                    "activity_count": 0,
                },
            )

            duration_seconds = (segment_end - segment_start).total_seconds()
            category_bucket["total_seconds"] = float(category_bucket["total_seconds"]) + duration_seconds
            category_bucket["activity_count"] = int(category_bucket["activity_count"]) + 1

            titles = list(category_bucket["titles"])
            if session["title"] not in titles:
                titles.append(session["title"])
            category_bucket["titles"] = titles

    results: list[dict[str, object]] = []
    for hour_start in sorted(buckets):
        hour_end = hour_start + timedelta(hours=1)
        categories = []
        for category_name in sorted(buckets[hour_start]):
            bucket = buckets[hour_start][category_name]
            total_minutes = int(round(float(bucket["total_seconds"]) / 60))
            if total_minutes < 1:
                continue

            categories.append(
                {
                    "category": bucket["category"],
                    "category_display": bucket["category_display"],
                    "total_minutes": total_minutes,
                    "activity_count": bucket["activity_count"],
                    "titles": bucket["titles"],
                }
            )

        if not categories:
            continue

        results.append(
            {
                "time_range": _format_time_range(hour_start, hour_end),
                "start_time": hour_start.isoformat(),
                "end_time": hour_end.isoformat(),
                "notes": notes_by_start_time.get(hour_start.isoformat(), []),
                "categories": categories,
            }
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, indent=JSON_INDENT) + "\n", encoding="utf-8")
    return results


def collect_vision_summaries_for_hour(
    base_dir: str | Path,
    date_str: str,
    hour_start: datetime,
) -> list[str]:
    path = build_vision_summary_path(base_dir, date_str)
    if not path.exists():
        return []

    hour_end = hour_start + timedelta(hours=1)
    summaries = []
    for entry in _load_vision_summary_list(path):
        captured_at = parse_timestamp(entry["captured_at"]).astimezone(LOCAL_TZ)
        if hour_start <= captured_at < hour_end:
            summaries.append(entry["summary"])
    return summaries


def request_hourly_note(
    hour_summary: dict[str, object],
    vision_summaries: list[str],
) -> str:
    payload = json.dumps(
        {
            "model": DEFAULT_HOURLY_NOTE_MODEL,
            "stream": False,
            "format": "json",
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "You are writing one concise hourly note for a productivity journal. "
                        "Use the category breakdown and screenshot observations. "
                        'Return valid JSON only with exactly this key: {"note":"..."}. '
                        "Keep it to one short sentence."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "time_range": hour_summary["time_range"],
                            "categories": hour_summary["categories"],
                            "vision_summaries": vision_summaries,
                        }
                    ),
                },
            ],
        }
    )

    result = subprocess.run(
        [
            "curl",
            "-sS",
            f"{DEFAULT_OLLAMA_BASE_URL}/api/chat",
            "-H",
            "Content-Type: application/json",
            "-d",
            payload,
        ],
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )
    body = json.loads(result.stdout)
    message = body.get("message") or {}
    content = message.get("content", "")
    if not isinstance(content, str):
        raise ValueError("Hourly note response content was not a string.")

    note_body = json.loads(content)
    if not isinstance(note_body, dict):
        raise ValueError("Hourly note response must be a JSON object.")

    note = note_body.get("note")
    if not isinstance(note, str) or not note.strip():
        raise ValueError("Hourly note response must include a non-empty note.")

    return sanitize_text(note.strip())


def generate_and_persist_hourly_note(
    base_dir: str | Path,
    date_str: str,
    hour_start_iso: str,
) -> str | None:
    path = build_hourly_summary_path(base_dir, date_str)
    if not path.exists():
        return None

    hourly_summaries = _load_hourly_summary_list(path)
    target_hour = None
    for hour_summary in hourly_summaries:
        if hour_summary.get("start_time") == hour_start_iso:
            target_hour = hour_summary
            break

    if target_hour is None:
        return None

    hour_start = parse_timestamp(hour_start_iso).astimezone(LOCAL_TZ)
    vision_summaries = collect_vision_summaries_for_hour(base_dir, date_str, hour_start)
    note = sanitize_text(request_hourly_note(target_hour, vision_summaries))
    target_hour["notes"] = [note]
    path.write_text(json.dumps(hourly_summaries, indent=JSON_INDENT) + "\n", encoding="utf-8")
    return note


def generate_previous_hour_note_if_missing(
    base_dir: str | Path,
    reference_time: datetime,
) -> str | None:
    completed_hour_start = (
        reference_time.astimezone(LOCAL_TZ).replace(minute=0, second=0, microsecond=0)
        - timedelta(hours=1)
    )
    date_str = completed_hour_start.date().isoformat()
    path = build_hourly_summary_path(base_dir, date_str)
    if not path.exists():
        return None

    hourly_summaries = _load_hourly_summary_list(path)
    target_hour = None
    for hour_summary in hourly_summaries:
        if hour_summary.get("start_time") == completed_hour_start.isoformat():
            target_hour = hour_summary
            break

    if target_hour is None:
        return None

    existing_notes = target_hour.get("notes")
    if isinstance(existing_notes, list) and any(
        isinstance(note, str) and note.strip() for note in existing_notes
    ):
        return None

    return generate_and_persist_hourly_note(
        base_dir,
        date_str,
        completed_hour_start.isoformat(),
    )
