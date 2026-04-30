from pathlib import PureWindowsPath


APP_NAME_BY_EXECUTABLE = {
    "chrome": "Google Chrome",
    "code": "Visual Studio Code",
    "whatsapp.root": "WhatsApp",
    "whatsapp": "WhatsApp",
}
BROWSER_APP_NAMES = {
    "Google Chrome",
    "Microsoft Edge",
    "Safari",
    "Firefox",
    "Arc",
    "Brave Browser",
}


def _clean_executable_name(value: str) -> str:
    cleaned_value = value.strip()
    path = PureWindowsPath(cleaned_value)
    suffix = path.suffix.lower()
    stem = path.stem.strip()

    if suffix == ".exe":
        normalized = stem.lower()
        if normalized in APP_NAME_BY_EXECUTABLE:
            return APP_NAME_BY_EXECUTABLE[normalized]
        return stem or cleaned_value

    return cleaned_value


def activity_title_to_app_name(title: str) -> str:
    cleaned_title = title.strip()
    if not cleaned_title:
        return ""

    parts = [part.strip() for part in cleaned_title.split(" - ") if part.strip()]
    if len(parts) > 1:
        last_part = parts[-1]
        app_name = _clean_executable_name(last_part)
        if app_name in BROWSER_APP_NAMES:
            tab_title = " - ".join(parts[1:-1]).strip()
            if tab_title:
                return tab_title
        if app_name:
            return app_name

    return _clean_executable_name(cleaned_title)
