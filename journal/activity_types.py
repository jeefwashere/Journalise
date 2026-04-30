from dataclasses import asdict, dataclass


@dataclass
class ActivitySession:
    app_name: str
    bundle_id: str
    started_at: str
    ended_at: str
    duration_seconds: int

    def to_dict(self) -> dict[str, str | int]:
        return asdict(self)
