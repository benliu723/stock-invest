from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable, Dict, Iterable, Sequence


RUBY = "/usr/bin/ruby"
VALID_EVIDENCE_TYPES = ("statement", "news", "personal_note")
VALID_SOURCE_KINDS = ("statement_source", "news_source")
VALID_SOURCE_PARSERS = ("rss", "page")
DEFAULT_CONFIDENCE = 3


@dataclass(frozen=True)
class Evidence:
    id: str
    type: str
    captured_at: datetime
    event_at: datetime | None
    confidence: int
    summary: str
    source: Dict[str, object]
    details: Dict[str, object]

    @classmethod
    def from_dict(cls, raw: Dict[str, object]) -> "Evidence":
        evidence_id = _validate_evidence_id(raw.get("id"))
        evidence_type = _validate_choice(raw.get("type"), "type", VALID_EVIDENCE_TYPES)
        captured_at = _parse_datetime(raw.get("captured_at"), "captured_at")
        event_at_raw = raw.get("event_at")
        event_at = None if event_at_raw in (None, "") else _parse_datetime(event_at_raw, "event_at")
        confidence = _validate_confidence(raw.get("confidence", DEFAULT_CONFIDENCE))
        summary = _validate_non_empty_string(raw.get("summary"), "summary")
        source = _validate_source_payload(raw.get("source"))
        details = _validate_details(evidence_type, raw.get("details"))
        return cls(
            id=evidence_id,
            type=evidence_type,
            captured_at=captured_at,
            event_at=event_at,
            confidence=confidence,
            summary=summary,
            source=source,
            details=details,
        )

    @property
    def created_at(self) -> datetime:
        return self.captured_at

    def to_dict(self) -> Dict[str, object]:
        payload = {
            "id": self.id,
            "type": self.type,
            "captured_at": self.captured_at.isoformat(),
            "confidence": self.confidence,
            "summary": self.summary,
            "source": dict(self.source),
            "details": dict(self.details),
        }
        if self.event_at is not None:
            payload["event_at"] = self.event_at.isoformat()
        return payload


class EvidenceStore:
    def __init__(self, evidence_dir: Path):
        self.evidence_dir = Path(evidence_dir)

    def save(self, evidence: Evidence) -> Path:
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        target_path = self._path_for_evidence_id(evidence.id)
        dump_yaml(target_path, evidence.to_dict())
        return target_path

    def get(self, evidence_id: str) -> Evidence:
        path = self._path_for_evidence_id(evidence_id)
        if not path.exists():
            raise LookupError(f"evidence {evidence_id!r} does not exist")
        return load_evidence(path)

    def exists(self, evidence_id: str) -> bool:
        return self._path_for_evidence_id(evidence_id).exists()

    def has_source_url(self, source_url: str) -> bool:
        return any(evidence.source.get("url") == source_url for evidence in self.iter_evidence())

    def iter_evidence(self) -> Iterable[Evidence]:
        if not self.evidence_dir.exists():
            return iter(())
        return (load_evidence(path) for path in sorted(self.evidence_dir.glob("*.yaml")))

    def _path_for_evidence_id(self, evidence_id: str) -> Path:
        return self.evidence_dir / f"{_validate_evidence_id(evidence_id)}.yaml"


