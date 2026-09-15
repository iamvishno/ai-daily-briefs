from __future__ import annotations

from datetime import UTC, date, datetime

from .feeds import canonical_url
from .models import Article


def article_score(article: Article, topic: dict, run_date: date) -> float:
    searchable_title = article.title.casefold()
    searchable_summary = article.summary.casefold()
    keywords = [str(item).casefold() for item in topic.get("keywords", [])]

    title_matches = sum(keyword in searchable_title for keyword in keywords)
    summary_matches = sum(keyword in searchable_summary for keyword in keywords)
    category_match = topic["slug"] in article.categories

    score = float(article.priority * 5)
    score += min(title_matches, 5) * 10
    score += min(summary_matches, 8) * 3
    score += 25 if category_match else 0

    if article.published:
        reference = datetime.combine(run_date, datetime.min.time(), tzinfo=UTC)
        age_days = max(0.0, (reference - article.published).total_seconds() / 86_400)
        score += max(0.0, 50.0 - min(age_days, 50.0))
    return score


def choose_article(
    articles: list[Article], topic: dict, used_urls: set[str], run_date: date
) -> Article:
    available = [item for item in articles if canonical_url(item.url) not in used_urls]
    if not available:
        raise ValueError("No unused source item is available")
    return max(available, key=lambda item: article_score(item, topic, run_date))
