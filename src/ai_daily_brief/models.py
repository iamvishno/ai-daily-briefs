from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Article:
    title: str
    url: str
    summary: str
    source: str
    published: datetime | None
    categories: tuple[str, ...]
    priority: int = 5

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["published"] = self.published.isoformat() if self.published else None
        data["categories"] = list(self.categories)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Article":
        published = data.get("published")
        return cls(
            title=str(data["title"]),
            url=str(data["url"]),
            summary=str(data.get("summary", "")),
            source=str(data["source"]),
            published=datetime.fromisoformat(published) if published else None,
            categories=tuple(data.get("categories", [])),
            priority=int(data.get("priority", 5)),
        )


@dataclass(frozen=True)
class BriefContent:
    headline: str
    opening: str
    why_it_matters: str
    my_perspective: str
    next_step: str
    caution: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BriefContent":
        required = (
            "headline",
            "opening",
            "why_it_matters",
            "my_perspective",
            "next_step",
            "caution",
        )
        missing = [field for field in required if not str(data.get(field, "")).strip()]
        if missing:
            raise ValueError(f"Generated brief is missing fields: {', '.join(missing)}")
        return cls(**{field: str(data[field]).strip() for field in required})
