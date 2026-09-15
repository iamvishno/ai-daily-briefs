from __future__ import annotations

import re
from urllib.parse import urlsplit

from .models import Article, BriefContent


BANNED_PERSONAL_CLAIMS = (
    r"\bI tested\b",
    r"\bI built\b",
    r"\bI implemented\b",
    r"\bI deployed\b",
    r"\bI used (?:this|the featured|the new)\b",
    r"\btoday I learned\b",
)


def _word_count(value: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", value))


def validate_article(article: Article) -> None:
    parts = urlsplit(article.url)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ValueError("The selected source URL is not a valid HTTP(S) URL")
    if len(article.title.strip()) < 8:
        raise ValueError("The selected source title is too short")
    if not article.source.strip():
        raise ValueError("The selected item has no source name")


def validate_brief(content: BriefContent) -> None:
    fields = (
        content.headline,
        content.opening,
        content.why_it_matters,
        content.my_perspective,
        content.next_step,
        content.caution,
    )
    combined = " ".join(fields)
    total_words = _word_count(combined)
    if not 130 <= total_words <= 300:
        raise ValueError(f"Brief length must be 130-300 words; received {total_words}")
    if not 8 <= len(content.headline) <= 180:
        raise ValueError("Headline length is outside the accepted range")
    if "I " not in content.my_perspective and "my " not in content.my_perspective.lower():
        raise ValueError("The perspective section must contain a genuine first-person connection")
    if "I " not in content.next_step:
        raise ValueError("The next-step section must be written as a first-person intention")
    if any("<" in value or ">" in value for value in fields):
        raise ValueError("Generated sections must not contain HTML")
    for pattern in BANNED_PERSONAL_CLAIMS:
        if re.search(pattern, combined, flags=re.I):
            raise ValueError(f"Unsupported personal claim detected: {pattern}")
    if re.search(r"\b(?:revolutionary|game-changing|changes everything)\b", combined, flags=re.I):
        raise ValueError("Unnecessary promotional language detected")


def validate_rendered_post(markdown: str, article: Article) -> None:
    required_headings = (
        "## Why this matters",
        "## My perspective",
        "## What I want to explore next",
        "## A point to keep in mind",
        "## Source",
    )
    missing = [heading for heading in required_headings if heading not in markdown]
    if missing:
        raise ValueError(f"Rendered post is missing headings: {', '.join(missing)}")
    if article.url not in markdown:
        raise ValueError("Rendered post does not contain the original source URL")
    if "automatically curated" not in markdown:
        raise ValueError("Rendered post does not contain the automation disclosure")