@dataclass(frozen=True)
class SourceConfig:
    id: str
    name: str
    kind: str
    url: str
    enabled: bool
    parser: str
    default_confidence: int = DEFAULT_CONFIDENCE
    url_contains: Sequence[str] = ()
    title_contains: Sequence[str] = ()
    max_items: int | None = None

    @classmethod
    def from_dict(cls, raw: Dict[str, object]) -> "SourceConfig":
        url_contains = tuple(
            _validate_non_empty_string(item, "source.url_contains[]")
            for item in raw.get("url_contains", [])
        )
        title_contains = tuple(
            _validate_non_empty_string(item, "source.title_contains[]")
            for item in raw.get("title_contains", [])
        )
        return cls(
            id=_validate_source_id(raw.get("id")),
            name=_validate_non_empty_string(raw.get("name"), "source.name"),
            kind=_validate_choice(raw.get("kind"), "source.kind", VALID_SOURCE_KINDS),
            url=_validate_non_empty_string(raw.get("url"), "source.url"),
            enabled=_validate_bool(raw.get("enabled", True), "source.enabled"),
            parser=_validate_choice(raw.get("parser"), "source.parser", VALID_SOURCE_PARSERS),
            default_confidence=_validate_confidence(raw.get("default_confidence", DEFAULT_CONFIDENCE)),
            url_contains=url_contains,
            title_contains=title_contains,
            max_items=_validate_optional_positive_int(raw.get("max_items"), "source.max_items"),
        )


class SourceRegistry:
    def __init__(self, sources: Sequence[SourceConfig]):
        self.sources = tuple(sources)

    @classmethod
    def load(cls, path: Path) -> "SourceRegistry":
        raw = load_yaml(path)
        return cls(tuple(SourceConfig.from_dict(item) for item in raw.get("sources", [])))

    def enabled_sources(self) -> Sequence[SourceConfig]:
        return tuple(source for source in self.sources if source.enabled)


class SubscriptionImporter:
    def __init__(self, store: EvidenceStore, fetcher: Callable[[str], str] | None = None):
        self.store = store
        self.fetcher = fetcher or _fetch_url

    def import_sources(
        self,
        sources: Sequence[SourceConfig],
        captured_at: datetime | None = None,
    ) -> Sequence[Evidence]:
        now = captured_at or datetime.now().astimezone()
        imported = []
        for source in sources:
            if not source.enabled:
                continue
            content = self.fetcher(source.url)
            for item in _parse_subscription_items(source, content):
                if self.store.has_source_url(item["url"]):
                    continue
                evidence = _item_to_evidence(source, item, now)
                self.store.save(evidence)
                imported.append(evidence)
        return tuple(imported)


# Legacy note classes are kept only so existing local callers do not break while
# the note layer moves to Evidence/EvidenceStore.
@dataclass(frozen=True)
class Source:
    type: str
    title: str
    url: str
    published_at: datetime | None = None

    @classmethod
    def from_dict(cls, raw: Dict[str, object]) -> "Source":
        published_at_raw = raw.get("published_at")
        return cls(
            type=_validate_non_empty_string(raw.get("type"), "source.type"),
            title=_validate_non_empty_string(raw.get("title"), "source.title"),
            url=_validate_non_empty_string(raw.get("url"), "source.url"),
            published_at=None
            if published_at_raw is None
            else _parse_datetime(published_at_raw, "source.published_at"),
        )

    def to_dict(self) -> Dict[str, object]:
        payload = {"type": self.type, "title": self.title, "url": self.url}
        if self.published_at is not None:
            payload["published_at"] = self.published_at.isoformat()
        return payload


@dataclass(frozen=True)
class Note:
    id: str
    created_at: datetime
    sources: Sequence[Source]
    summary: str
    observations: Sequence[str]

    @classmethod
    def from_dict(cls, raw: Dict[str, object]) -> "Note":
        sources = tuple(Source.from_dict(item) for item in raw.get("sources", []))
        if not sources:
            raise ValueError("sources must contain at least one source")
        observations = tuple(
            _validate_non_empty_string(item, "observations[]") for item in raw.get("observations", [])
        )
        if not observations:
            raise ValueError("observations must contain at least one observation")
        return cls(
            id=_validate_note_id(raw.get("id")),
            created_at=_parse_datetime(raw.get("created_at"), "created_at"),
            sources=sources,
            summary=_validate_non_empty_string(raw.get("summary"), "summary"),
            observations=observations,
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "sources": [source.to_dict() for source in self.sources],
            "summary": self.summary,
            "observations": list(self.observations),
        }


