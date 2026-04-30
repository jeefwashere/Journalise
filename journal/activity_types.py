from dataclasses import asdict, dataclass


@dataclass
class ActivitySession:
    title: str
    category: str
    description: str
    started_at: str
    ended_at: str
    created_at: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)
