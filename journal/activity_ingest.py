from datetime import datetime, timezone as datetime_timezone
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils.dateparse import parse_datetime

from journal.activity_store import append_session, load_sessions_for_date
from journal.activity_types import ActivitySession
from journal.models import Activity


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


def _parse_timestamp(value: str) -> datetime:
    parsed = parse_datetime(value)
    if parsed is None:
        raise ValueError(f"Invalid timestamp: {value}")

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return parsed.replace(tzinfo=datetime_timezone.utc)

    return parsed


def _session_from_dict(data: dict) -> ActivitySession:
    return ActivitySession(
        app_name=str(data["app_name"]),
        bundle_id=str(data.get("bundle_id", "")),
        started_at=str(data["started_at"]),
        ended_at=str(data["ended_at"]),
        duration_seconds=int(data.get("duration_seconds", 0)),
    )


def infer_category(app_name: str, bundle_id: str = "") -> str:
    haystack = f"{app_name} {bundle_id}".lower()

    for category, keywords in APP_CATEGORY_KEYWORDS.items():
        if any(keyword in haystack for keyword in keywords):
            return category

    return Activity.Category.OTHER


def activity_defaults_from_session(session: ActivitySession) -> dict:
    category = infer_category(session.app_name, session.bundle_id)
    duration_minutes = max(session.duration_seconds, 0) // 60
    description_parts = [
        "Tracked by local activity tracker.",
        f"Bundle ID: {session.bundle_id or 'unknown'}.",
        f"Duration: {duration_minutes} minutes.",
    ]

    return {
        "title": session.app_name or "Tracked activity",
        "category": category,
        "description": " ".join(description_parts),
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
