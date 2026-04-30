import json
import subprocess
from datetime import datetime, timezone as datetime_timezone
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils.dateparse import parse_datetime

from journal.activity_store import append_session, load_sessions_for_date
from journal.activity_types import ActivitySession
from journal.models import Activity
from journal.privacy import sanitize_text


DEFAULT_ACTIVITY_MODEL = "qwen3:8b"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
APP_CATEGORY_KEYWORDS = {
    Activity.Category.WORK: (
        "code",
        "github",
        "terminal",
        "visual studio",
        "vscode",
        "pycharm",
        "slack",
        "notion",
    ),
    Activity.Category.STUDY: (
        "anki",
        "canvas",
        "coursera",
        "docs",
        "kindle",
        "obsidian",
        "pdf",
        "school",
    ),
    Activity.Category.ENTERTAINMENT: (
        "netflix",
        "spotify",
        "steam",
        "tiktok",
        "twitch",
        "youtube",
    ),
    Activity.Category.COMMUNICATION: (
        "discord",
        "gmail",
        "mail",
        "messages",
        "teams",
        "telegram",
        "whatsapp",
        "zoom",
    ),
}
MODEL_CATEGORY_ALIASES = {
    "relax": Activity.Category.ENTERTAINMENT,
    "leisure": Activity.Category.ENTERTAINMENT,
}


def _parse_timestamp(value: str) -> datetime:
    parsed = parse_datetime(value)
    if parsed is None:
        raise ValueError(f"Invalid timestamp: {value}")

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return parsed.replace(tzinfo=datetime_timezone.utc)

    return parsed


def _session_from_dict(data: dict) -> ActivitySession:
    return ActivitySession(
        title=str(data.get("title") or data.get("app_name") or "Tracked activity"),
        category=str(data.get("category") or Activity.Category.OTHER),
        description=str(data.get("description") or ""),
        started_at=str(data["started_at"]),
        ended_at=str(data["ended_at"]),
        created_at=str(data.get("created_at") or data["ended_at"]),
    )


def normalize_category(value: str) -> str:
    normalized = value.strip().lower()
    normalized = MODEL_CATEGORY_ALIASES.get(normalized, normalized)
    allowed = {choice for choice, _label in Activity.Category.choices}
    if normalized in allowed:
        return normalized
    return Activity.Category.OTHER


def infer_category(title: str, description: str = "") -> str:
    haystack = f"{title} {description}".lower()

    for category, keywords in APP_CATEGORY_KEYWORDS.items():
        if any(keyword in haystack for keyword in keywords):
            return category

    return Activity.Category.OTHER


def activity_defaults_from_session(session: ActivitySession) -> dict:
    category = normalize_category(session.category)
    if category == Activity.Category.OTHER:
        category = infer_category(session.title, session.description)

    return {
        "title": session.title or "Tracked activity",
        "category": category,
        "description": session.description or "Tracked by local activity tracker.",
    }


