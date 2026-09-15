from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from typing import Any

from .models import Article, BriefContent


DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"


SYSTEM_INSTRUCTION = """You write one short daily AI briefing for Vishnu Vardhan's GitHub repository.

Voice:
- natural, clear British English;
- thoughtful and practical, like a technically curious early-career AI practitioner;
- human rhythm, varied sentence length and no corporate slogans;
- calm rather than breathless or promotional.

Evidence rules:
- use only the supplied source title, source excerpt and verified profile;
- never invent a capability, benchmark, date, quotation or project result;
- never claim Vishnu tested, built, implemented, deployed or used the featured technology;
- do not write "today I learned";
- personal wording may describe verified interests, existing profile facts or future intentions only;
- make uncertainty or a limitation visible;
- do not copy long wording from the source excerpt.

Return only a valid JSON object with exactly these string keys:
headline, opening, why_it_matters, my_perspective, next_step, caution.

The six values together should contain 150 to 250 words. Do not put Markdown headings, links, hashtags or emojis in the values."""


def _clean_generated_text(value: str) -> str:
    value = value.strip()
    value = re.sub(r"^```(?:json)?\s*|\s*```$", "", value, flags=re.I | re.S)
    return value.strip()


def _normalise_section(value: str) -> str:
    value = re.sub(r"^#+\s*", "", value.strip(), flags=re.M)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _gemini_payload(article: Article, topic: dict, profile: dict) -> dict[str, Any]:
    source_date = article.published.date().isoformat() if article.published else "not supplied"
    prompt = {
        "daily_topic": topic["label"],
        "source": {
            "publisher": article.source,
            "title": article.title,
            "published": source_date,
            "excerpt": article.summary[:1600],
        },
        "verified_profile": {
            "positioning": profile["positioning"],
            "background": profile["verified_background"],
            "technical_focus": profile["technical_focus"],
        },
        "safe_personal_connection": topic["connection"],
        "task": (
            "Explain the source-specific development, why it matters technically, how it "
            "connects with the safe personal connection, a realistic next learning question, "
            "and one important limitation. Keep the opening grounded and avoid hype."
        ),
    }
    return {
        "system_instruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
        "contents": [{"role": "user", "parts": [{"text": json.dumps(prompt)}]}],
        "generationConfig": {
            "temperature": 0.65,
            "topP": 0.9,
            "maxOutputTokens": 750,
            "responseMimeType": "application/json",
        },
    }


def _call_gemini(
    article: Article,
    topic: dict,
    profile: dict,
    api_key: str,
    model: str,
    attempts: int = 3,
) -> BriefContent:
    url = f"{GEMINI_API_BASE}/models/{model}:generateContent"
    body = json.dumps(_gemini_payload(article, topic, profile)).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
            "User-Agent": "VishnuDailyAIBriefs/1.0",
        },
    )

    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=75) as response:
                payload = json.loads(response.read().decode("utf-8"))
            raw_text = payload["candidates"][0]["content"]["parts"][0]["text"]
            raw_data = json.loads(_clean_generated_text(raw_text))
            cleaned = {key: _normalise_section(str(value)) for key, value in raw_data.items()}
            return BriefContent.from_dict(cleaned)
        except (
            urllib.error.URLError,
            TimeoutError,
            OSError,
            KeyError,
            IndexError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Gemini generation failed after {attempts} attempts: {last_error}")


def _short_source_signal(summary: str, maximum_words: int = 22) -> str:
    first_sentence = re.split(r"(?<=[.!?])\s+", summary.strip(), maxsplit=1)[0]
    words = re.findall(r"\S+", first_sentence)
    if not words:
        return "a technical development that deserves closer reading in the original source"
    signal = " ".join(words[:maximum_words]).rstrip(".,;:")
    return signal[0].lower() + signal[1:] if signal else signal


def source_based_fallback(article: Article, topic: dict) -> BriefContent:
    """Create a conservative brief when the configured language model is unavailable."""
    signal = _short_source_signal(article.summary)
    connection = topic["connection"]
    topic_label = topic["label"][:1].lower() + topic["label"][1:]
    return BriefContent(
        headline=article.title,
        opening=(
            f"Today's useful AI reading comes from {article.source}: “{article.title}”. The short "
            f"source description notes that {signal}. The original publication is linked below, "
            "so the full context and technical evidence remain easy to check."
        ),
        why_it_matters=(
            f"This matters because developments in {topic_label} should be judged by what they change "
            "in a real technical workflow, not by the headline alone. The practical questions "
            "are reliability, evidence, evaluation and the conditions under which the approach "
            "actually works."
        ),
        my_perspective=(
            f"For me, the most relevant connection is {connection}. I am interested in the "
            "engineering choices behind the result and in how those choices would be explained "
            "to someone who needs to trust the system."
        ),
        next_step=(
            "I want to read the source in full, identify the evaluation method and compare its "
            "claims with the constraints of a small, reproducible AI application."
        ),
        caution=(
            "A short announcement or abstract cannot establish real-world value on its own. "
            "Dataset quality, baselines, failure cases, cost and human oversight still need "
            "separate attention."
        ),
    )


def generate_brief(
    article: Article, topic: dict, profile: dict, allow_fallback: bool = True
) -> tuple[BriefContent, str]:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    model = os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL
    if api_key:
        try:
            return _call_gemini(article, topic, profile, api_key, model), f"gemini:{model}"
        except RuntimeError:
            if not allow_fallback:
                raise
    if not allow_fallback:
        raise RuntimeError("GEMINI_API_KEY is required when fallback generation is disabled")
    return source_based_fallback(article, topic), "source-based-fallback"
