from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .feeds import canonical_url, collect_articles, parse_feed
from .generator import generate_brief
from .models import Article
from .ranking import choose_article
from .rendering import dated_post_path, render_post, update_readme_index
from .validation import validate_article, validate_brief, validate_rendered_post


LONDON = ZoneInfo("Europe/London")
WEEKDAY_NAMES = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def save_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _state(path: Path) -> dict:
    if not path.exists():
        return {"used_urls": [], "article_cache": [], "last_successful_run": None}
    value = load_json(path)
    value.setdefault("used_urls", [])
    value.setdefault("article_cache", [])
    value.setdefault("last_successful_run", None)
    return value


def _cached_articles(state: dict) -> list[Article]:
    articles: list[Article] = []
    for item in state.get("article_cache", []):
        try:
            articles.append(Article.from_dict(item))
        except (KeyError, TypeError, ValueError):
            continue
    return articles


def _fallback_articles(root: Path) -> list[Article]:
    articles: list[Article] = []
    for item in load_json(root / "data" / "fallback_sources.json"):
        articles.append(
            Article(
                title=str(item["title"]),
                url=canonical_url(str(item["url"])),
                summary=str(item["summary"]),
                source=str(item["source"]),
                published=None,
                categories=tuple(item.get("categories", [])),
                priority=int(item.get("priority", 6)),
            )
        )
    return articles


def _merge_articles(*groups: list[Article]) -> list[Article]:
    merged: dict[str, Article] = {}
    for group in groups:
        for article in group:
            url = canonical_url(article.url)
            if url:
                merged[url] = article
    return list(merged.values())


def _fixture_articles(root: Path, fixture_path: Path, topic_slug: str) -> list[Article]:
    source = {
        "name": "Test AI Research Feed",
        "categories": [topic_slug],
        "priority": 10,
    }
    path = fixture_path if fixture_path.is_absolute() else root / fixture_path
    return parse_feed(path.read_text(encoding="utf-8"), source)


def _already_has_post(root: Path, run_date: date) -> bool:
    folder = root / "daily" / f"{run_date:%Y}" / f"{run_date:%m}"
    return folder.exists() and any(folder.glob(f"{run_date.isoformat()}-*.md"))


def _cache_payload(articles: list[Article], limit: int = 250) -> list[dict]:
    dated = sorted(
        articles,
        key=lambda item: item.published or datetime.min.replace(tzinfo=LONDON),
        reverse=True,
    )
    return [article.to_dict() for article in dated[:limit]]


def run_daily(
    root: Path,
    run_date: date | None = None,
    fixture_path: Path | None = None,
    dry_run: bool = False,
    strict_ai: bool = False,
) -> tuple[Path | None, str]:
    root = root.resolve()
    run_date = run_date or datetime.now(LONDON).date()
    if _already_has_post(root, run_date) and not dry_run:
        return None, f"A daily brief already exists for {run_date.isoformat()}; nothing changed."

    topics = load_json(root / "config" / "topics.json")
    topic = topics[WEEKDAY_NAMES[run_date.weekday()]]
    profile = load_json(root / "config" / "profile.json")
    state_path = root / "data" / "state.json"
    state = _state(state_path)

    if fixture_path:
        fresh_articles = _fixture_articles(root, fixture_path, topic["slug"])
        collection_errors: list[str] = []
    else:
        sources = load_json(root / "config" / "sources.json")
        fresh_articles, collection_errors = collect_articles(sources, topic["slug"])

    for error in collection_errors:
        print(f"Source warning: {error}", file=sys.stderr)

    cached = _cached_articles(state)
    fallbacks = [
        article
        for article in _fallback_articles(root)
        if topic["slug"] in article.categories
    ]
    candidates = _merge_articles(cached, fallbacks, fresh_articles)
    used_urls = {canonical_url(value) for value in state.get("used_urls", [])}
    article = choose_article(candidates, topic, used_urls, run_date)
    validate_article(article)

    content, generation_mode = generate_brief(
        article,
        topic,
        profile,
        allow_fallback=not strict_ai,
    )
    validate_brief(content)
    markdown = render_post(run_date, topic, article, content, generation_mode)
    validate_rendered_post(markdown, article)

    path = dated_post_path(root, run_date, content.headline)
    if dry_run:
        return path, markdown

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing daily brief: {path}")
    path.write_text(markdown, encoding="utf-8")

    updated_urls = list(state.get("used_urls", []))
    updated_urls.append(canonical_url(article.url))
    state["used_urls"] = list(dict.fromkeys(updated_urls))[-1500:]
    state["article_cache"] = _cache_payload(_merge_articles(cached, fresh_articles))
    state["last_successful_run"] = datetime.now(LONDON).isoformat()
    save_json(state_path, state)
    update_readme_index(root)
    return path, f"Created {path.relative_to(root).as_posix()} using {generation_mode}."
