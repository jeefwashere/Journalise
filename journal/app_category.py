import json
import subprocess
from pathlib import Path


ALLOWED_CATEGORIES = {
    "work",
    "study",
    "relax",
    "communication",
    "other",
}
DEFAULT_CATEGORY = "other"
DEFAULT_CATEGORY_MODEL = "qwen3:8b"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
JSON_INDENT = 2
COMMON_APP_CATEGORIES = {
    "Code": "study",
    "Visual Studio Code": "study",
    "Cursor": "study",
    "Codex": "study",
    "PyCharm": "study",
    "Xcode": "study",
    "Terminal": "work",
    "iTerm": "work",
    "iTerm2": "work",
    "Warp": "work",
    "Postman": "work",
    "TablePlus": "work",
    "Docker Desktop": "work",
    "Notion": "study",
    "Obsidian": "study",
    "Notes": "study",
    "ChatGPT": "study",
    "Claude": "study",
    "Safari": "study",
    "Google Chrome": "study",
    "Arc": "study",
    "Firefox": "study",
    "WhatsApp": "communication",
    "WeChat": "communication",
    "Slack": "communication",
    "Discord": "communication",
    "Telegram": "communication",
    "Messages": "communication",
    "Zoom": "communication",
    "FaceTime": "communication",
    "Mail": "communication",
    "MSTeams": "communication",
    "Microsoft Teams": "communication",
    "Spotify": "relax",
    "Music": "relax",
    "TV": "relax",
    "YouTube": "relax",
    "Photos": "relax",
    "Preview": "other",
    "Finder": "other",
    "Calendar": "other",
    "System Settings": "other",
    "Microsoft Word": "work",
}


def build_category_library_path(base_dir: str | Path) -> Path:
    return Path(base_dir) / "category_library.json"


def _load_category_library(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    try:
        library = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}

    if not isinstance(library, dict):
        return {}

    normalized_library: dict[str, str] = {}
    for app_name, category in library.items():
        if not isinstance(app_name, str) or not isinstance(category, str):
            return {}
        normalized_category = category.strip().lower()
        if normalized_category not in ALLOWED_CATEGORIES:
            return {}
        normalized_library[app_name] = normalized_category

    return normalized_library


def _save_category_library(path: Path, library: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(library, indent=JSON_INDENT) + "\n",
        encoding="utf-8",
    )


def _merge_with_common_categories(library: dict[str, str]) -> dict[str, str]:
    merged = dict(COMMON_APP_CATEGORIES)
    merged.update(library)
    return merged


def _normalize_model_category(value: str) -> str | None:
    normalized = value.strip().strip('"').strip("'").lower()
    if normalized in ALLOWED_CATEGORIES:
        return normalized
    return None


def request_category_from_model(app_name: str, max_attempts: int = 2) -> str:
    prompt = (
        "Classify this software name into exactly one category from this list: "
        "work, study, relax, communication, other. "
        "Return one lowercase word only.\n"
        f"Software name: {app_name}"
    )
    payload = json.dumps(
        {
            "model": DEFAULT_CATEGORY_MODEL,
            "stream": False,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        }
    )

    for _ in range(max_attempts):
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
            continue

        category = _normalize_model_category(content)
        if category is not None:
            return category

    return DEFAULT_CATEGORY


def resolve_app_category(base_dir: str | Path, app_name: str) -> str:
    path = build_category_library_path(base_dir)
    library = _load_category_library(path)
    merged_library = _merge_with_common_categories(library)

    if merged_library != library:
        _save_category_library(path, merged_library)

    cached_category = merged_library.get(app_name)
    if cached_category is not None:
        return cached_category

    category = request_category_from_model(app_name)
    merged_library[app_name] = category
    _save_category_library(path, merged_library)
    return category
