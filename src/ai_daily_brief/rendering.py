from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from .models import Article, BriefContent


INDEX_START = "<!-- DAILY_INDEX_START -->"
INDEX_END = "<!-- DAILY_INDEX_END -->"


def slugify(value: str, maximum_length: int = 80) -> str:
    value = value.casefold()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    if len(value) > maximum_length:
        value = value[:maximum_length].rsplit("-", 1)[0]
    return value.rstrip("-") or "ai-update"


def dated_post_path(root: Path, run_date: date, headline: str) -> Path:
    return (
        root
        / "daily"
        / f"{run_date:%Y}"
        / f"{run_date:%m}"
        / f"{run_date.isoformat()}-{slugify(headline)}.md"
    )


def render_post(
    run_date: date,
    topic: dict,
    article: Article,
    content: BriefContent,
    generation_mode: str,
) -> str:
    source_date = article.published.date().isoformat() if article.published else "not supplied"
    metadata = {
        "date": run_date.isoformat(),
        "topic": topic["label"],
        "source": article.source,
        "source_url": article.url,
        "source_published": source_date,
        "automated": True,
        "generation_mode": generation_mode,
    }
    front_matter = "\n".join(
        f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in metadata.items()
    )
    return f"""---
{front_matter}
---

# {content.headline}

{content.opening}

## Why this matters

{content.why_it_matters}

## My perspective

{content.my_perspective}

## What I want to explore next

{content.next_step}

## A point to keep in mind

{content.caution}

## Source

[{article.source}: {article.title}]({article.url})

---

> This daily brief was automatically curated from the cited primary source. Personal project claims are never generated automatically.
"""


def _post_metadata(path: Path, root: Path) -> tuple[str, str, str] | None:
    match = re.match(r"(\d{4}-\d{2}-\d{2})-", path.name)
    if not match:
        return None
    text = path.read_text(encoding="utf-8")
    heading = re.search(r"^# (.+)$", text, flags=re.M)
    if not heading:
        return None
    relative = path.relative_to(root).as_posix()
    return match.group(1), heading.group(1).strip(), relative


def update_readme_index(root: Path, maximum_entries: int = 30) -> None:
    readme_path = root / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    if INDEX_START not in readme or INDEX_END not in readme:
        raise ValueError("README index markers are missing")

    entries = [
        item
        for item in (_post_metadata(path, root) for path in root.glob("daily/*/*/*.md"))
        if item is not None
    ]
    entries.sort(key=lambda item: item[0], reverse=True)
    if entries:
        index = "\n".join(
            f"- [{entry_date} — {title}]({relative})"
            for entry_date, title, relative in entries[:maximum_entries]
        )
    else:
        index = "No daily briefs have been published yet."

    replacement = f"{INDEX_START}\n{index}\n{INDEX_END}"
    updated = re.sub(
        rf"{re.escape(INDEX_START)}.*?{re.escape(INDEX_END)}",
        replacement,
        readme,
        count=1,
        flags=re.S,
    )
    readme_path.write_text(updated, encoding="utf-8")
