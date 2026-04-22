import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


SERVICE_ROOT = Path(__file__).resolve().parents[1]
NOTE_ROOT = SERVICE_ROOT.parent / "middle-east-war-note"
sys.path.insert(0, str(SERVICE_ROOT))
sys.path.insert(0, str(NOTE_ROOT))

from note_service import NoteStore  # noqa: E402
from service import Snapshot, SnapshotStore  # noqa: E402


def make_note_payload(note_id: str, created_at: datetime):
    return {
        "id": note_id,
        "created_at": created_at.isoformat(),
        "sources": [
            {
                "type": "news",
                "title": "Reuters briefing",
                "url": "https://example.com/reuters-briefing",
                "published_at": created_at.isoformat(),
            }
        ],
        "summary": "局势继续高压运行。",
        "observations": [
            "美国强调避免失控。",
            "伊朗维持威慑。",
        ],
    }


def make_snapshot(note_ids, as_of: datetime):
    return Snapshot.from_dict(
        {
            "as_of": as_of.isoformat(),
            "source_notes": list(note_ids),
            "actors": [
                {
                    "actor": "美国",
                    "actor_weight": 4,
                    "factors": [
                        {
                            "id": "us_avoid_regional_war",
                            "text": "避免中东全面失控",
                            "kind": "core",
                            "weight": 5,
                            "direction": "僵持",
                        }
                    ],
                }
            ],
        }
    )


class SnapshotNoteValidationTest(unittest.TestCase):
    def test_save_rejects_missing_source_note(self):
        with tempfile.TemporaryDirectory() as state_dir, tempfile.TemporaryDirectory() as note_dir:
            store = SnapshotStore(Path(state_dir), note_dir=Path(note_dir))
            snapshot = make_snapshot(
                ["note-2026-04-19-01"],
                datetime(2026, 4, 19, 9, 0, tzinfo=timezone(timedelta(hours=8))),
            )

            with self.assertRaisesRegex(LookupError, "source note"):
                store.save(snapshot)

    def test_save_rejects_source_note_created_after_snapshot(self):
        with tempfile.TemporaryDirectory() as state_dir, tempfile.TemporaryDirectory() as note_dir:
            notes = NoteStore(Path(note_dir))
            note = make_note_payload(
                "note-2026-04-19-01",
                datetime(2026, 4, 19, 10, 0, tzinfo=timezone(timedelta(hours=8))),
            )
            notes.save(NoteStore.load_note(note))
            store = SnapshotStore(Path(state_dir), note_dir=Path(note_dir))
            snapshot = make_snapshot(
                ["note-2026-04-19-01"],
                datetime(2026, 4, 19, 9, 0, tzinfo=timezone(timedelta(hours=8))),
            )

            with self.assertRaisesRegex(ValueError, "created_at"):
                store.save(snapshot)


if __name__ == "__main__":
    unittest.main()
