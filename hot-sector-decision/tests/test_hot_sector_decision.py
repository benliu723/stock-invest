import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "hot_sector_decision.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "hot_sector_decision_under_test",
        MODULE_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class HotSectorDecisionTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def evaluate(self, payload):
        return self.module.evaluate_theme(payload)

    def test_marks_candidate_as_actionable_when_leader_is_strong_and_room_remains(self):
        result = self.evaluate(
            {
                "hot_theme": "机器人",
                "leader_stock": {
                    "name": "龙头A",
                    "trend_strength": 88,
                    "focus_strength": 92,
                    "pullback_quality": 80,
                },
                "candidate_stocks": [
                    {
                        "name": "补涨A",
                        "recent_strength": 82,
                        "position_vs_leader": 35,
                        "extension_risk": 20,
                    }
                ],
            }
        )

        self.assertEqual(result["leader_status"], "强")
        self.assertEqual(result["cards"][0]["decision"], "可做")

    def test_marks_extended_candidate_as_watch_only_even_if_leader_stays_strong(self):
        result = self.evaluate(
            {
                "hot_theme": "机器人",
                "leader_stock": {
                    "name": "龙头A",
                    "trend_strength": 84,
                    "focus_strength": 90,
                    "pullback_quality": 78,
                },
                "candidate_stocks": [
                    {
                        "name": "补涨A",
                        "recent_strength": 87,
                        "position_vs_leader": 72,
                        "extension_risk": 86,
                    }
                ],
            }
        )

        self.assertEqual(result["leader_status"], "强")
        self.assertEqual(result["cards"][0]["decision"], "只观察")

    def test_marks_candidates_as_retreat_when_leader_turns_weak_and_position_exists(self):
        result = self.evaluate(
            {
                "hot_theme": "机器人",
                "leader_stock": {
                    "name": "龙头A",
                    "trend_strength": 38,
                    "focus_strength": 42,
                    "pullback_quality": 35,
                },
                "candidate_stocks": [
                    {
                        "name": "补涨A",
                        "recent_strength": 91,
                        "position_vs_leader": 40,
                        "extension_risk": 45,
                        "in_position": True,
                    }
                ],
            }
        )

        self.assertEqual(result["leader_status"], "转弱")
        self.assertEqual(result["cards"][0]["decision"], "撤退")

    def test_marks_fast_rotation_theme_as_watch_only_under_dulling_leader(self):
        result = self.evaluate(
            {
                "hot_theme": "机器人",
                "leader_stock": {
                    "name": "龙头A",
                    "trend_strength": 66,
                    "focus_strength": 62,
                    "pullback_quality": 58,
                },
                "candidate_stocks": [
                    {
                        "name": "补涨A",
                        "recent_strength": 74,
                        "position_vs_leader": 44,
                        "extension_risk": 48,
                    },
                    {
                        "name": "补涨B",
                        "recent_strength": 68,
                        "position_vs_leader": 55,
                        "extension_risk": 46,
                    },
                ],
            }
        )

        self.assertEqual(result["leader_status"], "钝化")
        self.assertEqual(
            [card["decision"] for card in result["cards"]],
            ["只观察", "只观察"],
        )

    def test_allows_candidate_switch_when_new_candidate_has_better_room(self):
        result = self.evaluate(
            {
                "hot_theme": "机器人",
                "leader_stock": {
                    "name": "龙头A",
                    "trend_strength": 86,
                    "focus_strength": 88,
                    "pullback_quality": 82,
                },
                "candidate_stocks": [
                    {
                        "name": "旧补涨",
                        "recent_strength": 78,
                        "position_vs_leader": 70,
                        "extension_risk": 82,
                    },
                    {
                        "name": "新补涨",
                        "recent_strength": 76,
                        "position_vs_leader": 32,
                        "extension_risk": 28,
                    },
                ],
            }
        )

        decisions = {card["candidate"]: card["decision"] for card in result["cards"]}
        self.assertEqual(decisions["旧补涨"], "只观察")
        self.assertEqual(decisions["新补涨"], "可做")

    def test_cli_evaluate_command_prints_json_report(self):
        payload = {
            "hot_theme": "机器人",
            "leader_stock": {
                "name": "龙头A",
                "trend_strength": 88,
                "focus_strength": 90,
                "pullback_quality": 85,
            },
            "candidate_stocks": [
                {
                    "name": "补涨A",
                    "recent_strength": 84,
                    "position_vs_leader": 30,
                    "extension_risk": 24,
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tempdir:
            input_path = Path(tempdir) / "input.json"
            input_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            proc = subprocess.run(
                [sys.executable, str(MODULE_PATH), "evaluate", str(input_path)],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        report = json.loads(proc.stdout)
        self.assertEqual(report["theme"], "机器人")
        self.assertEqual(report["cards"][0]["decision"], "可做")


if __name__ == "__main__":
    unittest.main()