class NoteStore:
    def __init__(self, notes_dir: Path):
        self.notes_dir = Path(notes_dir)

    @staticmethod
    def load_note(raw: Dict[str, object]) -> Note:
        return Note.from_dict(raw)

    def save(self, note: Note) -> Path:
        self.notes_dir.mkdir(parents=True, exist_ok=True)
        target_path = self._path_for_note_id(note.id)
        dump_yaml(target_path, note.to_dict())
        return target_path

    def get(self, note_id: str) -> Note:
        path = self._path_for_note_id(note_id)
        if not path.exists():
            raise LookupError(f"note {note_id!r} does not exist")
        return load_note(path)

    def exists(self, note_id: str) -> bool:
        return self._path_for_note_id(note_id).exists()

    def _path_for_note_id(self, note_id: str) -> Path:
        return self.notes_dir / f"{_validate_note_id(note_id)}.yaml"


def load_evidence(path: Path) -> Evidence:
    return Evidence.from_dict(load_yaml(path))


def load_note(path: Path) -> Note:
    return Note.from_dict(load_yaml(path))


def load_yaml(path: Path) -> Dict[str, object]:
    script = (
        "require 'json'; require 'yaml'; "
        "data = YAML.safe_load(File.read(ARGV[0]), aliases: false); "
        "print JSON.generate(data)"
    )
    completed = subprocess.run(
        [RUBY, "-e", script, str(path)],
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(completed.stdout)


def dump_yaml(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    script = "require 'json'; require 'yaml'; print YAML.dump(JSON.parse(STDIN.read))"
    completed = subprocess.run(
        [RUBY, "-e", script],
        input=json.dumps(payload, ensure_ascii=False),
        check=True,
        text=True,
        capture_output=True,
    )
    path.write_text(completed.stdout, encoding="utf-8")


def _fetch_url(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "middle-east-war-note/0.1"})
    with urllib.request.urlopen(request, timeout=15) as response:
        return response.read().decode("utf-8", errors="replace")


def _parse_subscription_items(source: SourceConfig, content: str) -> Sequence[Dict[str, object]]:
    if source.parser == "rss":
        items = _parse_rss_items(content)
    if source.parser == "page":
        items = _parse_page_items(content, source.url)
    if source.parser not in VALID_SOURCE_PARSERS:
        raise ValueError(f"unsupported parser {source.parser!r}")

    filtered = tuple(
        item
        for item in items
        if _item_matches_filters(item, source)
    )
    if source.max_items is not None:
        return filtered[: source.max_items]
    return filtered


def _item_matches_filters(item: Dict[str, object], source: SourceConfig) -> bool:
    url = str(item["url"])
    title = str(item["title"])
    if source.url_contains and not any(part in url for part in source.url_contains):
        return False
    if source.title_contains and not any(part.lower() in title.lower() for part in source.title_contains):
        return False
    return True


def _parse_rss_items(content: str) -> Sequence[Dict[str, object]]:
    root = ET.fromstring(content)
    items = []
    for item in root.findall(".//item"):
        title = _xml_text(item, "title")
        link = _xml_text(item, "link")
        summary = _clean_text(_xml_text(item, "description")) or title
        published_at = _parse_rss_datetime(_xml_text(item, "pubDate"))
        if title and link:
            items.append({"title": title, "url": link, "summary": summary, "published_at": published_at})

    for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry"):
        title = _xml_text(entry, "{http://www.w3.org/2005/Atom}title")
        link = _atom_link(entry)
        summary = _clean_text(
            _xml_text(entry, "{http://www.w3.org/2005/Atom}summary")
            or _xml_text(entry, "{http://www.w3.org/2005/Atom}content")
        ) or title
        published_at = _parse_iso_datetime_or_none(
            _xml_text(entry, "{http://www.w3.org/2005/Atom}published")
            or _xml_text(entry, "{http://www.w3.org/2005/Atom}updated")
        )
        if title and link:
            items.append({"title": title, "url": link, "summary": summary, "published_at": published_at})
    return tuple(items)


class _LinkParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url.rstrip("/")
        self.links = []
        self._current_href = None
        self._text_chunks = []

    def handle_starttag(self, tag: str, attrs: Sequence[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self._current_href = href
            self._text_chunks = []

    def handle_data(self, data: str) -> None:
        if self._current_href is not None:
            self._text_chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or self._current_href is None:
            return
        title = _clean_text(" ".join(self._text_chunks))
        if title:
            self.links.append(
                {
                    "title": title,
                    "url": _absolute_url(self.base_url, self._current_href),
                    "summary": title,
                    "published_at": None,
                }
            )
        self._current_href = None
        self._text_chunks = []


def _parse_page_items(content: str, source_url: str) -> Sequence[Dict[str, object]]:
    parser = _LinkParser(source_url)
    parser.feed(content)
    return tuple(parser.links)


def _item_to_evidence(source: SourceConfig, item: Dict[str, object], captured_at: datetime) -> Evidence:
    evidence_type = _source_kind_to_evidence_type(source.kind)
    title = _validate_non_empty_string(item.get("title"), "item.title")
    url = _validate_non_empty_string(item.get("url"), "item.url")
    summary = _validate_non_empty_string(item.get("summary") or title, "item.summary")
    event_at = item.get("published_at")
    source_payload = {"id": source.id, "name": source.name, "url": url, "feed_url": source.url}
    if evidence_type == "news":
        details = {"headline": title, "outlet": source.name, "key_points": [summary]}
    else:
        details = {"speaker": source.name, "quote": title, "context": summary}
    return Evidence.from_dict(
        {
            "id": _evidence_id_for_url(source.id, url),
            "type": evidence_type,
            "captured_at": captured_at.isoformat(),
            "event_at": event_at.isoformat() if isinstance(event_at, datetime) else None,
            "confidence": source.default_confidence,
            "summary": summary,
            "source": source_payload,
            "details": details,
        }
    )


def _validate_evidence_id(value: object) -> str:
    evidence_id = _validate_non_empty_string(value, "id")
    if not evidence_id.startswith("evidence-"):
        raise ValueError("id must start with 'evidence-'")
    return evidence_id


def _validate_note_id(value: object) -> str:
    note_id = _validate_non_empty_string(value, "id")
    if not note_id.startswith("note-"):
        raise ValueError("id must start with 'note-'")
    return note_id


def _validate_source_id(value: object) -> str:
    source_id = _validate_non_empty_string(value, "source.id")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", source_id):
        raise ValueError("source.id must contain lowercase letters, numbers, and hyphens")
    return source_id


def _validate_non_empty_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _validate_choice(value: object, label: str, choices: Sequence[str]) -> str:
    text = _validate_non_empty_string(value, label)
    if text not in choices:
        raise ValueError(f"{label} must be one of {list(choices)}")
    return text


def _validate_bool(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{label} must be a boolean")
    return value


def _validate_confidence(value: object) -> int:
    if not isinstance(value, int) or not 0 <= value <= 5:
        raise ValueError("confidence must be an integer between 0 and 5")
    return value


def _validate_optional_positive_int(value: object, label: str) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _validate_source_payload(value: object) -> Dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError("source must be an object")
    payload = {
        "id": _validate_non_empty_string(value.get("id"), "source.id"),
        "name": _validate_non_empty_string(value.get("name"), "source.name"),
        "url": _validate_non_empty_string(value.get("url"), "source.url"),
    }
    if value.get("feed_url") is not None:
        payload["feed_url"] = _validate_non_empty_string(value.get("feed_url"), "source.feed_url")
    return payload


def _validate_details(evidence_type: str, value: object) -> Dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError("details must be an object")
    if evidence_type == "statement":
        return {
            "speaker": _validate_non_empty_string(value.get("speaker"), "details.speaker"),
            "quote": _validate_non_empty_string(value.get("quote"), "details.quote"),
            "context": _validate_non_empty_string(value.get("context"), "details.context"),
        }
    if evidence_type == "news":
        key_points = tuple(
            _validate_non_empty_string(item, "details.key_points[]") for item in value.get("key_points", [])
        )
        if not key_points:
            raise ValueError("details.key_points must contain at least one item")
        return {
            "headline": _validate_non_empty_string(value.get("headline"), "details.headline"),
            "outlet": _validate_non_empty_string(value.get("outlet"), "details.outlet"),
            "key_points": list(key_points),
        }
    if evidence_type == "personal_note":
        return {
            "note_text": _validate_non_empty_string(value.get("note_text"), "details.note_text"),
            "basis": _validate_non_empty_string(value.get("basis"), "details.basis"),
        }
    raise ValueError(f"unsupported evidence type {evidence_type!r}")


def _parse_datetime(value: object, label: str) -> datetime:
    text = _validate_non_empty_string(value, label)
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{label} must be a valid ISO 8601 datetime string") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{label} must include timezone information")
    return parsed


def _xml_text(element: ET.Element, name: str) -> str:
    child = element.find(name)
    if child is None or child.text is None:
        return ""
    return html.unescape(child.text.strip())


def _atom_link(entry: ET.Element) -> str:
    link = entry.find("{http://www.w3.org/2005/Atom}link")
    if link is None:
        return ""
    return link.attrib.get("href", "")


def _parse_rss_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return parsed.astimezone()
    return parsed


def _parse_iso_datetime_or_none(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return _parse_datetime(value, "feed datetime")
    except ValueError:
        return None


def _clean_text(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    return html.unescape(re.sub(r"\s+", " ", text)).strip()


def _absolute_url(base_url: str, href: str) -> str:
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("/"):
        match = re.match(r"^(https?://[^/]+)", base_url)
        if match:
            return f"{match.group(1)}{href}"
    return f"{base_url}/{href.lstrip('/')}"


def _source_kind_to_evidence_type(kind: str) -> str:
    if kind == "statement_source":
        return "statement"
    if kind == "news_source":
        return "news"
    raise ValueError(f"unsupported source kind {kind!r}")


def _evidence_id_for_url(source_id: str, url: str) -> str:
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
    return f"evidence-{source_id}-{digest}"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Middle East war evidence store")
    subparsers = parser.add_subparsers(dest="command", required=True)

    evidence_parent = argparse.ArgumentParser(add_help=False)
    evidence_parent.add_argument(
        "--evidence-dir",
        default=Path(__file__).resolve().parent / "evidence",
        type=Path,
        help="Directory that stores evidence yaml files",
    )

    put_parser = subparsers.add_parser("put", parents=[evidence_parent], help="Validate and store evidence YAML")
    put_parser.add_argument("input", type=Path, help="Path to an evidence YAML file")

    get_parser = subparsers.add_parser("get", parents=[evidence_parent], help="Read evidence by id")
    get_parser.add_argument("evidence_id", type=str)

    import_parser = subparsers.add_parser(
        "import-subscriptions",
        parents=[evidence_parent],
        help="Fetch enabled subscription sources and save metadata evidence",
    )
    import_parser.add_argument(
        "--sources",
        default=Path(__file__).resolve().parent / "sources.yaml",
        type=Path,
        help="Path to source config YAML",
    )

    return parser


def main(argv: Sequence[str]) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv[1:])
    store = EvidenceStore(args.evidence_dir)

    if args.command == "put":
        saved_path = store.save(load_evidence(args.input))
        print(saved_path)
        return 0

    if args.command == "get":
        print(json.dumps(store.get(args.evidence_id).to_dict(), ensure_ascii=False, indent=2))
        return 0

    if args.command == "import-subscriptions":
        registry = SourceRegistry.load(args.sources)
        imported = SubscriptionImporter(store).import_sources(registry.enabled_sources())
        print(json.dumps({"imported": [evidence.id for evidence in imported]}, ensure_ascii=False, indent=2))
        return 0

    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
