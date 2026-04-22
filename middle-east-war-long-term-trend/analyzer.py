from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence


VALID_DIRECTIONS = ("缓和", "僵持", "升级")
TREND_TO_SHAPE = {
    "缓和": "低冲突缓和均衡",
    "僵持": "高压持久战",
    "升级": "失稳上行态势",
}


@dataclass(frozen=True)
class Factor:
    name: str
    weight: int
    direction: str

    @property
    def normalized_weight(self) -> float:
        return self.weight / 100

    def indicator(self, target_direction: str) -> int:
        return 1 if self.direction == target_direction else 0


@dataclass(frozen=True)
class ActorProfile:
    actor: str
    actor_weight: int
    factors: Sequence[Factor]

    @property
    def normalized_weight(self) -> float:
        return self.actor_weight / 100


@dataclass(frozen=True)
class Scenario:
    name: str
    actor_profiles: Sequence[ActorProfile]

    @classmethod
    def from_dict(cls, raw: Dict) -> "Scenario":
        actor_profiles = tuple(
            ActorProfile(
                actor=profile["actor"],
                actor_weight=_validate_weight(profile["actor_weight"], "actor_weight"),
                factors=tuple(
                    Factor(
                        name=factor["name"],
                        weight=_validate_weight(factor["weight"], "factor weight"),
                        direction=_validate_direction(factor["direction"]),
                    )
                    for factor in profile["factors"]
                ),
            )
            for profile in raw["actor_profiles"]
        )
        scenario = cls(name=raw["name"], actor_profiles=actor_profiles)
        scenario._validate_references()
        return scenario

    def _validate_references(self) -> None:
        actor_names = [profile.actor for profile in self.actor_profiles]
        if len(actor_names) != len(set(actor_names)):
            raise ValueError("actor names must be unique")

        for profile in self.actor_profiles:
            factor_names = [factor.name for factor in profile.factors]
            if len(factor_names) != len(set(factor_names)):
                raise ValueError(f"factor names must be unique within actor {profile.actor!r}")

    def actor_map(self) -> Dict[str, ActorProfile]:
        return {profile.actor: profile for profile in self.actor_profiles}


@dataclass(frozen=True)
class TrendResult:
    primary_trend: str
    long_term_shape: str
    drivers: Sequence[str]
    reversal_conditions: Sequence[str]
    scores: Dict[str, float]


def _validate_weight(value: int, label: str) -> int:
    if not isinstance(value, int) or not 0 <= value <= 100:
        raise ValueError(f"{label} must be an integer between 0 and 100")
    return value


def _validate_direction(direction: str) -> str:
    if direction not in VALID_DIRECTIONS:
        raise ValueError(f"direction must be one of {list(VALID_DIRECTIONS)}")
    return direction


def load_scenario(path: Path) -> Scenario:
    with path.open("r", encoding="utf-8") as handle:
        return Scenario.from_dict(json.load(handle))


def analyze_scenario(scenario: Scenario) -> TrendResult:
    contributions = []
    for profile in scenario.actor_profiles:
        for factor in profile.factors:
            contribution = round(profile.normalized_weight * factor.normalized_weight, 4)
            contributions.append(
                {
                    "actor": profile.actor,
                    "actor_weight": profile.actor_weight,
                    "factor": factor.name,
                    "factor_weight": factor.weight,
                    "direction": factor.direction,
                    "contribution": contribution,
                }
            )

    scores = {
        direction: round(
            sum(
                item["contribution"] * _indicator(item["direction"], direction)
                for item in contributions
            ),
            4,
        )
        for direction in VALID_DIRECTIONS
    }
    primary_trend = _select_primary_trend(scores)

    return TrendResult(
        primary_trend=primary_trend,
        long_term_shape=TREND_TO_SHAPE[primary_trend],
        drivers=_build_drivers(contributions, primary_trend),
        reversal_conditions=_build_reversal_conditions(contributions, scores, primary_trend),
        scores=scores,
    )


def _indicator(current_direction: str, target_direction: str) -> int:
    return 1 if current_direction == target_direction else 0


def _select_primary_trend(scores: Dict[str, float]) -> str:
    return max(VALID_DIRECTIONS, key=lambda direction: (scores[direction], -VALID_DIRECTIONS.index(direction)))


def _build_drivers(contributions: Sequence[Dict[str, object]], primary_trend: str) -> List[str]:
    winning_contributions = [
        item for item in contributions if item["direction"] == primary_trend
    ]
    winning_contributions.sort(key=lambda item: item["contribution"], reverse=True)

    drivers = []
    for item in winning_contributions[:4]:
        drivers.append(
            f"{item['actor']}的因素“{item['factor']}”指向{primary_trend}，"
            f"AW={item['actor_weight']}/100，FW={item['factor_weight']}/100，"
            f"贡献值为{item['contribution']:.4f}。"
        )
    return drivers


def _build_reversal_conditions(
    contributions: Sequence[Dict[str, object]],
    scores: Dict[str, float],
    primary_trend: str,
) -> List[str]:
    ordered_directions = sorted(VALID_DIRECTIONS, key=lambda direction: scores[direction], reverse=True)
    runner_up = ordered_directions[1]
    margin = round(scores[primary_trend] - scores[runner_up], 4)

    primary_items = sorted(
        [item for item in contributions if item["direction"] == primary_trend],
        key=lambda item: item["contribution"],
        reverse=True,
    )
    runner_up_items = sorted(
        [item for item in contributions if item["direction"] == runner_up],
        key=lambda item: item["contribution"],
        reverse=True,
    )

    conditions = [
        f"若当前{primary_trend}方向总分 S({primary_trend}) 的领先优势 {margin:.4f} 被削弱，长期主趋势需要重新评估。",
    ]
    if primary_items:
        top_primary = primary_items[0]
        conditions.append(
            f"若{top_primary['actor']}的因素“{top_primary['factor']}”对应的 AW 或 FW 下调，"
            f"S({primary_trend}) 将下降。"
        )
    if runner_up_items:
        top_runner_up = runner_up_items[0]
        conditions.append(
            f"若{top_runner_up['actor']}的因素“{top_runner_up['factor']}”对应的 AW 或 FW 上调，"
            f"S({runner_up}) 可能反超 S({primary_trend})。"
        )
    return conditions


def result_to_dict(result: TrendResult) -> Dict[str, object]:
    return {
        "长期主趋势": result.primary_trend,
        "长期形态": result.long_term_shape,
        "趋势形成原因": list(result.drivers),
        "改判条件": list(result.reversal_conditions),
        "方向总分": dict(result.scores),
    }


def main(argv: Sequence[str]) -> int:
    if len(argv) != 2:
        print("Usage: python3 analyzer.py <scenario.json>", file=sys.stderr)
        return 1

    scenario = load_scenario(Path(argv[1]))
    result = analyze_scenario(scenario)
    print(json.dumps(result_to_dict(result), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
