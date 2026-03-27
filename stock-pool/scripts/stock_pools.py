#!/usr/bin/env python3

from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
from pathlib import Path
from typing import Any, Optional
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import urlopen

try:
    import akshare as ak
except ImportError:
    ak = None


STATE_PATH = Path(__file__).parent.parent / "data" / "stock_pools.json"
DEFAULT_POOL_NAME = "默认股票池"
POOL_SUFFIXES = ("股票池", "股票组", "池", "组")
DEFAULT_POOL_ALIASES = {
    DEFAULT_POOL_NAME,
    "默认池",
    "默认组",
    "默认股票池",
    "默认股票组",
}
EASTMONEY_SUGGEST_TOKEN = "D43BF722C8E33BDC906FB84D85E326E8"
AKSHARE_LOOKUP_TIMEOUT_SECONDS = 2.5
_AKSHARE_CODE_NAME_MAP: Optional[dict[str, str]] = None


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


def is_ticker_id(value: str) -> bool:
    return bool(re.fullmatch(r"\d{6}", value))


def akshare_code_name_map() -> dict[str, str]:
    global _AKSHARE_CODE_NAME_MAP
    if _AKSHARE_CODE_NAME_MAP is not None:
        return _AKSHARE_CODE_NAME_MAP

    if ak is None:
        _AKSHARE_CODE_NAME_MAP = {}
        return _AKSHARE_CODE_NAME_MAP

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        future = executor.submit(ak.stock_info_a_code_name)
        df = future.result(timeout=AKSHARE_LOOKUP_TIMEOUT_SECONDS)
    except Exception:
        executor.shutdown(wait=False, cancel_futures=True)
        _AKSHARE_CODE_NAME_MAP = {}
        return _AKSHARE_CODE_NAME_MAP
    executor.shutdown(wait=False, cancel_futures=True)

    code_column = None
    name_column = None
    for candidate in ("code", "代码"):
        if candidate in df.columns:
            code_column = candidate
            break
    for candidate in ("name", "名称"):
        if candidate in df.columns:
            name_column = candidate
            break
    if code_column is None or name_column is None:
        _AKSHARE_CODE_NAME_MAP = {}
        return _AKSHARE_CODE_NAME_MAP

    mapping: dict[str, str] = {}
    for _, row in df.iterrows():
        code = str(row[code_column]).strip()
        name = str(row[name_column]).strip()
        if is_ticker_id(code) and name:
            mapping[name] = code
    _AKSHARE_CODE_NAME_MAP = mapping
    return _AKSHARE_CODE_NAME_MAP


def lookup_ticker_id_via_akshare(query: str) -> Optional[str]:
    if is_ticker_id(query):
        return query
    return akshare_code_name_map().get(query)


def lookup_ticker_id_via_eastmoney(query: str) -> Optional[str]:
    url = (
        "https://searchapi.eastmoney.com/api/suggest/get"
        f"?input={quote(query)}&type=14&token={EASTMONEY_SUGGEST_TOKEN}"
    )
    try:
        with urlopen(url, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError):
        return None

    data = payload.get("QuotationCodeTable", {}).get("Data", [])
    if not data:
        return None
    first_match = data[0]
    code = first_match.get("Code") or first_match.get("UnifiedCode")
    if not isinstance(code, str) or not is_ticker_id(code):
        return None
    return code


def lookup_ticker_id(query: str) -> Optional[str]:
    if is_ticker_id(query):
        return query
    return lookup_ticker_id_via_akshare(query) or lookup_ticker_id_via_eastmoney(query)


def resolve_ticker_id_or_raise(raw_value: str) -> str:
    ticker_id = lookup_ticker_id(raw_value.strip())
    if ticker_id is None:
        raise ValueError(f"无法解析股票标识: {raw_value}")
    return ticker_id


