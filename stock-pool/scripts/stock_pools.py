#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Optional


STATE_PATH = Path(__file__).parent.parent / "data" / "stock_pools.json"
DEFAULT_POOL_NAME = "默认股票池"


def default_state() -> dict[str, Any]:
    return {
        "pools": {
            DEFAULT_POOL_NAME: {
                "name": DEFAULT_POOL_NAME,
                "is_default": True,
                "members": [],
            }
        },
    }


def ensure_default_pool(state: dict[str, Any]) -> dict[str, Any]:
    pools = state.setdefault("pools", {})
    pool = pools.get(DEFAULT_POOL_NAME)
    if not isinstance(pool, dict):
        pools[DEFAULT_POOL_NAME] = {
            "name": DEFAULT_POOL_NAME,
            "is_default": True,
            "members": [],
        }
        return state
    pool["name"] = DEFAULT_POOL_NAME
    pool["is_default"] = True
    pool.setdefault("members", [])
    return state


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        state = default_state()
        save_state(state)
        return state
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return ensure_default_pool(state)


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps(ensure_default_pool(state), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def find_pool(state: dict[str, Any], pool_name: str) -> Optional[dict[str, Any]]:
    return state["pools"].get(pool_name)


def member_tickids(pool: dict[str, Any]) -> list[str]:
    return list(pool.get("members", []))


def all_stocks(state: dict[str, Any]) -> list[str]:
    seen = set()
    result = []
    for pool in state["pools"].values():
        for tickid in member_tickids(pool):
            if tickid not in seen:
                seen.add(tickid)
                result.append(tickid)
    return result


def json_print(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def resolve_pool_names(state: dict[str, Any], raw_pool_names: list[str]) -> list[str]:
    resolved = []
    for raw_name in raw_pool_names:
        candidate = raw_name.strip()
        if candidate in state["pools"]:
            resolved.append(candidate)
            continue
        if candidate.endswith("池") and candidate[:-1] in state["pools"]:
            resolved.append(candidate[:-1])
            continue
        resolved.append(candidate)
    return resolved


def create_pool_impl(pool_name: str) -> dict[str, Any]:
    state = load_state()
    if pool_name in state["pools"]:
        return {
            "ok": True,
            "action": "create_pool",
            "pool_name": pool_name,
            "created": False,
            "message": f"股票池 {pool_name} 已存在",
            "pool": state["pools"][pool_name],
        }

    state["pools"][pool_name] = {
        "name": pool_name,
        "is_default": False,
        "members": [],
    }
    save_state(state)
    return {
        "ok": True,
        "action": "create_pool",
        "pool_name": pool_name,
        "created": True,
        "message": f"已创建股票池 {pool_name}",
        "pool": state["pools"][pool_name],
    }


def delete_pool_impl(pool_name: str) -> dict[str, Any]:
    state = load_state()
    if pool_name == DEFAULT_POOL_NAME:
        return {
            "ok": False,
            "action": "delete_pool",
            "pool_name": pool_name,
            "message": "默认股票池不可删除",
        }
    if pool_name not in state["pools"]:
        return {
            "ok": False,
            "action": "delete_pool",
            "pool_name": pool_name,
            "message": "股票池不存在",
        }
    deleted = state["pools"].pop(pool_name)
    save_state(state)
    return {
        "ok": True,
        "action": "delete_pool",
        "pool_name": pool_name,
        "message": f"已删除股票池 {pool_name}",
        "deleted_pool": deleted,
    }


def rename_pool_impl(pool_name: str, new_pool_name: str) -> dict[str, Any]:
    state = load_state()
    if pool_name == DEFAULT_POOL_NAME:
        return {
            "ok": False,
            "action": "rename_pool",
            "pool_name": pool_name,
            "new_pool_name": new_pool_name,
            "message": "默认股票池不可修改",
        }
    pool = find_pool(state, pool_name)
    if pool is None:
        return {
            "ok": False,
            "action": "rename_pool",
            "pool_name": pool_name,
            "new_pool_name": new_pool_name,
            "message": "股票池不存在",
        }
    if new_pool_name in state["pools"]:
        return {
            "ok": False,
            "action": "rename_pool",
            "pool_name": pool_name,
            "new_pool_name": new_pool_name,
            "message": f"目标股票池 {new_pool_name} 已存在",
        }
    updated_pool = dict(pool)
    updated_pool["name"] = new_pool_name
    state["pools"].pop(pool_name)
    state["pools"][new_pool_name] = updated_pool
    save_state(state)
    return {
        "ok": True,
        "action": "rename_pool",
        "pool_name": pool_name,
        "new_pool_name": new_pool_name,
        "message": f"已将股票池 {pool_name} 修改为 {new_pool_name}",
        "pool": updated_pool,
    }


def add_stock_impl(pool_name: str, tickid: str) -> dict[str, Any]:
    state = load_state()
    pool = find_pool(state, pool_name)
    if pool is None:
        return {
            "ok": False,
            "action": "add_stock",
            "pool_name": pool_name,
            "tickid": tickid,
            "message": "股票池不存在",
        }
    if tickid in pool.get("members", []):
        return {
            "ok": True,
            "action": "add_stock",
            "pool_name": pool_name,
            "tickid": tickid,
            "added": False,
            "message": f"{tickid} 已在股票池 {pool_name} 中",
            "pool": pool,
        }
    pool.setdefault("members", []).append(tickid)
    save_state(state)
    return {
        "ok": True,
        "action": "add_stock",
        "pool_name": pool_name,
        "tickid": tickid,
        "added": True,
        "message": f"已将 {tickid} 加入股票池 {pool_name}",
        "pool": pool,
    }


def remove_stock_impl(pool_name: str, tickid: str) -> dict[str, Any]:
    state = load_state()
    pool = find_pool(state, pool_name)
    if pool is None:
        return {
            "ok": False,
            "action": "remove_stock",
            "pool_name": pool_name,
            "tickid": tickid,
            "message": "股票池不存在",
        }
    members = pool.get("members", [])
    if tickid not in members:
        return {
            "ok": True,
            "action": "remove_stock",
            "pool_name": pool_name,
            "tickid": tickid,
            "removed": False,
            "message": f"{tickid} 不在股票池 {pool_name} 中",
            "pool": pool,
        }
    pool["members"] = [t for t in members if t != tickid]
    save_state(state)
    return {
        "ok": True,
        "action": "remove_stock",
        "pool_name": pool_name,
        "tickid": tickid,
        "removed": True,
        "message": f"已将 {tickid} 从股票池 {pool_name} 中移除",
        "pool": pool,
    }


def show_pool_impl(pool_name: str) -> dict[str, Any]:
    state = load_state()
    pool = find_pool(state, pool_name)
    if pool is None:
        return {
            "ok": False,
            "action": "show_pool",
            "pool_name": pool_name,
            "message": "股票池不存在",
        }
    return {
        "ok": True,
        "action": "show_pool",
        "pool_name": pool_name,
        "pool": pool,
    }


def show_all_pools_impl() -> dict[str, Any]:
    state = load_state()
    return {
        "ok": True,
        "action": "show_all_pools",
        "default_pool_name": DEFAULT_POOL_NAME,
        "pools": state["pools"],
    }


def show_all_stocks_impl() -> dict[str, Any]:
    state = load_state()
    return {
        "ok": True,
        "action": "show_all_stocks",
        "default_pool_name": DEFAULT_POOL_NAME,
        "pools": {
            name: list(pool.get("members", [])) for name, pool in state["pools"].items()
        },
        "all_stocks": list({tickid for pool in state["pools"].values() for tickid in pool.get("members", [])}),
    }


def parse_text_command(text: str) -> tuple[str, dict[str, Any]]:
    normalized = " ".join(text.strip().split())

    match = re.search(
        r"(?:帮我)?创建一个股票组[，,\s]*组名为\s*([^\s，。,；;]+)[，,\s]*并(?:将|把)\s*(.+?)\s*加入(?:到)?(?:该|这个)?股票组[，,\s]*然后关注到\s*(.+)",
        normalized,
    )
    if match:
        stock_names = [name.strip() for name in re.split(r"[、和及,，]", match.group(2)) if name.strip()]
        follow_group_names = [name.strip() for name in re.split(r"[、和及,，]", match.group(3)) if name.strip()]
        return "create_add_and_follow", {
            "group_name": match.group(1),
            "stock_names": stock_names,
            "follow_groups": follow_group_names,
        }

    if normalized in {"获取所有关注股票", "获取所有组的股票", "所有关注股票", "所有组的股票"}:
        return "show_all_stocks", {}

    if normalized in {"查看所有股票组", "获取所有股票组", "显示所有股票组"}:
        return "show_all_groups", {}

    match = re.search(r"删除股票组\s*([^\s，。,；;]+)", normalized)
    if match:
        return "delete_group", {"group_name": match.group(1)}

    match = re.search(r"股票组\s*([^\s，。,；;]+)\s*修改为\s*([^\s，。,；;]+)", normalized)
    if match:
        return "rename_group", {"group_name": match.group(1), "new_group_name": match.group(2)}

    match = re.search(
        r"(?:帮我)?(?:创建|新增)一个股票组[，,\s]*组名为\s*([^\s，。,；;]+)[，,\s]*(?:并|然后)?(?:将|把)?\s*([^\s，。,；;]+)\s*加入(?:到)?(?:该|这个)?股票组(?:中)?",
        normalized,
    )
    if match:
        return "create_group_and_add_stock", {"group_name": match.group(1), "stock_name": match.group(2)}

    match = re.search(
        r"把\s*(.+?)\s*加入\s*([^\s，。,；;]+)股票组中",
        normalized,
    )
    if match and "和" in match.group(1):
        stock_names = [name.strip() for name in re.split(r"[、和及,，]", match.group(1)) if name.strip()]
        return "add_multiple_stocks", {"group_name": match.group(2), "stock_names": stock_names}

    match = re.search(
        r"将\s*(.+?)\s*加入\s*([^\s，。,；;]+)股票组中",
        normalized,
    )
    if match and "和" in match.group(1):
        stock_names = [name.strip() for name in re.split(r"[、和及,，]", match.group(1)) if name.strip()]
        return "add_multiple_stocks", {"group_name": match.group(2), "stock_names": stock_names}

    match = re.search(r"(?:帮我)?创建一个股票组[，,\s]*组名为\s*([^\s，。,；;]+)", normalized)
    if match:
        return "create_group", {"group_name": match.group(1)}

    match = re.search(r"将\s*([^\s，。,；;]+)\s*加入\s*([^\s，。,；;]+)股票组中", normalized)
    if match:
        return "add_stock", {"stock_name": match.group(1), "group_name": match.group(2)}

    match = re.search(r"把\s*([^\s，。,；;]+)\s*加入\s*([^\s，。,；;]+)股票组中", normalized)
    if match:
        return "add_stock", {"stock_name": match.group(1), "group_name": match.group(2)}

    match = re.search(r"把\s*(.+?)\s*从\s*([^\s，。,；;]+)组(?:中)?删掉", normalized)
    if match and ("和" in match.group(1) or "、" in match.group(1) or "，" in match.group(1) or "," in match.group(1)):
        stock_names = [name.strip() for name in re.split(r"[、和及,，]", match.group(1)) if name.strip()]
        return "remove_multiple_stocks", {"group_name": match.group(2), "stock_names": stock_names}

    match = re.search(r"把\s*([^\s，。,；;]+)\s*从\s*([^\s，。,；;]+)组(?:中)?删掉", normalized)
    if match:
        return "remove_stock", {"stock_name": match.group(1), "group_name": match.group(2)}

    match = re.search(r"将\s*(.+?)\s*从\s*([^\s，。,；;]+)组(?:中)?移除", normalized)
    if match and ("和" in match.group(1) or "、" in match.group(1) or "，" in match.group(1) or "," in match.group(1)):
        stock_names = [name.strip() for name in re.split(r"[、和及,，]", match.group(1)) if name.strip()]
        return "remove_multiple_stocks", {"group_name": match.group(2), "stock_names": stock_names}

    match = re.search(r"将\s*([^\s，。,；;]+)\s*从\s*([^\s，。,；;]+)组(?:中)?移除", normalized)
    if match:
        return "remove_stock", {"stock_name": match.group(1), "group_name": match.group(2)}

    match = re.search(r"从\s*([^\s，。,；;]+)组(?:中)?删除\s*([^\s，。,；;]+)", normalized)
    if match:
        return "remove_stock", {"group_name": match.group(1), "stock_name": match.group(2)}

    match = re.search(r"从\s*(.+?)\s*取消关注\s*([^\s，。,；;]+)", normalized)
    if match:
        group_names = [name.strip() for name in re.split(r"[、和及,，]", match.group(1)) if name.strip()]
        return "unfollow_stock", {"stock_name": match.group(2), "groups": group_names}

    match = re.search(r"在\s*(.+?)\s*中取消关注\s*([^\s，。,；;]+)", normalized)
    if match:
        group_names = [name.strip() for name in re.split(r"[、和及,，]", match.group(1)) if name.strip()]
        return "unfollow_stock", {"stock_name": match.group(2), "groups": group_names}

    match = re.search(r"([^\s，。,；;]+)组有哪些股票\??", normalized)
    if match:
        return "show_group", {"group_name": match.group(1)}

    match = re.search(r"取消关注\s*([^\s，。,；;]+)", normalized)
    if match:
        return "unfollow_stock", {"stock_name": match.group(1)}

    match = re.search(r"关注\s*([^\s，。,；;]+)\s*到\s*(.+)", normalized)
    if match:
        group_names = [name.strip() for name in re.split(r"[、和及,，]", match.group(2)) if name.strip()]
        return "follow_stock", {"stock_name": match.group(1), "groups": group_names}

    match = re.search(r"关注\s*([^\s，。,；;]+)", normalized)
    if match:
        return "follow_stock", {"stock_name": match.group(1)}

    raise ValueError("暂不支持这条自然语言指令")


def create_pool(args: argparse.Namespace) -> None:
    json_print(create_pool_impl(args.pool_name))


def delete_pool(args: argparse.Namespace) -> None:
    json_print(delete_pool_impl(args.pool_name))


def rename_pool(args: argparse.Namespace) -> None:
    json_print(rename_pool_impl(args.pool_name, args.new_pool_name))


def add_stock(args: argparse.Namespace) -> None:
    json_print(add_stock_impl(args.pool_name, args.stock_name))


def remove_stock(args: argparse.Namespace) -> None:
    json_print(remove_stock_impl(args.pool_name, args.stock_name))


def show_pool(args: argparse.Namespace) -> None:
    json_print(show_pool_impl(args.pool_name))


def show_all_pools(_: argparse.Namespace) -> None:
    json_print(show_all_pools_impl())


def show_all_stocks(_: argparse.Namespace) -> None:
    json_print(show_all_stocks_impl())


def selection_prompt_payload(state: dict[str, Any], stock_name: str, action: str) -> dict[str, Any]:
    if action == "follow_stock":
        message = "请选择一个或多个股票池；如果不选择，关注操作将默认使用默认股票池"
    else:
        message = "请选择一个或多个股票池以执行取消关注"
    return {
        "ok": True,
        "action": action,
        "selection_required": True,
        "stock_name": stock_name,
        "available_pools": list(state["pools"].keys()),
        "default_pool_name": DEFAULT_POOL_NAME,
        "message": message,
    }


def follow_stock(args: argparse.Namespace) -> None:
    state = load_state()
    raw_pool_names = args.pools or [DEFAULT_POOL_NAME]
    pool_names = resolve_pool_names(state, raw_pool_names)
    available_pools = list(state["pools"].keys())
    missing_pools = [name for name in pool_names if name not in state["pools"]]
    if missing_pools:
        json_print(
            {
                "ok": False,
                "action": "follow_stock",
                "stock_name": args.stock_name,
                "message": "部分股票池不存在",
                "available_pools": available_pools,
                "missing_pools": missing_pools,
                "default_pool_name": DEFAULT_POOL_NAME,
            }
        )
        return

    updated_pools = []
    already_present_pools = []
    for pool_name in pool_names:
        pool = state["pools"][pool_name]
        if args.stock_name in member_tickids(pool):
            already_present_pools.append(pool_name)
            continue
        pool.setdefault("members", []).append(args.stock_name)
        updated_pools.append(pool_name)

    save_state(state)
    json_print(
        {
            "ok": True,
            "action": "follow_stock",
            "stock_name": args.stock_name,
            "selected_pools": pool_names,
            "used_default_pool": not args.pools,
            "default_pool_name": DEFAULT_POOL_NAME,
            "available_pools": available_pools,
            "updated_pools": updated_pools,
            "already_present_pools": already_present_pools,
        }
    )


def unfollow_stock(args: argparse.Namespace) -> None:
    state = load_state()
    available_pools = list(state["pools"].keys())
    if args.pools is None:
        json_print(selection_prompt_payload(state, args.stock_name, "unfollow_stock"))
        return

    pool_names = resolve_pool_names(state, args.pools)
    missing_pools = [name for name in pool_names if name not in state["pools"]]
    if missing_pools:
        json_print(
            {
                "ok": False,
                "action": "unfollow_stock",
                "stock_name": args.stock_name,
                "message": "部分股票池不存在",
                "available_pools": available_pools,
                "missing_pools": missing_pools,
            }
        )
        return

    updated_pools = []
    absent_pools = []
    for pool_name in pool_names:
        pool = state["pools"][pool_name]
        members = pool.get("members", [])
        remaining = [member for member in members if member != args.stock_name]
        if len(remaining) == len(members):
            absent_pools.append(pool_name)
            continue
        pool["members"] = remaining
        updated_pools.append(pool_name)

    save_state(state)
    json_print(
        {
            "ok": True,
            "action": "unfollow_stock",
            "stock_name": args.stock_name,
            "selected_pools": pool_names,
            "available_pools": available_pools,
            "updated_pools": updated_pools,
            "absent_pools": absent_pools,
        }
    )


def text_command(args: argparse.Namespace) -> None:
    try:
        action, payload = parse_text_command(args.text)
    except ValueError as exc:
        json_print(
            {
                "ok": False,
                "action": "text_command",
                "text": args.text,
                "message": str(exc),
            }
        )
        return

    pools = args.pools
    if action == "create_group":
        create_pool(argparse.Namespace(pool_name=payload["group_name"]))
        return
    if action == "delete_group":
        delete_pool(argparse.Namespace(pool_name=payload["group_name"]))
        return
    if action == "rename_group":
        rename_pool(
            argparse.Namespace(
                pool_name=payload["group_name"],
                new_pool_name=payload["new_group_name"],
            )
        )
        return
    if action == "add_stock":
        add_stock(
            argparse.Namespace(pool_name=payload["group_name"], stock_name=payload["stock_name"])
        )
        return
    if action == "add_multiple_stocks":
        results = [add_stock_impl(payload["group_name"], stock_name) for stock_name in payload["stock_names"]]
        json_print(
            {
                "ok": all(result.get("ok", False) for result in results),
                "action": "add_multiple_stocks",
                "group_name": payload["group_name"],
                "stock_names": payload["stock_names"],
                "steps": results,
                "group": results[-1].get("group") if results else None,
            }
        )
        return
    if action == "remove_stock":
        remove_stock(
            argparse.Namespace(pool_name=payload["group_name"], stock_name=payload["stock_name"])
        )
        return
    if action == "remove_multiple_stocks":
        results = [remove_stock_impl(payload["group_name"], stock_name) for stock_name in payload["stock_names"]]
        json_print(
            {
                "ok": all(result.get("ok", False) for result in results),
                "action": "remove_multiple_stocks",
                "group_name": payload["group_name"],
                "stock_names": payload["stock_names"],
                "steps": results,
                "group": results[-1].get("group") if results else None,
            }
        )
        return
    if action == "show_group":
        show_pool(argparse.Namespace(pool_name=payload["group_name"]))
        return
    if action == "show_all_groups":
        show_all_pools(argparse.Namespace())
        return
    if action == "show_all_stocks":
        show_all_stocks(argparse.Namespace())
        return
    if action == "create_group_and_add_stock":
        create_result = create_pool_impl(payload["group_name"])
        add_result = add_stock_impl(payload["group_name"], payload["stock_name"])
        json_print(
            {
                "ok": bool(create_result.get("ok") and add_result.get("ok")),
                "action": "create_group_and_add_stock",
                "group_name": payload["group_name"],
                "stock_name": payload["stock_name"],
                "steps": [create_result, add_result],
                "pool": add_result.get("pool") or create_result.get("pool"),
            }
        )
        return
    if action == "create_add_and_follow":
        steps = [create_pool_impl(payload["group_name"])]
        last_pool = steps[0].get("pool")
        for stock_name in payload["stock_names"]:
            result = add_stock_impl(payload["group_name"], stock_name)
            steps.append(result)
            last_pool = result.get("pool", last_pool)
        follow_results = []
        for stock_name in payload["stock_names"]:
            state = load_state()
            resolved_pools = resolve_pool_names(state, payload["follow_groups"])
            available_pools = list(state["pools"].keys())
            missing_pools = [name for name in resolved_pools if name not in state["pools"]]
            if missing_pools:
                follow_results.append(
                    {
                        "ok": False,
                        "action": "follow_stock",
                        "stock_name": stock_name,
                        "message": "部分股票池不存在",
                        "available_pools": available_pools,
                        "missing_pools": missing_pools,
                        "default_pool_name": DEFAULT_POOL_NAME,
                    }
                )
                continue
            updated_pools = []
            already_present_pools = []
            for pool_name in resolved_pools:
                pool = state["pools"][pool_name]
                if stock_name in member_tickids(pool):
                    already_present_pools.append(pool_name)
                    continue
                pool.setdefault("members", []).append(stock_name)
                updated_pools.append(pool_name)
            save_state(state)
            follow_results.append(
                {
                    "ok": True,
                    "action": "follow_stock",
                    "stock_name": stock_name,
                    "selected_pools": resolved_pools,
                    "used_default_pool": False,
                    "default_pool_name": DEFAULT_POOL_NAME,
                    "available_pools": available_pools,
                    "updated_pools": updated_pools,
                    "already_present_pools": already_present_pools,
                }
            )
        steps.extend(follow_results)
        json_print(
            {
                "ok": all(step.get("ok", False) for step in steps),
                "action": "create_add_and_follow",
                "group_name": payload["group_name"],
                "stock_names": payload["stock_names"],
                "follow_pools": payload["follow_groups"],
                "steps": steps,
                "pool": last_pool,
            }
        )
        return
    if action == "follow_stock":
        follow_pools = payload.get("groups", pools)
        follow_stock(argparse.Namespace(stock_name=payload["stock_name"], pools=follow_pools))
        return
    if action == "unfollow_stock":
        unfollow_pools = payload.get("groups", pools)
        unfollow_stock(argparse.Namespace(stock_name=payload["stock_name"], pools=unfollow_pools))
        return

    json_print(
        {
            "ok": False,
            "action": "text_command",
            "text": args.text,
            "message": f"未实现的动作: {action}",
        }
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage persistent stock pools.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create-pool")
    create.add_argument("pool_name")
    create.set_defaults(func=create_pool)

    delete = subparsers.add_parser("delete-pool")
    delete.add_argument("pool_name")
    delete.set_defaults(func=delete_pool)

    rename = subparsers.add_parser("rename-pool")
    rename.add_argument("pool_name")
    rename.add_argument("new_pool_name")
    rename.set_defaults(func=rename_pool)

    add = subparsers.add_parser("add-stock")
    add.add_argument("pool_name")
    add.add_argument("stock_name")
    add.set_defaults(func=add_stock)

    remove = subparsers.add_parser("remove-stock")
    remove.add_argument("pool_name")
    remove.add_argument("stock_name")
    remove.set_defaults(func=remove_stock)

    show = subparsers.add_parser("show-pool")
    show.add_argument("pool_name")
    show.set_defaults(func=show_pool)

    show_pools = subparsers.add_parser("show-all-pools")
    show_pools.set_defaults(func=show_all_pools)

    show_stocks = subparsers.add_parser("show-all-stocks")
    show_stocks.set_defaults(func=show_all_stocks)

    follow = subparsers.add_parser("follow-stock")
    follow.add_argument("stock_name")
    follow.add_argument("--pools", nargs="*")
    follow.set_defaults(func=follow_stock)

    unfollow = subparsers.add_parser("unfollow-stock")
    unfollow.add_argument("stock_name")
    unfollow.add_argument("--pools", nargs="*")
    unfollow.set_defaults(func=unfollow_stock)

    text = subparsers.add_parser("text-command")
    text.add_argument("text")
    text.add_argument("--pools", nargs="*")
    text.set_defaults(func=text_command)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
