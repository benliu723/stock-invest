#!/usr/bin/env python3

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch


SKILL_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = SKILL_ROOT / "scripts" / "stock_pools.py"
EVALS_PATH = SKILL_ROOT / "evals" / "evals.json"
DEFAULT_WORKSPACE_ROOT = SKILL_ROOT.parent / "stock-pool-workspace"
DEFAULT_POOL_NAME = "默认股票池"

TICKER_MAP = {
    "上能电气": "300827",
    "隆基绿能": "601012",
    "通威股份": "600438",
    "宁德时代": "300750",
    "亿纬锂能": "300014",
    "金风科技": "002202",
}

EVAL_NAMES = {
    1: "create-pool",
    2: "add-stock-to-existing-pool",
    3: "create-second-pool",
    4: "show-all-stocks",
    5: "delete-pool",
    6: "rename-pool",
    7: "show-pool-members",
    8: "follow-default-pool",
    9: "unfollow-selection-required",
    10: "follow-auto-create-pool",
    11: "stock-pool-synonym-create",
    12: "unfollow-with-pool-aliases",
}


def load_module():
    spec = importlib.util.spec_from_file_location("stock_pools_benchmark", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_evals() -> list[dict[str, Any]]:
    payload = json.loads(EVALS_PATH.read_text(encoding="utf-8"))
    return payload["evals"]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_state(pools: dict[str, list[str]]) -> dict[str, Any]:
    state_pools = {
        DEFAULT_POOL_NAME: {
            "name": DEFAULT_POOL_NAME,
            "is_default": True,
            "members": list(pools.get(DEFAULT_POOL_NAME, [])),
        }
    }
    for pool_name, members in pools.items():
        if pool_name == DEFAULT_POOL_NAME:
            continue
        state_pools[pool_name] = {
            "name": pool_name,
            "is_default": False,
            "members": list(members),
        }
    return {"pools": state_pools}


def initial_state_for_eval(eval_id: int) -> dict[str, Any]:
    if eval_id == 1:
        return make_state({})
    if eval_id == 2:
        return make_state({"储能": []})
    if eval_id == 3:
        return make_state({"储能": []})
    if eval_id == 4:
        return make_state({"储能": ["300827"], "光伏": ["601012"]})
    if eval_id == 5:
        return make_state({"储能": ["300827"]})
    if eval_id == 6:
        return make_state({"储能": ["300827"]})
    if eval_id == 7:
        return make_state({"储能": ["300827", "601012"]})
    if eval_id == 8:
        return make_state({})
    if eval_id == 9:
        return make_state({"储能": ["300827"], DEFAULT_POOL_NAME: ["300827"]})
    if eval_id == 10:
        return make_state({})
    if eval_id == 11:
        return make_state({})
    if eval_id == 12:
        return make_state({"储能": ["300827"], DEFAULT_POOL_NAME: ["300827"]})
    raise ValueError(f"Unsupported eval id: {eval_id}")


def lookup_ticker_stub(query: str) -> str | None:
    if isinstance(query, str) and query.isdigit() and len(query) == 6:
        return query
    return TICKER_MAP.get(query)


def run_text_command(module, prompt: str) -> dict[str, Any]:
    args = argparse.Namespace(text=prompt, pools=None)
    buf = io.StringIO()
    with patch.object(module, "lookup_ticker_id", side_effect=lookup_ticker_stub):
        with contextlib.redirect_stdout(buf):
            module.text_command(args)
    return json.loads(buf.getvalue())


def check(text: str, passed: bool, evidence_ok: str, evidence_fail: str) -> dict[str, Any]:
    return {
        "text": text,
        "passed": passed,
        "evidence": evidence_ok if passed else evidence_fail,
    }


def grade_eval(eval_id: int, eval_case: dict[str, Any], result: dict[str, Any], state_before: dict[str, Any], state_after: dict[str, Any]) -> list[dict[str, Any]]:
    expectations = eval_case["expectations"]

    if eval_id == 1:
        return [
            check(expectations[0], result.get("ok") and result.get("action") == "create_pool", f"Result action={result.get('action')} ok={result.get('ok')}.", f"Expected create_pool success, got action={result.get('action')} ok={result.get('ok')}."),
            check(expectations[1], result.get("pool_name") == "储能", f"Result pool_name={result.get('pool_name')}.", f"Expected pool_name=储能, got {result.get('pool_name')}."),
            check(expectations[2], DEFAULT_POOL_NAME in state_after["pools"], f"State keys include {DEFAULT_POOL_NAME}.", f"State keys are {list(state_after['pools'].keys())}."),
            check(expectations[3], state_after["pools"].get("储能", {}).get("members") == [], f"State members for 储能 are {state_after['pools'].get('储能', {}).get('members')}.", f"Expected empty members for 储能, got {state_after['pools'].get('储能', {}).get('members')}."),
        ]
    if eval_id == 2:
        return [
            check(expectations[0], result.get("ok") and result.get("action") == "add_stock", f"Result action={result.get('action')} ok={result.get('ok')}.", f"Expected add_stock success, got action={result.get('action')} ok={result.get('ok')}."),
            check(expectations[1], result.get("stock_name") == "上能电气" and result.get("tickid") == "300827", f"Result stock_name={result.get('stock_name')} tickid={result.get('tickid')}.", f"Expected stock_name=上能电气 and tickid=300827, got stock_name={result.get('stock_name')} tickid={result.get('tickid')}."),
            check(expectations[2], state_after["pools"].get("储能", {}).get("members") == ["300827"], f"State members for 储能 are {state_after['pools'].get('储能', {}).get('members')}.", f"Expected 储能 members ['300827'], got {state_after['pools'].get('储能', {}).get('members')}."),
            check(expectations[3], DEFAULT_POOL_NAME in state_after["pools"], f"State keys include {DEFAULT_POOL_NAME}.", f"State keys are {list(state_after['pools'].keys())}."),
        ]
    if eval_id == 3:
        return [
            check(expectations[0], result.get("ok") and result.get("action") == "create_pool", f"Result action={result.get('action')} ok={result.get('ok')}.", f"Expected create_pool success, got action={result.get('action')} ok={result.get('ok')}."),
            check(expectations[1], result.get("pool_name") == "光伏", f"Result pool_name={result.get('pool_name')}.", f"Expected pool_name=光伏, got {result.get('pool_name')}."),
            check(expectations[2], "储能" in state_after["pools"], "State retains pool 储能.", f"State keys are {list(state_after['pools'].keys())}."),
            check(expectations[3], state_after["pools"].get("光伏", {}).get("members") == [], f"State members for 光伏 are {state_after['pools'].get('光伏', {}).get('members')}.", f"Expected empty members for 光伏, got {state_after['pools'].get('光伏', {}).get('members')}."),
        ]
    if eval_id == 4:
        all_stocks = result.get("all_stocks", [])
        return [
            check(expectations[0], result.get("ok") and result.get("action") == "show_all_stocks", f"Result action={result.get('action')} ok={result.get('ok')}.", f"Expected show_all_stocks success, got action={result.get('action')} ok={result.get('ok')}."),
            check(expectations[1], "储能" in result.get("pools", {}) and "光伏" in result.get("pools", {}), f"Grouped pools keys are {list(result.get('pools', {}).keys())}.", f"Expected grouped pools to include 储能 and 光伏, got {list(result.get('pools', {}).keys())}."),
            check(expectations[2], sorted(all_stocks) == ["300827", "601012"], f"all_stocks={all_stocks}.", f"Expected deduplicated all_stocks ['300827', '601012'], got {all_stocks}."),
            check(expectations[3], result.get("default_pool_name") == DEFAULT_POOL_NAME, f"default_pool_name={result.get('default_pool_name')}.", f"Expected default_pool_name={DEFAULT_POOL_NAME}, got {result.get('default_pool_name')}."),
        ]
    if eval_id == 5:
        return [
            check(expectations[0], result.get("ok") and result.get("action") == "delete_pool", f"Result action={result.get('action')} ok={result.get('ok')}.", f"Expected delete_pool success, got action={result.get('action')} ok={result.get('ok')}."),
            check(expectations[1], result.get("pool_name") == "储能", f"Result pool_name={result.get('pool_name')}.", f"Expected deleted pool 储能, got {result.get('pool_name')}."),
            check(expectations[2], "储能" not in state_after["pools"], f"State keys are {list(state_after['pools'].keys())}.", f"Pool 储能 still present in state keys {list(state_after['pools'].keys())}."),
            check(expectations[3], DEFAULT_POOL_NAME in state_after["pools"], f"State retains {DEFAULT_POOL_NAME}.", f"State keys are {list(state_after['pools'].keys())}."),
        ]
    if eval_id == 6:
        return [
            check(expectations[0], result.get("ok") and result.get("action") == "rename_pool", f"Result action={result.get('action')} ok={result.get('ok')}.", f"Expected rename_pool success, got action={result.get('action')} ok={result.get('ok')}."),
            check(expectations[1], result.get("pool_name") == "储能" and result.get("new_pool_name") == "储能-2", f"Result pool_name={result.get('pool_name')} new_pool_name={result.get('new_pool_name')}.", f"Expected rename 储能 -> 储能-2, got {result.get('pool_name')} -> {result.get('new_pool_name')}."),
            check(expectations[2], "储能" not in state_after["pools"], f"State keys are {list(state_after['pools'].keys())}.", f"Pool 储能 still present in state keys {list(state_after['pools'].keys())}."),
            check(expectations[3], state_after["pools"].get("储能-2", {}).get("members") == ["300827"], f"State members for 储能-2 are {state_after['pools'].get('储能-2', {}).get('members')}.", f"Expected 储能-2 members ['300827'], got {state_after['pools'].get('储能-2', {}).get('members')}."),
        ]
    if eval_id == 7:
        return [
            check(expectations[0], result.get("ok") and result.get("action") == "show_pool", f"Result action={result.get('action')} ok={result.get('ok')}.", f"Expected show_pool success, got action={result.get('action')} ok={result.get('ok')}."),
            check(expectations[1], result.get("pool_name") == "储能", f"Result pool_name={result.get('pool_name')}.", f"Expected pool_name=储能, got {result.get('pool_name')}."),
            check(expectations[2], result.get("pool", {}).get("members") == state_before["pools"]["储能"]["members"], f"Returned members={result.get('pool', {}).get('members')} and persisted members={state_before['pools']['储能']['members']}.", f"Expected returned members {state_before['pools']['储能']['members']}, got {result.get('pool', {}).get('members')}."),
        ]
    if eval_id == 8:
        return [
            check(expectations[0], result.get("ok") and result.get("action") == "follow_stock", f"Result action={result.get('action')} ok={result.get('ok')}.", f"Expected follow_stock success, got action={result.get('action')} ok={result.get('ok')}."),
            check(expectations[1], result.get("used_default_pool") is True and result.get("selected_pools") == [DEFAULT_POOL_NAME], f"used_default_pool={result.get('used_default_pool')} selected_pools={result.get('selected_pools')}.", f"Expected default-only selection, got used_default_pool={result.get('used_default_pool')} selected_pools={result.get('selected_pools')}."),
            check(expectations[2], result.get("ticker_id") == "300827", f"ticker_id={result.get('ticker_id')}.", f"Expected ticker_id=300827, got {result.get('ticker_id')}."),
            check(expectations[3], state_after["pools"][DEFAULT_POOL_NAME]["members"] == ["300827"], f"Default pool members are {state_after['pools'][DEFAULT_POOL_NAME]['members']}.", f"Expected default pool members ['300827'], got {state_after['pools'][DEFAULT_POOL_NAME]['members']}."),
        ]
    if eval_id == 9:
        return [
            check(expectations[0], result.get("ok") and result.get("action") == "unfollow_stock", f"Result action={result.get('action')} ok={result.get('ok')}.", f"Expected unfollow_stock selection payload, got action={result.get('action')} ok={result.get('ok')}."),
            check(expectations[1], result.get("selection_required") is True, f"selection_required={result.get('selection_required')}.", f"Expected selection_required=true, got {result.get('selection_required')}."),
            check(expectations[2], DEFAULT_POOL_NAME in result.get("available_pools", []), f"available_pools={result.get('available_pools')}.", f"Expected available_pools to include {DEFAULT_POOL_NAME}, got {result.get('available_pools')}."),
            check(expectations[3], state_after == state_before, "Persisted state is unchanged before pool selection.", "State changed even though no pool selection was provided."),
        ]
    if eval_id == 10:
        return [
            check(expectations[0], result.get("ok") and result.get("action") == "follow_stock", f"Result action={result.get('action')} ok={result.get('ok')}.", f"Expected follow_stock success, got action={result.get('action')} ok={result.get('ok')}."),
            check(expectations[1], result.get("selected_pools") == [DEFAULT_POOL_NAME, "储能"], f"selected_pools={result.get('selected_pools')}.", f"Expected selected_pools ['{DEFAULT_POOL_NAME}', '储能'], got {result.get('selected_pools')}."),
            check(expectations[2], result.get("created_pools") == ["储能"], f"created_pools={result.get('created_pools')}.", f"Expected created_pools ['储能'], got {result.get('created_pools')}."),
            check(expectations[3], state_after["pools"][DEFAULT_POOL_NAME]["members"] == ["300827"] and state_after["pools"]["储能"]["members"] == ["300827"], f"Default members={state_after['pools'][DEFAULT_POOL_NAME]['members']}, 储能 members={state_after['pools']['储能']['members']}.", f"Expected both pools to contain 300827, got default={state_after['pools'][DEFAULT_POOL_NAME]['members']} 储能={state_after['pools'].get('储能', {}).get('members')}."),
        ]
    if eval_id == 11:
        return [
            check(expectations[0], result.get("action") == "create_pool", f"Result action={result.get('action')}.", f"Expected action=create_pool, got {result.get('action')}."),
            check(expectations[1], result.get("ok") is True and result.get("pool_name") == "储能", f"ok={result.get('ok')} pool_name={result.get('pool_name')}.", f"Expected ok=true and pool_name=储能, got ok={result.get('ok')} pool_name={result.get('pool_name')}."),
            check(expectations[2], state_after["pools"].get("储能", {}).get("members") == [], f"State members for 储能 are {state_after['pools'].get('储能', {}).get('members')}.", f"Expected empty members for 储能, got {state_after['pools'].get('储能', {}).get('members')}."),
        ]
    if eval_id == 12:
        return [
            check(expectations[0], result.get("ok") and result.get("action") == "unfollow_stock", f"Result action={result.get('action')} ok={result.get('ok')}.", f"Expected unfollow_stock success, got action={result.get('action')} ok={result.get('ok')}."),
            check(expectations[1], result.get("selected_pools") == [DEFAULT_POOL_NAME, "储能"], f"selected_pools={result.get('selected_pools')}.", f"Expected resolved selected_pools ['{DEFAULT_POOL_NAME}', '储能'], got {result.get('selected_pools')}."),
            check(expectations[2], result.get("ticker_id") == "300827", f"ticker_id={result.get('ticker_id')}.", f"Expected ticker_id=300827, got {result.get('ticker_id')}."),
            check(expectations[3], state_after["pools"][DEFAULT_POOL_NAME]["members"] == [] and state_after["pools"]["储能"]["members"] == [], f"Default members={state_after['pools'][DEFAULT_POOL_NAME]['members']}, 储能 members={state_after['pools']['储能']['members']}.", f"Expected both pools to be emptied, got default={state_after['pools'][DEFAULT_POOL_NAME]['members']} 储能={state_after['pools']['储能']['members']}."),
        ]
    raise ValueError(f"Unsupported eval id: {eval_id}")


def build_transcript(prompt: str, result: dict[str, Any]) -> str:
    return (
        "# Functional Benchmark Transcript\n\n"
        "## Eval Prompt\n\n"
        f"{prompt}\n\n"
        "## Execution\n\n"
        "Executed `text-command` against a temporary state file with ticker lookup stubbed for benchmark determinism.\n\n"
        "## Result\n\n"
        "```json\n"
        f"{json.dumps(result, ensure_ascii=False, indent=2)}\n"
        "```\n"
    )


def run_single_eval(eval_case: dict[str, Any], workspace: Path, run_number: int) -> None:
    eval_id = eval_case["id"]
    eval_dir = workspace / f"eval-{eval_id}"
    run_dir = eval_dir / "with_skill" / f"run-{run_number}"
    outputs_dir = run_dir / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    write_json(
        eval_dir / "eval_metadata.json",
        {
            "eval_id": eval_id,
            "eval_name": EVAL_NAMES[eval_id],
            "prompt": eval_case["prompt"],
            "expectations": eval_case["expectations"],
        },
    )

    module = load_module()
    state_path = run_dir / "state.json"
    module.STATE_PATH = state_path
    module._AKSHARE_CODE_NAME_MAP = None

    state_before = initial_state_for_eval(eval_id)
    module.save_state(state_before)
    start = time.perf_counter()
    result = run_text_command(module, eval_case["prompt"])
    duration = time.perf_counter() - start
    state_after = json.loads(state_path.read_text(encoding="utf-8"))

    transcript = build_transcript(eval_case["prompt"], result)
    outputs = {
        "result.json": result,
        "state_before.json": state_before,
        "state_after.json": state_after,
    }
    for filename, payload in outputs.items():
        write_json(outputs_dir / filename, payload)
    (run_dir / "transcript.md").write_text(transcript, encoding="utf-8")

    metrics = {
        "tool_calls": {"LocalFunction": 1},
        "total_tool_calls": 1,
        "total_steps": 1,
        "files_created": sorted(outputs.keys()),
        "errors_encountered": 0 if result.get("ok", False) else 1,
        "output_chars": sum(len(json.dumps(payload, ensure_ascii=False)) for payload in outputs.values()),
        "transcript_chars": len(transcript),
    }
    write_json(outputs_dir / "metrics.json", metrics)

    graded_expectations = grade_eval(eval_id, eval_case, result, state_before, state_after)
    passed = sum(1 for item in graded_expectations if item["passed"])
    total = len(graded_expectations)
    grading = {
        "expectations": graded_expectations,
        "summary": {
            "passed": passed,
            "failed": total - passed,
            "total": total,
            "pass_rate": round(passed / total, 4) if total else 0.0,
        },
        "execution_metrics": metrics,
        "timing": {
            "executor_duration_seconds": round(duration, 4),
            "total_duration_seconds": round(duration, 4),
        },
        "claims": [],
        "user_notes_summary": {
            "uncertainties": [],
            "needs_review": [],
            "workarounds": ["Ticker lookup is stubbed for benchmark determinism."],
        },
        "eval_feedback": {
            "suggestions": [],
            "overall": "No suggestions, evals are aligned with the current deterministic benchmark harness.",
        },
    }
    write_json(run_dir / "grading.json", grading)
    write_json(
        run_dir / "timing.json",
        {
            "total_tokens": 0,
            "duration_ms": round(duration * 1000, 2),
            "total_duration_seconds": round(duration, 4),
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a deterministic functional benchmark for stock-pool.")
    parser.add_argument("--workspace", type=Path, default=None, help="Workspace directory for benchmark artifacts.")
    parser.add_argument("--runs", type=int, default=3, help="Number of deterministic runs per eval.")
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    workspace = args.workspace or (DEFAULT_WORKSPACE_ROOT / f"functional-{timestamp}")
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True, exist_ok=True)

    evals = load_evals()
    for eval_case in evals:
        for run_number in range(1, args.runs + 1):
            run_single_eval(eval_case, workspace, run_number)

    summary = {
        "workspace": str(workspace),
        "eval_count": len(evals),
        "runs_per_eval": args.runs,
        "configuration": "with_skill",
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
