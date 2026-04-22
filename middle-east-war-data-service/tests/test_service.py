import importlib.util
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parent
sys.path.insert(0, str(SERVICE_ROOT))

from service import Snapshot, SnapshotStore, export_legacy_scenario  # noqa: E402


def load_legacy_analyzer():
    analyzer_path = REPO_ROOT / "middle-east-war-long-term-trend" / "analyzer.py"
    spec = importlib.util.spec_from_file_location("legacy_analyzer", analyzer_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def make_snapshot(as_of: datetime, actor_weight: int = 4, factor_weight: int = 5):
    return Snapshot.from_dict(
        {
            "as_of": as_of.isoformat(),
            "source_notes": [
                "note-2026-04-19-01",
                "note-2026-04-19-02",
            ],
            "actors": [
                {
                    "actor": "美国",
                    "actor_weight": actor_weight,
                    "factors": [
                        {
                            "id": "us_avoid_regional_war",
                            "text": "避免中东全面失控",
                            "kind": "core",
                            "weight": factor_weight,
                            "direction": "僵持",
                        },
                        {
                            "id": "us_prevent_iran_nuclear",
                            "text": "阻止伊朗拥核",
                            "kind": "stage",
                            "weight": 3,
                            "direction": "升级",
                        },
                    ],
                },
                {
                    "actor": "伊朗",
                    "actor_weight": 3,
                    "factors": [
                        {
                            "id": "iran_preserve_regime_security",
                            "text": "避免政权安全受损",
                            "kind": "core",
                            "weight": 5,
                            "direction": "僵持",
                        }
                    ],
                },
            ],
        }
    )


class SnapshotStoreTest(unittest.TestCase):
    def test_save_snapshot_round_trips_and_updates_current(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SnapshotStore(Path(temp_dir))
            snapshot = make_snapshot(datetime(2026, 4, 19, 9, 0, tzinfo=timezone(timedelta(hours=8))))

            saved_path = store.save(snapshot)
            loaded = store.load_current()

            self.assertTrue(saved_path.exists())
            self.assertEqual(saved_path.suffix, ".yaml")
            self.assertEqual(loaded.to_dict(), snapshot.to_dict())
            self.assertEqual(
                store.current_path.read_text(encoding="utf-8"),
                saved_path.read_text(encoding="utf-8"),
            )

    def test_query_returns_latest_snapshot_not_after_target(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SnapshotStore(Path(temp_dir))
            earlier = make_snapshot(datetime(2026, 4, 19, 9, 0, tzinfo=timezone.utc), actor_weight=2)
            later = make_snapshot(datetime(2026, 4, 19, 16, 0, tzinfo=timezone.utc), actor_weight=5)
            store.save(earlier)
            store.save(later)

            found = store.get_snapshot(datetime(2026, 4, 19, 12, 0, tzinfo=timezone.utc))

            self.assertEqual(found.as_of, earlier.as_of)
            self.assertEqual(found.actors[0].actor_weight, 2)

    def test_query_raises_when_target_is_before_first_snapshot(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SnapshotStore(Path(temp_dir))
            store.save(make_snapshot(datetime(2026, 4, 19, 9, 0, tzinfo=timezone.utc)))

            with self.assertRaises(LookupError):
                store.get_snapshot(datetime(2026, 4, 18, 23, 0, tzinfo=timezone.utc))


class LegacyCompatibilityTest(unittest.TestCase):
    def test_export_legacy_scenario_maps_grades_to_percent_scale(self):
        snapshot = make_snapshot(
            datetime(2026, 4, 19, 9, 0, tzinfo=timezone(timedelta(hours=8))),
            actor_weight=4,
            factor_weight=5,
        )

        legacy = export_legacy_scenario(snapshot)

        self.assertEqual(legacy["name"], "snapshot-2026-04-19T09:00:00+08:00")
        self.assertEqual(legacy["actor_profiles"][0]["actor_weight"], 80)
        self.assertEqual(legacy["actor_profiles"][0]["factors"][0]["name"], "避免中东全面失控")
        self.assertEqual(legacy["actor_profiles"][0]["factors"][0]["weight"], 100)
        self.assertEqual(legacy["actor_profiles"][0]["factors"][0]["direction"], "僵持")

    def test_exported_scenario_can_be_consumed_by_existing_analyzer(self):
        snapshot = make_snapshot(datetime(2026, 4, 19, 9, 0, tzinfo=timezone.utc))
        legacy_analyzer = load_legacy_analyzer()

        scenario = legacy_analyzer.Scenario.from_dict(export_legacy_scenario(snapshot))
        result = legacy_analyzer.analyze_scenario(scenario)

        self.assertEqual(result.primary_trend, "僵持")
        self.assertGreater(result.scores["僵持"], result.scores["升级"])


if __name__ == "__main__":
    unittest.main()
