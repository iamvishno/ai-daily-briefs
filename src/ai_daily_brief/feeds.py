from __future__ import annotations

import html
import re
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .models import Article


USER_AGENT = "VishnuDailyAIBriefs/1.0 (+https://github.com/iamvishno)"
TRACKING_PARAMETERS = {"fbclid", "gclid", "mc_cid", "mc_eid"}


def canonical_url(value: str) -> str:
    """Remove fragments and common tracking parameters from a source URL."""
    value = value.strip()
    parts = urlsplit(value)
    query = [
        (key, item)
        for key, item in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in TRACKING_PARAMETERS
    ]
    clean_path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), clean_path, urlencode(query), ""))


def plain_text(value: str, limit: int = 1800) -> str:
    """Convert a small HTML feed excerpt to compact plain text."""
    value = re.sub(r"<script\b[^>]*>.*?</script>", " ", value or "", flags=re.I | re.S)
    value = re.sub(r"<style\b[^>]*>.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    value = re.sub(r"\s+", " ", value).strip()
    return value[:limit]


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        parsed = None
    if parsed is None:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _child_text(element: ET.Element, names: Iterable[str]) -> str:
    wanted = {name.lower() for name in names}
    for child in element.iter():
        local_name = child.tag.rsplit("}", 1)[-1].lower()
        if local_name in wanted and child.text:
            return child.text.strip()
    return ""


def _entry_link(entry: ET.Element) -> str:
    for child in entry:
        if child.tag.rsplit("}", 1)[-1].lower() != "link":
            continue
        href = child.attrib.get("href", "").strip()
        relation = child.attrib.get("rel", "alternate")
        if href and relation in {"alternate", ""}:
            return href
        if child.text and child.text.strip():
            return child.text.strip()
    return _child_text(entry, ("guid", "id"))


def parse_feed(xml_text: str, source: dict) -> list[Article]:
    """Parse RSS, Atom and arXiv Atom entries into one small data model."""
    root = ET.fromstring(xml_text)
    entries = [node for node in root.iter() if node.tag.rsplit("}", 1)[-1] in {"item", "entry"}]
    articles: list[Article] = []
    seen: set[str] = set()

    for entry in entries:
        title = plain_text(_child_text(entry, ("title",)), limit=300)
        url = canonical_url(_entry_link(entry))
        summary = plain_text(_child_text(entry, ("description", "summary", "content")))
        published = parse_datetime(
            _child_text(entry, ("published", "updated", "pubDate", "date"))
        )
        if not title or not url or url in seen:
            continue
        seen.add(url)
        articles.append(
            Article(
                title=title,
                url=url,
                summary=summary,
                source=str(source["name"]),
                published=published,
                categories=tuple(source.get("categories", [])),
                priority=int(source.get("priority", 5)),
            )
        )
    return articles


def fetch_text(url: str, timeout: int = 25, attempts: int = 3) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/atom+xml, application/rss+xml, application/xml, text/xml",
        },
    )
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return response.read().decode(charset, errors="replace")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Unable to fetch {url}: {last_error}")


def collect_articles(sources: list[dict], topic_slug: str) -> tuple[list[Article], list[str]]:
    articles: list[Article] = []
    errors: list[str] = []
    for source in sources:
        if topic_slug not in source.get("categories", []):
            continue
        try:
            articles.extend(parse_feed(fetch_text(str(source["feed_url"])), source))
        except (RuntimeError, ET.ParseError, KeyError, ValueError) as exc:
            errors.append(f"{source.get('name', 'Unknown source')}: {exc}")
    return articles, errors
