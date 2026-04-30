import json
from pathlib import Path

from journal.activity_types import ActivitySession

REQUIRED_SESSION_KEYS = {
    "title",
    "category",
    "description",
    "started_at",
    "ended_at",
    "created_at",
}
JSON_INDENT = 2


def _day_path(base_dir: str | Path, date_str: str) -> Path:
    return Path(base_dir) / "activity_logs" / f"{date_str}.json"


def _load_session_list(path: Path) -> list[dict[str, str]]:
    try:
        sessions = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    if not isinstance(sessions, list):
        return []

    for session in sessions:
        if not isinstance(session, dict):
            return []
        if not REQUIRED_SESSION_KEYS.issubset(session):
            return []

    return sessions


def append_session(base_dir: str | Path, date_str: str, session: ActivitySession) -> None:
    path = _day_path(base_dir, date_str)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        sessions = _load_session_list(path)
    else:
        sessions = []

    sessions.append(session.to_dict())
    save_sessions_for_date(base_dir, date_str, sessions)


def save_sessions_for_date(
    base_dir: str | Path,
    date_str: str,
    sessions: list[dict[str, str]],
) -> None:
    path = _day_path(base_dir, date_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(sessions, indent=JSON_INDENT) + "\n",
        encoding="utf-8",
    )


def load_sessions_for_date(base_dir: str | Path, date_str: str) -> list[dict[str, str]]:
    path = _day_path(base_dir, date_str)
    if not path.exists():
        return []

    return _load_session_list(path)
