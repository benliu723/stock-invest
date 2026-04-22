from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Sequence


VALID_DIRECTIONS = ("缓和", "僵持", "升级")
VALID_KINDS = ("core", "stage")
GRADE_MIN = 0
GRADE_MAX = 5
LEGACY_SCALE = 20
RUBY = "/usr/bin/ruby"
NOTE_SERVICE_PATH = Path(__file__).resolve().parent.parent / "middle-east-war-note" / "note_service.py"
_NOTE_SERVICE_MODULE = None


@dataclass(frozen=True)
class FactorSnapshot:
    id: str
    text: str
    kind: str
    weight: int
    direction: str

    @classmethod
    def from_dict(cls, raw: Dict[str, object]) -> "FactorSnapshot":
        factor_id = _validate_non_empty_string(raw.get("id"), "factor.id")
        text = _validate_non_empty_string(raw.get("text"), "factor.text")
        kind = _validate_kind(raw.get("kind"))
        weight = _validate_grade(raw.get("weight"), "factor.weight")
        direction = _validate_direction(raw.get("direction"))
        return cls(id=factor_id, text=text, kind=kind, weight=weight, direction=direction)

    def to_dict(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "text": self.text,
            "kind": self.kind,
            "weight": self.weight,
            "direction": self.direction,
        }


@dataclass(frozen=True)
class ActorSnapshot:
    actor: str
    actor_weight: int
    factors: Sequence[FactorSnapshot]

    @classmethod
    def from_dict(cls, raw: Dict[str, object]) -> "ActorSnapshot":
        actor = _validate_non_empty_string(raw.get("actor"), "actor")
        actor_weight = _validate_grade(raw.get("actor_weight"), "actor_weight")
        factors = tuple(FactorSnapshot.from_dict(item) for item in raw.get("factors", []))
        if not factors:
            raise ValueError(f"actor {actor!r} must contain at least one factor")

        factor_ids = [factor.id for factor in factors]
        if len(factor_ids) != len(set(factor_ids)):
            raise ValueError(f"factor ids must be unique within actor {actor!r}")

        return cls(actor=actor, actor_weight=actor_weight, factors=factors)

    def to_dict(self) -> Dict[str, object]:
        return {
            "actor": self.actor,
            "actor_weight": self.actor_weight,
            "factors": [factor.to_dict() for factor in self.factors],
        }


@dataclass(frozen=True)
class Snapshot:
    as_of: datetime
    source_notes: Sequence[str]
    actors: Sequence[ActorSnapshot]

    @classmethod
    def from_dict(cls, raw: Dict[str, object]) -> "Snapshot":
        as_of = _parse_as_of(raw.get("as_of"))
        source_notes = tuple(_validate_non_empty_string(item, "source_notes[]") for item in raw.get("source_notes", []))
        if not source_notes:
            raise ValueError("source_notes must contain at least one note id")

        actors = tuple(ActorSnapshot.from_dict(item) for item in raw.get("actors", []))
        if not actors:
            raise ValueError("actors must contain at least one actor snapshot")

        actor_names = [actor.actor for actor in actors]
        if len(actor_names) != len(set(actor_names)):
            raise ValueError("actor names must be unique within a snapshot")

        return cls(as_of=as_of, source_notes=source_notes, actors=actors)

    def to_dict(self) -> Dict[str, object]:
        return {
            "as_of": self.as_of.isoformat(),
            "source_notes": list(self.source_notes),
            "actors": [actor.to_dict() for actor in self.actors],
        }


class SnapshotStore:
    def __init__(self, state_dir: Path, note_dir: Path | None = None):
        self.state_dir = Path(state_dir)
        self.snapshots_dir = self.state_dir / "snapshots"
        self.current_path = self.state_dir / "current.yaml"
        self.note_dir = None if note_dir is None else Path(note_dir)

    def save(self, snapshot: Snapshot) -> Path:
        self._validate_source_notes(snapshot)
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        target_path = self.snapshots_dir / _snapshot_filename(snapshot.as_of)
        dump_yaml(target_path, snapshot.to_dict())

        current_snapshot = self.load_current() if self.current_path.exists() else None
        if current_snapshot is None or snapshot.as_of >= current_snapshot.as_of:
            dump_yaml(self.current_path, snapshot.to_dict())
        return target_path

    def load_current(self) -> Snapshot:
        if self.current_path.exists():
            return load_snapshot(self.current_path)

        snapshots = list(self.iter_snapshots())
        if not snapshots:
            raise LookupError("no snapshots available")
        return snapshots[-1]

    def get_snapshot(self, as_of: datetime) -> Snapshot:
        _require_timezone(as_of, "query as_of")
        candidates = [snapshot for snapshot in self.iter_snapshots() if snapshot.as_of <= as_of]
        if not candidates:
            raise LookupError(f"no snapshot exists at or before {as_of.isoformat()}")
        return candidates[-1]

    def iter_snapshots(self) -> Iterable[Snapshot]:
        if not self.snapshots_dir.exists():
            return iter(())

        snapshots = [
            load_snapshot(path)
            for path in sorted(self.snapshots_dir.glob("*.yaml"))
        ]
        snapshots.sort(key=lambda snapshot: snapshot.as_of)
        return iter(snapshots)

    def _validate_source_notes(self, snapshot: Snapshot) -> None:
        if self.note_dir is None:
            return

        note_store = _load_note_store(self.note_dir)
        for note_id in snapshot.source_notes:
            try:
                note = note_store.get(note_id)
            except LookupError as exc:
                raise LookupError(f"source note {note_id!r} does not exist") from exc
            if note.created_at > snapshot.as_of:
                raise ValueError(
                    f"source note {note_id!r} created_at {note.created_at.isoformat()} "
                    f"is later than snapshot as_of {snapshot.as_of.isoformat()}"
                )


