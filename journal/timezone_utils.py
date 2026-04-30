from datetime import datetime, timedelta, timezone


LOCAL_TZ = timezone(timedelta(hours=-4), name="UTC-4")


def parse_timestamp(value: str) -> datetime:
    if value.endswith("Z"):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return datetime.fromisoformat(value)


def format_timestamp(value: datetime) -> str:
    return value.astimezone(LOCAL_TZ).isoformat()


def local_date_str(value: datetime | str) -> str:
    if isinstance(value, str):
        value = parse_timestamp(value)
    return value.astimezone(LOCAL_TZ).date().isoformat()
