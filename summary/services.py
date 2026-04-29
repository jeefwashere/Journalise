import json
import os
from urllib import error, request

from django.conf import settings
from journal.activity_store import load_sessions_for_date
from summary.stats import calculate_stats


DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "qwen3:8b"


def build_fallback_summary(date_str, stats, activity_logs):
    session_count = stats.get("session_count", 0)
    total_minutes = int(stats.get("total_tracked_seconds", 0) / 60)
    session_label = "session" if session_count == 1 else "sessions"

    return {
        "date": date_str,
        "stats": stats,
        "accomplishments": [f"Tracked {session_count} activity {session_label}."],
        "journal": (
            f"Recorded {session_count} activity {session_label} across "
            f"{total_minutes} minutes."
        ),
        "productivity_score": stats.get("productivity_score", 0),
        "source": "fallback",
    }


def generate_daily_summary(date_str, base_dir=None):
    if base_dir is None:
        base_dir = settings.BASE_DIR / "data"

    activity_logs = load_sessions_for_date(base_dir, date_str)
    stats = calculate_stats(activity_logs)

    try:
        summary = _generate_ollama_summary(date_str, stats, activity_logs)
        normalized_summary = _normalize_summary(summary)
    except (RuntimeError, ValueError, error.URLError, json.JSONDecodeError):
        return build_fallback_summary(date_str, stats, activity_logs)

    return {
        "date": date_str,
        "stats": stats,
        "accomplishments": normalized_summary["accomplishments"],
        "journal": normalized_summary["journal"],
        "productivity_score": normalized_summary["productivity_score"],
        "source": "ollama",
    }


def _generate_ollama_summary(date_str, stats, activity_logs):
    base_url = os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL).rstrip("/")
    model = os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
    payload = json.dumps(
        {
            "model": model,
            "format": "json",
            "stream": False,
            "prompt": _build_prompt(activity_logs, stats, date_str),
        }
    ).encode("utf-8")
    ollama_request = request.Request(
        f"{base_url}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with request.urlopen(ollama_request, timeout=30) as response:
        body = json.loads(response.read().decode("utf-8"))

    response_text = body.get("response", "")
    if not response_text:
        raise ValueError("Ollama response did not include summary content.")

    summary = json.loads(response_text)
    if not isinstance(summary, dict):
        raise ValueError("Ollama summary must be a JSON object.")

    return summary


def _normalize_summary(summary):
    accomplishments = summary.get("accomplishments")
    journal = summary.get("journal")
    productivity_score = summary.get("productivity_score")

    if not isinstance(accomplishments, list):
        raise ValueError("Ollama accomplishments must be a list.")

    if not isinstance(journal, str):
        raise ValueError("Ollama journal must be a string.")

    try:
        productivity_score = int(productivity_score)
    except (TypeError, ValueError):
        raise ValueError("Ollama productivity score must be int-compatible.") from None

    return {
        "accomplishments": accomplishments,
        "journal": journal,
        "productivity_score": productivity_score,
    }


def _build_prompt(activity_logs, stats, date_str):
    return (
        "Summarize this activity data into JSON with keys "
        "accomplishments, journal, and productivity_score.\n"
        f"Date: {date_str}\n"
        f"Stats: {json.dumps(stats, sort_keys=True)}\n"
        f"Activity logs: {json.dumps(activity_logs, sort_keys=True)}"
    )
