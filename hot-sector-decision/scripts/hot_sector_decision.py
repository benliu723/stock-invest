#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


LEADER_STATUS_STRONG = "强"
LEADER_STATUS_DULLING = "钝化"
LEADER_STATUS_WEAK = "转弱"

DECISION_ACTIONABLE = "可做"
DECISION_WATCH = "只观察"
DECISION_ABANDON = "放弃"
DECISION_RETREAT = "撤退"


def clamp_score(value: Any) -> int:
    score = int(value)
    if score < 0:
        return 0
    if score > 100:
        return 100
    return score


def leader_composite_score(leader_stock: dict[str, Any]) -> int:
    trend_strength = clamp_score(leader_stock.get("trend_strength", 0))
    focus_strength = clamp_score(leader_stock.get("focus_strength", 0))
    pullback_quality = clamp_score(leader_stock.get("pullback_quality", 0))
    return round(trend_strength * 0.45 + focus_strength * 0.35 + pullback_quality * 0.20)


def determine_leader_status(leader_stock: dict[str, Any]) -> str:
    trend_strength = clamp_score(leader_stock.get("trend_strength", 0))
    focus_strength = clamp_score(leader_stock.get("focus_strength", 0))
    composite = leader_composite_score(leader_stock)

    if composite >= 75 and trend_strength >= 70 and focus_strength >= 70:
        return LEADER_STATUS_STRONG
    if composite >= 55 and trend_strength >= 50 and focus_strength >= 50:
        return LEADER_STATUS_DULLING
    return LEADER_STATUS_WEAK


def candidate_has_room(candidate: dict[str, Any]) -> bool:
    return clamp_score(candidate.get("position_vs_leader", 100)) <= 45


def candidate_is_extended(candidate: dict[str, Any]) -> bool:
    return (
        clamp_score(candidate.get("extension_risk", 100)) >= 70
        or clamp_score(candidate.get("position_vs_leader", 100)) >= 65
    )


def candidate_is_strong(candidate: dict[str, Any]) -> bool:
    return clamp_score(candidate.get("recent_strength", 0)) >= 75


def build_reason(leader_status: str, candidate: dict[str, Any], decision: str) -> str:
    name = candidate["name"]
    recent_strength = clamp_score(candidate.get("recent_strength", 0))
    position_vs_leader = clamp_score(candidate.get("position_vs_leader", 0))
    extension_risk = clamp_score(candidate.get("extension_risk", 0))

    if decision == DECISION_ACTIONABLE:
        return (
            f"{name} 强于板块平均，距离龙头仍有空间，且透支风险较低。"
            f" leader_status={leader_status} recent_strength={recent_strength}"
            f" position_vs_leader={position_vs_leader} extension_risk={extension_risk}"
        )
    if decision == DECISION_WATCH:
        return (
            f"{name} 暂未失去观察价值，但当前更适合等待确认。"
            f" leader_status={leader_status} recent_strength={recent_strength}"
            f" position_vs_leader={position_vs_leader} extension_risk={extension_risk}"
        )
    if decision == DECISION_RETREAT:
        return f"{name} 所属热点的龙头已转弱，优先撤退而不是继续博弈补涨。"
    return f"{name} 当前不满足补涨交易条件，继续参与的性价比较低。"


def determine_candidate_decision(
    leader_status: str,
    candidate: dict[str, Any],
) -> str:
    if leader_status == LEADER_STATUS_WEAK:
        return DECISION_RETREAT if candidate.get("in_position") else DECISION_ABANDON

    if leader_status == LEADER_STATUS_DULLING:
        return DECISION_WATCH if clamp_score(candidate.get("recent_strength", 0)) >= 60 else DECISION_ABANDON

    if candidate_is_strong(candidate) and candidate_has_room(candidate) and not candidate_is_extended(candidate):
        return DECISION_ACTIONABLE

    if clamp_score(candidate.get("recent_strength", 0)) >= 60:
        return DECISION_WATCH

    return DECISION_ABANDON


def candidate_priority(decision: str) -> int:
    priorities = {
        DECISION_ACTIONABLE: 0,
        DECISION_WATCH: 1,
        DECISION_ABANDON: 2,
        DECISION_RETREAT: 3,
    }
    return priorities[decision]


def evaluate_theme(payload: dict[str, Any]) -> dict[str, Any]:
    hot_theme = payload["hot_theme"]
    leader_stock = payload["leader_stock"]
    candidate_stocks = payload.get("candidate_stocks", [])

    leader_status = determine_leader_status(leader_stock)
    cards = []
    for candidate in candidate_stocks:
        decision = determine_candidate_decision(leader_status, candidate)
        cards.append(
            {
                "candidate": candidate["name"],
                "decision": decision,
                "reason": build_reason(leader_status, candidate, decision),
                "metrics": {
                    "recent_strength": clamp_score(candidate.get("recent_strength", 0)),
                    "position_vs_leader": clamp_score(candidate.get("position_vs_leader", 0)),
                    "extension_risk": clamp_score(candidate.get("extension_risk", 0)),
                    "in_position": bool(candidate.get("in_position", False)),
                },
            }
        )

    cards.sort(
        key=lambda card: (
            candidate_priority(card["decision"]),
            -card["metrics"]["recent_strength"],
            card["metrics"]["extension_risk"],
        )
    )

    return {
        "theme": hot_theme,
        "leader": {
            "name": leader_stock["name"],
            "status": leader_status,
            "composite_score": leader_composite_score(leader_stock),
        },
        "leader_status": leader_status,
        "cards": cards,
    }


def load_payload(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def evaluate_command(args: argparse.Namespace) -> None:
    print(json.dumps(evaluate_theme(load_payload(args.input_path)), ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate hot-theme leader and high-elasticity follower candidates.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    evaluate_parser = subparsers.add_parser("evaluate", help="evaluate one hot theme payload")
    evaluate_parser.add_argument("input_path", help="path to input JSON")
    evaluate_parser.set_defaults(func=evaluate_command)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
