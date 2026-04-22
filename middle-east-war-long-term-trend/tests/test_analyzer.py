import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from analyzer import Scenario, analyze_scenario  # noqa: E402


def make_actor(actor, actor_weight, factors):
    return {
        "actor": actor,
        "actor_weight": actor_weight,
        "factors": [
            {"name": name, "weight": weight, "direction": direction}
            for name, weight, direction in factors
        ],
    }


class AnalyzeScenarioTest(unittest.TestCase):
    def test_indicator_returns_one_only_for_matching_direction(self):
        scenario = Scenario.from_dict(
            {
                "name": "indicator",
                "actor_profiles": [
                    make_actor("美国", 100, [("避免失控", 80, "僵持")]),
                    make_actor("以色列", 100, [("维持威慑", 80, "升级")]),
                    make_actor("伊朗", 100, [("缓解压力", 80, "缓和")]),
                ]
            }
        )

        us_factor = scenario.actor_profiles[0].factors[0]

        self.assertEqual(us_factor.indicator("缓和"), 0)
        self.assertEqual(us_factor.indicator("僵持"), 1)
        self.assertEqual(us_factor.indicator("升级"), 0)

    def test_returns_stalemate_when_stalemate_scores_highest(self):
        scenario = Scenario.from_dict(
            {
                "name": "stalemate",
                "actor_profiles": [
                    make_actor(
                        "美国",
                        90,
                        [
                            ("避免中东全面失控", 95, "僵持"),
                            ("阻止伊朗拥核", 80, "升级"),
                        ],
                    ),
                    make_actor(
                        "以色列",
                        95,
                        [
                            ("维持长期威慑", 90, "僵持"),
                            ("压制代理人网络", 70, "升级"),
                        ],
                    ),
                    make_actor(
                        "伊朗",
                        85,
                        [
                            ("避免政权安全受损", 92, "僵持"),
                            ("保持地区威慑能力", 75, "升级"),
                        ],
                    ),
                ],
            }
        )

        result = analyze_scenario(scenario)

        self.assertEqual(result.primary_trend, "僵持")
        self.assertEqual(result.long_term_shape, "高压持久战")
        self.assertGreater(result.scores["僵持"], result.scores["缓和"])
        self.assertGreater(result.scores["僵持"], result.scores["升级"])

    def test_returns_easing_when_easing_scores_highest(self):
        scenario = Scenario.from_dict(
            {
                "name": "easing",
                "actor_profiles": [
                    make_actor(
                        "美国",
                        100,
                        [
                            ("压低地区失控风险", 95, "缓和"),
                            ("稳定能源与盟友预期", 88, "缓和"),
                        ],
                    ),
                    make_actor(
                        "以色列",
                        80,
                        [
                            ("降低多线作战压力", 90, "缓和"),
                            ("保留基本威慑", 40, "僵持"),
                        ],
                    ),
                    make_actor(
                        "伊朗",
                        75,
                        [
                            ("缓解外部压力", 93, "缓和"),
                            ("避免政权安全受损", 86, "僵持"),
                        ],
                    ),
                ],
            }
        )

        result = analyze_scenario(scenario)

        self.assertEqual(result.primary_trend, "缓和")
        self.assertEqual(result.long_term_shape, "低冲突缓和均衡")
        self.assertGreater(result.scores["缓和"], result.scores["升级"])

    def test_returns_escalation_when_high_impact_actors_point_to_escalation(self):
        scenario = Scenario.from_dict(
            {
                "name": "escalation",
                "actor_profiles": [
                    make_actor(
                        "美国",
                        95,
                        [
                            ("阻止伊朗拥核", 100, "升级"),
                            ("维护地区威慑信誉", 85, "升级"),
                        ],
                    ),
                    make_actor(
                        "以色列",
                        100,
                        [
                            ("打击伊朗核设施", 100, "升级"),
                            ("重建压制优势", 92, "升级"),
                        ],
                    ),
                    make_actor(
                        "伊朗",
                        85,
                        [
                            ("避免政权安全受损", 80, "僵持"),
                            ("保持地区威慑能力", 78, "升级"),
                        ],
                    ),
                ],
            }
        )

        result = analyze_scenario(scenario)

        self.assertEqual(result.primary_trend, "升级")
        self.assertEqual(result.long_term_shape, "失稳上行态势")
        self.assertGreater(result.scores["升级"], result.scores["僵持"])

    def test_adjusting_actor_or_factor_weight_changes_the_result(self):
        baseline = Scenario.from_dict(
            {
                "name": "baseline",
                "actor_profiles": [
                    make_actor("美国", 45, [("避免中东全面失控", 90, "僵持")]),
                    make_actor("以色列", 100, [("打击伊朗核设施", 95, "升级")]),
                    make_actor("伊朗", 40, [("避免政权安全受损", 85, "僵持")]),
                ],
            }
        )
        adjusted = Scenario.from_dict(
            {
                "name": "adjusted",
                "actor_profiles": [
                    make_actor("美国", 95, [("避免中东全面失控", 95, "僵持")]),
                    make_actor("以色列", 75, [("打击伊朗核设施", 60, "升级")]),
                    make_actor("伊朗", 80, [("避免政权安全受损", 90, "僵持")]),
                ],
            }
        )

        baseline_result = analyze_scenario(baseline)
        adjusted_result = analyze_scenario(adjusted)

        self.assertEqual(baseline_result.primary_trend, "升级")
        self.assertEqual(adjusted_result.primary_trend, "僵持")
        self.assertNotEqual(baseline_result.scores, adjusted_result.scores)


if __name__ == "__main__":
    unittest.main()
