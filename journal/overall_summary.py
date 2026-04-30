import json
import subprocess
from pathlib import Path

from journal.env_utils import get_env_value
from journal.hourly_summary import build_hourly_summary_path
from journal.management.commands.collect_activity import build_vision_summary_path
from journal.privacy import sanitize_text


DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
JSON_INDENT = 2


def build_overall_summary_path(base_dir: str | Path, date_str: str) -> Path:
    return Path(base_dir) / "overall_summaries" / f"{date_str}.json"


def _load_json_list(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    if not isinstance(data, list):
        return []

    return [item for item in data if isinstance(item, dict)]


def clean_vision_summary_entries(
    vision_summaries: list[dict[str, object]],
) -> list[dict[str, str]]:
    clean_entries: list[dict[str, str]] = []

    for entry in vision_summaries:
        captured_at = entry.get("captured_at")
        summary = entry.get("summary")

        if not isinstance(captured_at, str) or not isinstance(summary, str):
            continue

        clean_entries.append(
            {
                "captured_at": captured_at,
                "summary": sanitize_text(summary),
            }
        )

    return clean_entries


def request_gemini_overall_summary(
    clean_vision_summaries: list[dict[str, str]],
    hourly_summaries: list[dict[str, object]],
    env_path: str | Path = ".env",
) -> str:
    api_key = get_env_value("GEMINI_API_KEY", env_path=env_path)
    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing. Add it to .env before generating an overall summary.")

    payload = json.dumps(
        {
            "contents": [
                {
                    "parts": [
                        {
                            "text": (
                                    "Write a personal daily journal entry based on the user's activity data. "
                                    "The tone should be reflective, natural, and first-person, like a short end-of-day diary. "
                                    "Do not sound like a productivity report or surveillance log. "
                                    "Avoid sensitive details, exact website titles, private names, account information, or overly specific screen content. "
                                    "Summarize the day by describing the main activities, focus patterns, interruptions, and transitions. "
                                    "Mention what the user seemed to spend the most time on, what felt productive, and what could be improved tomorrow. "
                                    "Keep it concise, around 120 to 180 words.\n\n"
                                + json.dumps(
                                    {
                                        "hourly_summaries": hourly_summaries,
                                        "vision_summaries": clean_vision_summaries,
                                    }
                                )
                            )
                        }
                    ]
                }
            ]
        }
    )

    result = subprocess.run(
        [
            "curl",
            "-sS",
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{DEFAULT_GEMINI_MODEL}:generateContent",
            "-H",
            f"x-goog-api-key: {api_key}",
            "-H",
            "Content-Type: application/json",
            "-X",
            "POST",
            "-d",
            payload,
        ],
        capture_output=True,
        text=True,
        timeout=180,
        check=True,
    )

    body = json.loads(result.stdout)
    candidates = body.get("candidates") or []
    if not candidates:
        raise ValueError("Gemini response did not include any candidates.")

    content = candidates[0].get("content") or {}
    parts = content.get("parts") or []
    if not parts:
        raise ValueError("Gemini response did not include any parts.")

    text = parts[0].get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Gemini response did not include summary text.")

    return sanitize_text(text.strip())


def generate_and_persist_overall_summary(
    base_dir: str | Path,
    date_str: str,
    env_path: str | Path = ".env",
) -> dict[str, object]:
    vision_path = build_vision_summary_path(base_dir, date_str)
    hourly_path = build_hourly_summary_path(base_dir, date_str)

    vision_summaries = _load_json_list(vision_path)
    hourly_summaries = _load_json_list(hourly_path)

    clean_vision_summaries = clean_vision_summary_entries(vision_summaries)

    summary = request_gemini_overall_summary(
        clean_vision_summaries,
        hourly_summaries,
        env_path=env_path,
    )

    payload = {
        "date": date_str,
        "moderation_model": None,
        "summary_model": DEFAULT_GEMINI_MODEL,
        "moderation_results": [],
        "clean_vision_summaries": clean_vision_summaries,
        "overall_summary": summary,
    }

    output_path = build_overall_summary_path(base_dir, date_str)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=JSON_INDENT) + "\n",
        encoding="utf-8",
    )

    return payload