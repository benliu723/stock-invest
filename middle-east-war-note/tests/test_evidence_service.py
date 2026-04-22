import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import sys


NOTE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(NOTE_ROOT))

from note_service import Evidence, EvidenceStore, SourceConfig, SourceRegistry, SubscriptionImporter  # noqa: E402


TZ = timezone(timedelta(hours=8))


def make_evidence(evidence_type: str, details: dict) -> Evidence:
    return Evidence.from_dict(
        {
            "id": f"evidence-2026-04-19-{evidence_type}",
            "type": evidence_type,
            "captured_at": datetime(2026, 4, 19, 9, 0, tzinfo=TZ).isoformat(),
            "event_at": datetime(2026, 4, 19, 8, 30, tzinfo=TZ).isoformat(),
            "confidence": 3,
            "summary": "中东局势维持高压。",
            "source": {
                "id": "manual",
                "name": "Manual entry",
                "url": "manual://entry",
            },
            "details": details,
        }
    )


class EvidenceStoreTest(unittest.TestCase):
    def test_save_statement_news_and_personal_note_round_trip(self):
        examples = [
            make_evidence(
                "statement",
                {
                    "speaker": "特朗普",
                    "quote": "We do not want a wider war.",
                    "context": "公开表态",
                },
            ),
            make_evidence(
                "news",
                {
                    "headline": "US adds forces in the Middle East",
                    "outlet": "AP",
                    "key_points": ["美军增兵", "地区风险上升"],
                },
            ),
            make_evidence(
                "personal_note",
                {
                    "note_text": "一位无法公开引用的信息源认为风险没有下降。",
                    "basis": "个人记录",
                },
            ),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            store = EvidenceStore(Path(temp_dir))
            for evidence in examples:
                store.save(evidence)
                self.assertEqual(store.get(evidence.id).to_dict(), evidence.to_dict())

    def test_rejects_missing_type_specific_details(self):
        with self.assertRaisesRegex(ValueError, "details.speaker"):
            make_evidence(
                "statement",
                {
                    "quote": "We do not want a wider war.",
                    "context": "公开表态",
                },
            )


class SourceRegistryTest(unittest.TestCase):
    def test_loads_enabled_sources_and_applies_default_confidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "sources.yaml"
            config_path.write_text(
                """
sources:
  - id: ap-middle-east
    name: AP Middle East
    kind: news_source
    url: https://example.com/ap/rss
    enabled: true
    parser: rss
  - id: trump-feed
    name: Trump feed
    kind: statement_source
    url: https://example.com/trump/rss
    enabled: false
    parser: rss
    default_confidence: 4
""",
                encoding="utf-8",
            )

            registry = SourceRegistry.load(config_path)

            enabled = registry.enabled_sources()
            self.assertEqual([source.id for source in enabled], ["ap-middle-east"])
            self.assertEqual(enabled[0].default_confidence, 3)


class SubscriptionImporterTest(unittest.TestCase):
    def test_imports_rss_items_as_news_evidence_with_default_confidence(self):
        rss = """
<rss>
  <channel>
    <item>
      <title>US adds forces in the Middle East</title>
      <link>https://example.com/ap/story-1</link>
      <pubDate>Sun, 19 Apr 2026 08:30:00 +0800</pubDate>
      <description>US officials said additional forces arrived in the region.</description>
    </item>
  </channel>
</rss>
"""

        source = SourceConfig.from_dict(
            {
                "id": "ap-middle-east",
                "name": "AP Middle East",
                "kind": "news_source",
                "url": "https://example.com/ap/rss",
                "enabled": True,
                "parser": "rss",
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            store = EvidenceStore(Path(temp_dir))
            importer = SubscriptionImporter(store, fetcher=lambda url: rss)

            imported = importer.import_sources([source], captured_at=datetime(2026, 4, 19, 9, 0, tzinfo=TZ))

            self.assertEqual(len(imported), 1)
            evidence = imported[0]
            self.assertEqual(evidence.type, "news")
            self.assertEqual(evidence.confidence, 3)
            self.assertEqual(evidence.summary, "US officials said additional forces arrived in the region.")
            self.assertEqual(evidence.details["headline"], "US adds forces in the Middle East")
            self.assertEqual(evidence.source["url"], "https://example.com/ap/story-1")
            self.assertEqual(store.get(evidence.id).to_dict(), evidence.to_dict())

    def test_page_import_respects_url_filter_and_max_items(self):
        page = """
<html>
  <body>
    <a href="/about">About</a>
    <a href="/world/middle-east/sports">Sports roundup</a>
    <a href="/world/middle-east/story-1">Middle East story 1</a>
    <a href="/world/middle-east/story-2">Middle East story 2</a>
  </body>
</html>
"""

        source = SourceConfig.from_dict(
            {
                "id": "reuters-middle-east",
                "name": "Reuters Middle East",
                "kind": "news_source",
                "url": "https://www.reuters.com/world/middle-east/",
                "enabled": True,
                "parser": "page",
                "url_contains": ["/world/middle-east/"],
                "title_contains": ["Middle East"],
                "max_items": 1,
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            store = EvidenceStore(Path(temp_dir))
            importer = SubscriptionImporter(store, fetcher=lambda url: page)

            imported = importer.import_sources([source], captured_at=datetime(2026, 4, 19, 9, 0, tzinfo=TZ))

            self.assertEqual(len(imported), 1)
            self.assertEqual(imported[0].source["url"], "https://www.reuters.com/world/middle-east/story-1")

    def test_uses_title_as_summary_when_rss_description_is_missing_and_deduplicates_url(self):
        rss = """
<rss>
  <channel>
    <item>
      <title>Trump comments on Middle East tensions</title>
      <link>https://example.com/trump/post-1</link>
      <pubDate>Sun, 19 Apr 2026 08:30:00 +0800</pubDate>
    </item>
  </channel>
</rss>
"""

        source = SourceConfig.from_dict(
            {
                "id": "trump-feed",
                "name": "Trump feed",
                "kind": "statement_source",
                "url": "https://example.com/trump/rss",
                "enabled": True,
                "parser": "rss",
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            store = EvidenceStore(Path(temp_dir))
            importer = SubscriptionImporter(store, fetcher=lambda url: rss)

            first_import = importer.import_sources([source], captured_at=datetime(2026, 4, 19, 9, 0, tzinfo=TZ))
            second_import = importer.import_sources([source], captured_at=datetime(2026, 4, 19, 9, 5, tzinfo=TZ))

            self.assertEqual(len(first_import), 1)
            self.assertEqual(len(second_import), 0)
            self.assertEqual(first_import[0].type, "statement")
            self.assertEqual(first_import[0].summary, "Trump comments on Middle East tensions")
            self.assertEqual(first_import[0].details["speaker"], "Trump feed")


if __name__ == "__main__":
    unittest.main()