def normalize_member_value(raw_member: Any) -> Optional[str]:
    if isinstance(raw_member, str):
        stripped = raw_member.strip()
        if not stripped:
            return None
        return lookup_ticker_id(stripped) or stripped
    if isinstance(raw_member, dict):
        for key in ("tickid", "ticker_id", "tickerId", "code", "name"):
            value = raw_member.get(key)
            if isinstance(value, str) and value.strip():
                return lookup_ticker_id(value.strip()) or value.strip()
    return None


def normalize_state_members(state: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    changed = False
    for pool in state.get("pools", {}).values():
        normalized_members: list[str] = []
        for raw_member in pool.get("members", []):
            normalized = normalize_member_value(raw_member)
            if normalized is None:
                changed = True
                continue
            if normalized not in normalized_members:
                normalized_members.append(normalized)
            if normalized != raw_member:
                changed = True
        if normalized_members != pool.get("members", []):
            pool["members"] = normalized_members
            changed = True
    return state, changed


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        state = default_state()
        save_state(state)
        return state
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    state = ensure_default_pool(state)
    state, changed = normalize_state_members(state)
    if changed:
        save_state(state)
    return state


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


def unique_preserve_order(values: list[str]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def clean_text_token(value: str) -> str:
    return value.strip().strip("，。,；;？！?")


def normalize_pool_reference(raw_name: str) -> str:
    candidate = clean_text_token(raw_name)
    if candidate in DEFAULT_POOL_ALIASES:
        return DEFAULT_POOL_NAME

    for suffix in POOL_SUFFIXES:
        if not candidate.endswith(suffix):
            continue
        base = candidate[: -len(suffix)].strip()
        if base in {"默认", "默认股票"}:
            return DEFAULT_POOL_NAME
        if base:
            return base
    return candidate


def candidate_pool_names(raw_name: str) -> list[str]:
    candidate = clean_text_token(raw_name)
    normalized = normalize_pool_reference(candidate)
    candidates = [candidate]
    if normalized not in candidates:
        candidates.append(normalized)
    if normalized != DEFAULT_POOL_NAME:
        for variant in (f"{normalized}股票池", f"{normalized}股票组"):
            if variant not in candidates:
                candidates.append(variant)
    return candidates


def resolve_pool_names(state: dict[str, Any], raw_pool_names: list[str]) -> list[str]:
    resolved = []
    for raw_name in raw_pool_names:
        if not clean_text_token(raw_name):
            continue
        for candidate in candidate_pool_names(raw_name):
            if candidate in state["pools"]:
                resolved.append(candidate)
                break
        else:
            resolved.append(normalize_pool_reference(raw_name))
    return unique_preserve_order(resolved)


def ensure_pool_in_state(state: dict[str, Any], pool_name: str) -> bool:
    if pool_name == DEFAULT_POOL_NAME:
        ensure_default_pool(state)
        return False
    if pool_name in state["pools"]:
        return False
    state["pools"][pool_name] = {
        "name": pool_name,
        "is_default": False,
        "members": [],
    }
    return True


def ensure_pools_in_state(state: dict[str, Any], pool_names: list[str]) -> list[str]:
    created_pools = []
    for pool_name in pool_names:
        if ensure_pool_in_state(state, pool_name):
            created_pools.append(pool_name)
    return created_pools


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


def add_stock_by_input_impl(pool_name: str, raw_value: str) -> dict[str, Any]:
    try:
        tickid = resolve_ticker_id_or_raise(raw_value)
    except ValueError as exc:
        return {
            "ok": False,
            "action": "add_stock",
            "pool_name": pool_name,
            "stock_name": raw_value,
            "message": str(exc),
        }
    result = add_stock_impl(pool_name, tickid)
    result["stock_name"] = raw_value
    return result


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


def remove_stock_by_input_impl(pool_name: str, raw_value: str) -> dict[str, Any]:
    tickid = lookup_ticker_id(raw_value) or raw_value
    result = remove_stock_impl(pool_name, tickid)
    result["stock_name"] = raw_value
    return result


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
        "all_stocks": all_stocks(state),
    }


def parse_text_command(text: str) -> tuple[str, dict[str, Any]]:
    normalized = " ".join(text.strip().split())
    named_pool = r"([^\s，。,；;]+)"
    named_pool_before_unit = r"([^\s，。,；;]+?)(?=股票(?:池|组)|池|组)"
    pool_unit = r"(?:股票(?:池|组)|池|组)"

    match = re.search(
        rf"(?:帮我)?创建一个股票(?:池|组)[，,\s]*(?:池名|组名)为\s*{named_pool}[，,\s]*并(?:将|把)\s*(.+?)\s*加入(?:到)?(?:该|这个)?股票(?:池|组)[，,\s]*然后关注到\s*(.+)",
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

    if any(phrase in normalized for phrase in {"获取所有关注股票", "获取所有组的股票", "所有关注股票", "所有组的股票"}):
        return "show_all_stocks", {}

    if any(phrase in normalized for phrase in {"查看所有股票组", "获取所有股票组", "显示所有股票组"}):
        return "show_all_groups", {}

    match = re.search(r"删除股票(?:池|组)\s*([^\s，。,；;]+)", normalized)
    if match:
        return "delete_group", {"group_name": match.group(1)}

    match = re.search(r"股票(?:池|组)\s*([^\s，。,；;]+)\s*修改为\s*([^\s，。,；;]+)", normalized)
    if match:
        return "rename_group", {"group_name": match.group(1), "new_group_name": match.group(2)}

    match = re.search(
        rf"(?:帮我)?(?:创建|新增)一个股票(?:池|组)[，,\s]*(?:池名|组名)为\s*{named_pool}[，,\s]*(?:并|然后)?(?:将|把)?\s*([^\s，。,；;]+)\s*加入(?:到)?(?:该|这个)?股票(?:池|组)(?:中)?",
        normalized,
    )
    if match:
        return "create_group_and_add_stock", {"group_name": match.group(1), "stock_name": match.group(2)}

    match = re.search(
        rf"把\s*(.+?)\s*加入\s*{named_pool_before_unit}{pool_unit}中",
        normalized,
    )
    if match and any(token in match.group(1) for token in ("和", "、", "，", ",")):
        stock_names = [name.strip() for name in re.split(r"[、和及,，]", match.group(1)) if name.strip()]
        return "add_multiple_stocks", {"group_name": match.group(2), "stock_names": stock_names}

    match = re.search(
        rf"将\s*(.+?)\s*加入\s*{named_pool_before_unit}{pool_unit}中",
        normalized,
    )
    if match and any(token in match.group(1) for token in ("和", "、", "，", ",")):
        stock_names = [name.strip() for name in re.split(r"[、和及,，]", match.group(1)) if name.strip()]
        return "add_multiple_stocks", {"group_name": match.group(2), "stock_names": stock_names}

    match = re.search(
        rf"(?:帮我)?(?:创建|新增)一个股票(?:池|组)[，,\s]*(?:池名|组名)为\s*{named_pool}",
        normalized,
    )
    if match:
        return "create_group", {"group_name": match.group(1)}

    match = re.search(
        rf"(?:新建|创建|新增)一个叫\s*{named_pool}\s*的股票(?:池|组)",
        normalized,
    )
    if match:
        return "create_group", {"group_name": match.group(1)}

    match = re.search(rf"将\s*([^\s，。,；;]+)\s*加入\s*{named_pool_before_unit}{pool_unit}中", normalized)
    if match:
        return "add_stock", {"stock_name": match.group(1), "group_name": match.group(2)}

    match = re.search(rf"把\s*([^\s，。,；;]+)\s*加入\s*{named_pool_before_unit}{pool_unit}中", normalized)
    if match:
        return "add_stock", {"stock_name": match.group(1), "group_name": match.group(2)}

    match = re.search(rf"把\s*(.+?)\s*从\s*{named_pool_before_unit}{pool_unit}(?:中)?删掉", normalized)
    if match and ("和" in match.group(1) or "、" in match.group(1) or "，" in match.group(1) or "," in match.group(1)):
        stock_names = [name.strip() for name in re.split(r"[、和及,，]", match.group(1)) if name.strip()]
        return "remove_multiple_stocks", {"group_name": match.group(2), "stock_names": stock_names}

    match = re.search(rf"把\s*([^\s，。,；;]+)\s*从\s*{named_pool_before_unit}{pool_unit}(?:中)?删掉", normalized)
    if match:
        return "remove_stock", {"stock_name": match.group(1), "group_name": match.group(2)}

    match = re.search(rf"将\s*(.+?)\s*从\s*{named_pool_before_unit}{pool_unit}(?:中)?移除", normalized)
    if match and ("和" in match.group(1) or "、" in match.group(1) or "，" in match.group(1) or "," in match.group(1)):
        stock_names = [name.strip() for name in re.split(r"[、和及,，]", match.group(1)) if name.strip()]
        return "remove_multiple_stocks", {"group_name": match.group(2), "stock_names": stock_names}

    match = re.search(rf"将\s*([^\s，。,；;]+)\s*从\s*{named_pool_before_unit}{pool_unit}(?:中)?移除", normalized)
    if match:
        return "remove_stock", {"stock_name": match.group(1), "group_name": match.group(2)}

    match = re.search(rf"从\s*{named_pool_before_unit}{pool_unit}(?:中)?删除\s*([^\s，。,；;]+)", normalized)
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

    match = re.search(rf"{named_pool_before_unit}{pool_unit}有哪些股票[?？]?", normalized)
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
    json_print(add_stock_by_input_impl(args.pool_name, args.stock_name))


def remove_stock(args: argparse.Namespace) -> None:
    json_print(remove_stock_by_input_impl(args.pool_name, args.stock_name))


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


def follow_stock_impl(stock_name: str, raw_pool_names: Optional[list[str]]) -> dict[str, Any]:
    state = load_state()
    try:
        ticker_id = resolve_ticker_id_or_raise(stock_name)
    except ValueError as exc:
        return {
            "ok": False,
            "action": "follow_stock",
            "stock_name": stock_name,
            "message": str(exc),
        }
    requested_pool_names = raw_pool_names or [DEFAULT_POOL_NAME]
    pool_names = resolve_pool_names(state, requested_pool_names)
    created_pools = ensure_pools_in_state(state, pool_names) if raw_pool_names else []
    available_pools = list(state["pools"].keys())

    updated_pools = []
    already_present_pools = []
    for pool_name in pool_names:
        pool = state["pools"][pool_name]
        if ticker_id in member_tickids(pool):
            already_present_pools.append(pool_name)
            continue
        pool.setdefault("members", []).append(ticker_id)
        updated_pools.append(pool_name)

    save_state(state)
    return {
        "ok": True,
        "action": "follow_stock",
        "stock_name": stock_name,
        "ticker_id": ticker_id,
        "selected_pools": pool_names,
        "used_default_pool": not raw_pool_names,
        "default_pool_name": DEFAULT_POOL_NAME,
        "available_pools": available_pools,
        "created_pools": created_pools,
        "updated_pools": updated_pools,
        "already_present_pools": already_present_pools,
    }


def follow_stock(args: argparse.Namespace) -> None:
    json_print(follow_stock_impl(args.stock_name, args.pools))


def unfollow_stock(args: argparse.Namespace) -> None:
    state = load_state()
    ticker_id = lookup_ticker_id(args.stock_name) or args.stock_name
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
        remaining = [member for member in members if member != ticker_id]
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
            "ticker_id": ticker_id,
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
        results = [add_stock_by_input_impl(payload["group_name"], stock_name) for stock_name in payload["stock_names"]]
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
        results = [remove_stock_by_input_impl(payload["group_name"], stock_name) for stock_name in payload["stock_names"]]
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
        add_result = add_stock_by_input_impl(payload["group_name"], payload["stock_name"])
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
            result = add_stock_by_input_impl(payload["group_name"], stock_name)
            steps.append(result)
            last_pool = result.get("pool", last_pool)
        follow_results = [follow_stock_impl(stock_name, payload["follow_groups"]) for stock_name in payload["stock_names"]]
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