def export_legacy_scenario(snapshot: Snapshot, name: str | None = None) -> Dict[str, object]:
    scenario_name = name or f"snapshot-{snapshot.as_of.isoformat()}"
    return {
        "name": scenario_name,
        "actor_profiles": [
            {
                "actor": actor.actor,
                "actor_weight": _grade_to_legacy_weight(actor.actor_weight),
                "factors": [
                    {
                        "name": factor.text,
                        "weight": _grade_to_legacy_weight(factor.weight),
                        "direction": factor.direction,
                    }
                    for factor in actor.factors
                ],
            }
            for actor in snapshot.actors
        ],
    }


def load_snapshot(path: Path) -> Snapshot:
    return Snapshot.from_dict(load_yaml(path))


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


def _validate_non_empty_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _validate_kind(value: object) -> str:
    kind = _validate_non_empty_string(value, "factor.kind")
    if kind not in VALID_KINDS:
        raise ValueError(f"factor.kind must be one of {list(VALID_KINDS)}")
    return kind


def _validate_grade(value: object, label: str) -> int:
    if not isinstance(value, int) or not GRADE_MIN <= value <= GRADE_MAX:
        raise ValueError(f"{label} must be an integer between {GRADE_MIN} and {GRADE_MAX}")
    return value


def _validate_direction(value: object) -> str:
    direction = _validate_non_empty_string(value, "factor.direction")
    if direction not in VALID_DIRECTIONS:
        raise ValueError(f"factor.direction must be one of {list(VALID_DIRECTIONS)}")
    return direction


def _parse_as_of(value: object) -> datetime:
    as_of_text = _validate_non_empty_string(value, "as_of")
    try:
        parsed = datetime.fromisoformat(as_of_text)
    except ValueError as exc:
        raise ValueError("as_of must be a valid ISO 8601 datetime string") from exc
    _require_timezone(parsed, "as_of")
    return parsed


def _require_timezone(value: datetime, label: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must include timezone information")


def _snapshot_filename(as_of: datetime) -> str:
    return f"{as_of.strftime('%Y-%m-%dT%H-%M-%S%z')}.yaml"


def _grade_to_legacy_weight(value: int) -> int:
    return value * LEGACY_SCALE


def _load_note_store(note_dir: Path):
    module = _load_note_service_module()
    return module.NoteStore(note_dir)


def _load_note_service_module():
    global _NOTE_SERVICE_MODULE
    if _NOTE_SERVICE_MODULE is not None:
        return _NOTE_SERVICE_MODULE

    spec = importlib.util.spec_from_file_location("middle_east_war_note_service", NOTE_SERVICE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load note service from {NOTE_SERVICE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    _NOTE_SERVICE_MODULE = module
    return module


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Middle East war snapshot store")
    subparsers = parser.add_subparsers(dest="command", required=True)
    state_dir_parent = argparse.ArgumentParser(add_help=False)
    state_dir_parent.add_argument(
        "--state-dir",
        default=Path(__file__).resolve().parent / "state",
        type=Path,
        help="Directory that contains snapshots/ and current.yaml",
    )
    state_dir_parent.add_argument(
        "--note-dir",
        default=Path(__file__).resolve().parent.parent / "middle-east-war-note" / "notes",
        type=Path,
        help="Directory that stores note yaml files for source_notes validation",
    )

    save_parser = subparsers.add_parser(
        "put",
        parents=[state_dir_parent],
        help="Validate and store a snapshot YAML file",
    )
    save_parser.add_argument("input", type=Path, help="Path to a snapshot YAML file")

    get_parser = subparsers.add_parser(
        "get",
        parents=[state_dir_parent],
        help="Read the latest snapshot at or before as_of",
    )
    get_parser.add_argument("--as-of", type=str, help="ISO 8601 datetime. Omit to read current.yaml")

    export_parser = subparsers.add_parser(
        "export-legacy",
        parents=[state_dir_parent],
        help="Export a compatible scenario JSON payload for middle-east-war-long-term-trend",
    )
    export_parser.add_argument("--as-of", type=str, help="ISO 8601 datetime. Omit to read current.yaml")

    return parser


def _resolve_snapshot(store: SnapshotStore, as_of_text: str | None) -> Snapshot:
    if as_of_text is None:
        return store.load_current()
    return store.get_snapshot(_parse_as_of(as_of_text))


def main(argv: Sequence[str]) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv[1:])
    store = SnapshotStore(args.state_dir, note_dir=args.note_dir)

    if args.command == "put":
        saved_path = store.save(load_snapshot(args.input))
        print(saved_path)
        return 0

    snapshot = _resolve_snapshot(store, getattr(args, "as_of", None))
    if args.command == "get":
        print(json.dumps(snapshot.to_dict(), ensure_ascii=False, indent=2))
        return 0

    if args.command == "export-legacy":
        print(json.dumps(export_legacy_scenario(snapshot), ensure_ascii=False, indent=2))
        return 0

    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
