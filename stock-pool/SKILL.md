---
name: stock-pool
description: Create and maintain persistent stock pools (股票池/股票组) across turns and conversations. Use this skill whenever the user wants to create a 股票池 or 股票组, add or remove stocks, rename or delete a pool, list pool members, view all followed stocks, or say things like “关注 上能电气”, “取消关注 上能电气”, “储能池有哪些股票”, or “获取所有关注股票”.
---


# Stock Pool（股票池/股票组）

Manage persistent stock pools (股票池/股票组，以下统称“股票池”) with a local state file and script. This skill is for operational pool maintenance, not broad stock analysis.


## Source of truth

- State file: `/Users/benliu/Documents/Playground/stock-pool/data/stock_pools.json`
- Script: `/Users/benliu/Documents/Playground/stock-pool/scripts/stock_pools.py`

Always use the script instead of editing JSON manually.

## Core rules

- Read saved state first and write updated state back after every change.
- Do not rely on chat memory for stock-pool state.
- The default pool is `默认股票池`（系统基础池，始终存在，不可删除或重命名，等同于“默认组”）。文档中“默认组”与“默认股票池”同义。
- `默认股票池` must always exist。
- `默认股票池` cannot be deleted。
- `默认股票池` cannot be renamed。
- Stocks can be added to or removed from `默认股票池`。
- If a target pool does not exist, say `股票池不存在`（兼容“股票组不存在”）。
- Avoid duplicates inside the same pool.

## Preferred entrypoint

Prefer:

```bash
python3 /Users/benliu/Documents/Playground/stock-pool/scripts/stock_pools.py text-command "<自然语言指令>"
```

Use direct subcommands only when they are clearer than `text-command`.

## Supported operations

- Create, delete, or rename pool (支持“股票池/股票组”)
- Add or remove stock(s) in pool
- Show pool(s) or all stocks
- Follow/unfollow stock(s)
- Support chained commands

## Follow / unfollow behavior

- `关注 <股票>`: if no pool is specified, default to `默认股票池`。
- `关注 <股票>到A池和B池`（或A组和B组）: add the stock to all selected pools, auto-create pool if needed.
- `取消关注 <股票>`: if no pool is specified, return selectable pool options instead of removing silently。
- `从A池和B池取消关注<股票>`（或A组和B组）: remove from the selected pools only。

## Natural language patterns

High-confidence patterns already supported by `text-command`（支持“股票池/股票组”同义表达）：

- `新建一个叫储能的股票池`
- `将上能电气加入储能股票池中`
- `把隆基绿能和通威股份加入光伏股票池中`
- `把上能电气从储能池删掉`
- `删除股票池 储能`
- `股票池 储能修改为储能-2`
- `储能池有哪些股票`
- `获取所有关注股票`
- `关注 上能电气`
- `关注 上能电气到默认股票池和储能池`
- `取消关注 上能电气`
- `从默认池和储能池取消关注上能电气`
- `帮我创建一个股票池，池名为风电，并将金风科技加入该股票池`
- `创建一个股票池，池名为储能-2，并将宁德时代和亿纬锂能加入该股票池，然后关注到默认池和储能池`

## Minimal command reference

```bash
python3 /Users/benliu/Documents/Playground/stock-pool/scripts/stock_pools.py create-pool 储能
python3 /Users/benliu/Documents/Playground/stock-pool/scripts/stock_pools.py add-stock 储能 上能电气
python3 /Users/benliu/Documents/Playground/stock-pool/scripts/stock_pools.py remove-stock 储能 上能电气
python3 /Users/benliu/Documents/Playground/stock-pool/scripts/stock_pools.py show-pool 储能
python3 /Users/benliu/Documents/Playground/stock-pool/scripts/stock_pools.py show-all-stocks
python3 /Users/benliu/Documents/Playground/stock-pool/scripts/stock_pools.py follow-stock 上能电气 --pools 默认池 储能
python3 /Users/benliu/Documents/Playground/stock-pool/scripts/stock_pools.py unfollow-stock 上能电气 --pools 默认池 储能
```

## Response shape

Prefer concise stateful output:

```markdown
# Stock Pool: <name>

## Action
<created | updated | removed | current state>

## Members
- <stock>

## Notes
- <duplicates skipped, selection required, or error note>
```

For `show-all-stocks`, keep both:

- grouped view by stock pool
- deduplicated `all_stocks` summary

## When not to overcomplicate

- Do not invent extra tags or metadata unless the user asks.
- Do not turn a simple edit request into market commentary.
- Do not rebuild all groups if the user asked for a single change.
