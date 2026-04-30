import os
from pathlib import Path


def load_dotenv(path: str | Path = ".env") -> dict[str, str]:
    env_path = Path(path)
    if not env_path.exists():
        return {}

    loaded: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        loaded[key.strip()] = value.strip().strip('"').strip("'")
    return loaded


def get_env_value(key: str, env_path: str | Path = ".env") -> str | None:
    value = os.getenv(key)
    if value:
        return value

    dotenv_values = load_dotenv(env_path)
    return dotenv_values.get(key)
