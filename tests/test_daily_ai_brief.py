from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_daily_brief.feeds import canonical_url, parse_feed  # noqa: E402
from ai_daily_brief.generator import source_based_fallback  # noqa: E402
from ai_daily_brief.ranking import choose_article  # noqa: E402
from ai_daily_brief.runner import run_daily  # noqa: E402
from ai_daily_brief.validation import validate_brief  # noqa: E402


class FeedTests(unittest.TestCase):
    def setUp(self) -> None:
        self.xml = (ROOT / "tests" / "fixtures" / "sample_feed.xml").read_text(
            encoding="utf-8"
        )
        self.source = {
            "name": "Test AI Research Feed",
            "categories": ["ai-tools", "healthcare-ai", "deep-learning-vision"],
            "priority": 10,
        }

    def test_rss_is_parsed_and_tracking_is_removed(self) -> None:
        articles = parse_feed(self.xml, self.source)
        self.assertEqual(len(articles), 3)
        self.assertEqual(
            articles[0].url,
            "https://example.org/ai/agent-evaluation-toolkit",
        )
        self.assertIsNotNone(articles[0].published)

    def test_atom_is_parsed(self) -> None:
        atom = """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <title>Agent evaluation with execution traces</title>
            <link href="https://example.org/papers/agent-traces" rel="alternate" />
            <updated>2026-09-15T05:00:00Z</updated>
            <summary>Execution traces expose tool calls, errors and recovery decisions.</summary>
          </entry>
        </feed>"""
        articles = parse_feed(atom, self.source)
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].url, "https://example.org/papers/agent-traces")

    def test_ranking_prefers_topic_relevance(self) -> None:
        articles = parse_feed(self.xml, self.source)
        topic = {
            "slug": "healthcare-ai",
            "label": "Healthcare AI",
            "keywords": ["clinical", "patient", "calibration"],
        }
        selected = choose_article(articles, topic, set(), date(2026, 9, 15))
        self.assertIn("clinical", selected.title.lower())

    def test_used_url_is_not_selected_again(self) -> None:
        articles = parse_feed(self.xml, self.source)
        topic = {
            "slug": "ai-tools",
            "label": "AI tools",
            "keywords": ["toolkit", "tool", "agent"],
        }
        used = {canonical_url(articles[0].url)}
        selected = choose_article(articles, topic, used, date(2026, 9, 15))
        self.assertNotEqual(selected.url, articles[0].url)


class WritingTests(unittest.TestCase):
    def test_fallback_is_human_readable_and_safe(self) -> None:
        source = {
            "name": "Test AI Research Feed",
            "categories": ["ai-tools"],
            "priority": 10,
        }
        article = parse_feed(
            (ROOT / "tests" / "fixtures" / "sample_feed.xml").read_text(encoding="utf-8"),
            source,
        )[0]
        topic = json.loads((ROOT / "config" / "topics.json").read_text(encoding="utf-8"))[
            "tuesday"
        ]
        content = source_based_fallback(article, topic)
        validate_brief(content)
        combined = " ".join(content.__dict__.values()).lower()
        self.assertIn("for me", combined)
        self.assertNotIn("i tested", combined)
        self.assertNotIn("game-changing", combined)

    def test_fallback_passes_for_every_weekday_voice(self) -> None:
        source = {
            "name": "Test AI Research Feed",
            "categories": ["ai-tools"],
            "priority": 10,
        }
        article = parse_feed(
            (ROOT / "tests" / "fixtures" / "sample_feed.xml").read_text(encoding="utf-8"),
            source,
        )[0]
        topics = json.loads((ROOT / "config" / "topics.json").read_text(encoding="utf-8"))
        for weekday, topic in topics.items():
            with self.subTest(weekday=weekday):
                validate_brief(source_based_fallback(article, topic))


class IntegrationTests(unittest.TestCase):
    def _copy_project(self, destination: Path) -> None:
        for name in ("README.md", "config", "data", "tests"):
            source = ROOT / name
            target = destination / name
            if source.is_dir():
                shutil.copytree(source, target)
            else:
                shutil.copy2(source, target)

    def test_run_creates_one_post_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            temp_root = Path(temp_directory)
            self._copy_project(temp_root)
            clean_environment = {key: value for key, value in os.environ.items() if key != "GEMINI_API_KEY"}
            with patch.dict(os.environ, clean_environment, clear=True):
                path, message = run_daily(
                    temp_root,
                    run_date=date(2026, 9, 15),
                    fixture_path=Path("tests/fixtures/sample_feed.xml"),
                )
                self.assertIsNotNone(path)
                self.assertTrue(path.exists())
                self.assertIn("source-based-fallback", message)
                markdown = path.read_text(encoding="utf-8")
                self.assertIn("## My perspective", markdown)
                self.assertIn("https://example.org/ai/agent-evaluation-toolkit", markdown)
                self.assertIn(path.name, (temp_root / "README.md").read_text(encoding="utf-8"))

                second_path, second_message = run_daily(
                    temp_root,
                    run_date=date(2026, 9, 15),
                    fixture_path=Path("tests/fixtures/sample_feed.xml"),
                )
                self.assertIsNone(second_path)
                self.assertIn("nothing changed", second_message)
                posts = list((temp_root / "daily").glob("*/*/*.md"))
                self.assertEqual(len(posts), 1)


if __name__ == "__main__":
    unittest.main()
