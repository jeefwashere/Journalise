def _duration_seconds(value):
    try:
        if value is None:
            return 0
        duration_seconds = int(value)
    except (TypeError, ValueError):
        return 0

    if duration_seconds < 0:
        return 0

    return duration_seconds


def calculate_stats(activity_logs):
    total_tracked_seconds = 0
    session_count = len(activity_logs)
    app_totals = {}

    for log in activity_logs:
        app_name = log.get("app_name") or "Unknown"
        duration_seconds = _duration_seconds(log.get("duration_seconds"))
        total_tracked_seconds += duration_seconds
        app_totals[app_name] = app_totals.get(app_name, 0) + duration_seconds

    top_apps = [
        {"app_name": app_name, "duration_seconds": duration_seconds}
        for app_name, duration_seconds in sorted(
            app_totals.items(),
            key=lambda item: item[1],
            reverse=True,
        )
        if duration_seconds > 0
    ]

    if session_count == 0:
        productivity_score = 0
    else:
        productivity_score = min(100, int(total_tracked_seconds / 60))

    return {
        "total_tracked_seconds": total_tracked_seconds,
        "session_count": session_count,
        "top_apps": top_apps,
        "productivity_score": productivity_score,
    }