def request_activity_fields_from_model(
    app_name: str,
    window_title: str,
    *,
    model: str = DEFAULT_ACTIVITY_MODEL,
) -> dict[str, str]:
    prompt = (
        "Create one Activity object summary from active desktop window metadata. "
        "Return valid JSON only with exactly these string keys: "
        '{"title":"...","category":"...","description":"..."}. '
        "Category must be one of: work, study, entertainment, communication, other. "
        "Title should be concise and useful for a journal activity list. "
        "Description should be one short sentence and avoid secrets, message bodies, "
        "account details, or long identifiers.\n"
        f"App name: {app_name}\n"
        f"Window title: {window_title or 'unknown'}"
    )
    payload = json.dumps(
        {
            "model": model,
            "stream": False,
            "format": "json",
            "messages": [{"role": "user", "content": prompt}],
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
        timeout=60,
        check=True,
    )
    body = json.loads(result.stdout)
    message = body.get("message") or {}
    content = message.get("content", "")
    if not isinstance(content, str):
        raise ValueError("activity model response content was not a string")

    fields = json.loads(content)
    if not isinstance(fields, dict):
        raise ValueError("activity model response must be a JSON object")

    title = fields.get("title")
    category = fields.get("category")
    description = fields.get("description")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("activity model response must include a title")
    if not isinstance(category, str):
        raise ValueError("activity model response must include a category")
    if not isinstance(description, str):
        raise ValueError("activity model response must include a description")

    return {
        "title": sanitize_text(title.strip())[:255],
        "category": normalize_category(category),
        "description": sanitize_text(description.strip()),
    }


def fallback_activity_fields(app_name: str, window_title: str) -> dict[str, str]:
    title = f"{app_name} - {window_title}" if window_title else app_name
    return {
        "title": sanitize_text(title or "Tracked activity")[:255],
        "category": infer_category(app_name, window_title),
        "description": sanitize_text(
            f"Tracked active window from {app_name or 'an unknown app'}."
        ),
    }


@lru_cache(maxsize=256)
def _cached_activity_fields_for_window(app_name: str, window_title: str) -> tuple[str, str, str]:
    try:
        fields = request_activity_fields_from_model(app_name, window_title)
    except Exception:
        fields = fallback_activity_fields(app_name, window_title)
    return fields["title"], fields["category"], fields["description"]


def activity_fields_for_window(app_name: str, window_title: str) -> dict[str, str]:
    title, category, description = _cached_activity_fields_for_window(
        app_name,
        window_title,
    )
    return {
        "title": title,
        "category": category,
        "description": description,
    }


@transaction.atomic
def persist_session(
    user,
    session: ActivitySession,
    *,
    base_dir: str | Path | None = None,
    write_log: bool = True,
) -> tuple[Activity, bool]:
    started_at = _parse_timestamp(session.started_at)
    ended_at = _parse_timestamp(session.ended_at)
    defaults = activity_defaults_from_session(session)

    activity, created = Activity.objects.get_or_create(
        user=user,
        title=defaults["title"],
        started_at=started_at,
        ended_at=ended_at,
        defaults={
            "category": defaults["category"],
            "description": defaults["description"],
        },
    )

    if not created:
        changed_fields = []
        for field in ("category", "description"):
            if getattr(activity, field) != defaults[field]:
                setattr(activity, field, defaults[field])
                changed_fields.append(field)

        if changed_fields:
            activity.save(update_fields=changed_fields)

    if write_log and created:
        if base_dir is None:
            base_dir = settings.BASE_DIR / "data"
        append_session(base_dir, started_at.date().isoformat(), session)

    return activity, created


@transaction.atomic
def create_activity_from_window(
    user,
    app_name: str,
    window_title: str,
    started_at: datetime,
    ended_at: datetime,
) -> Activity:
    fields = activity_fields_for_window(app_name, window_title)
    return Activity.objects.create(
        user=user,
        title=fields["title"],
        category=fields["category"],
        description=fields["description"],
        started_at=started_at,
        ended_at=ended_at,
    )


@transaction.atomic
def create_activity_from_window_for_user_id(
    user_id: int,
    app_name: str,
    window_title: str,
    started_at: datetime,
    ended_at: datetime,
) -> Activity:
    fields = activity_fields_for_window(app_name, window_title)
    return Activity.objects.create(
        user_id=user_id,
        title=fields["title"],
        category=fields["category"],
        description=fields["description"],
        started_at=started_at,
        ended_at=ended_at,
    )


def persist_sessions(
    user,
    sessions: list[ActivitySession | dict],
    *,
    base_dir: str | Path | None = None,
    write_log: bool = True,
) -> dict:
    activities = []
    created_count = 0

    for item in sessions:
        session = item if isinstance(item, ActivitySession) else _session_from_dict(item)
        activity, created = persist_session(
            user,
            session,
            base_dir=base_dir,
            write_log=write_log,
        )
        activities.append(activity)
        if created:
            created_count += 1

    return {
        "activities": activities,
        "created_count": created_count,
        "updated_count": len(activities) - created_count,
    }


def persist_sessions_for_date(
    user,
    date_str: str,
    *,
    base_dir: str | Path | None = None,
) -> dict:
    if base_dir is None:
        base_dir = settings.BASE_DIR / "data"

    sessions = load_sessions_for_date(base_dir, date_str)
    return persist_sessions(user, sessions, base_dir=base_dir, write_log=False)
