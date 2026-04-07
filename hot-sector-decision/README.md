# Hot Sector Decision

极简的热点后半段交易系统：默认你已经知道热点板块和龙头股，只负责输出 `龙头状态 + 高弹性补涨动作卡片`。

## 输入结构

```json
{
  "hot_theme": "机器人",
  "leader_stock": {
    "name": "龙头A",
    "trend_strength": 88,
    "focus_strength": 90,
    "pullback_quality": 85
  },
  "candidate_stocks": [
    {
      "name": "补涨A",
      "recent_strength": 84,
      "position_vs_leader": 30,
      "extension_risk": 24,
      "in_position": false
    }
  ]
}
```

字段含义：

- `hot_theme`: 已确认的热点板块名称。
- `leader_stock.trend_strength`: 龙头趋势强度，0-100。
- `leader_stock.focus_strength`: 龙头辨识度/资金聚焦强度，0-100。
- `leader_stock.pullback_quality`: 龙头强势整理质量，0-100。
- `candidate_stocks[].recent_strength`: 候选补涨近期强度，0-100。
- `candidate_stocks[].position_vs_leader`: 相对龙头的位置透支程度，越低越有补涨空间，0-100。
- `candidate_stocks[].extension_risk`: 候选股自身透支风险，越低越安全，0-100。
- `candidate_stocks[].in_position`: 当前是否已持有，用于区分 `放弃` 和 `撤退`。

## 输出规则

- 龙头状态只输出三档：`强` / `钝化` / `转弱`
- 候选动作只输出四档：`可做` / `只观察` / `放弃` / `撤退`

默认逻辑：

- 龙头 `强`：只在“补涨强 + 有空间 + 未透支”时输出 `可做`
- 龙头 `钝化`：以 `只观察` 为主
- 龙头 `转弱`：未持仓输出 `放弃`，已持仓输出 `撤退`

## 命令行

```bash
python3 scripts/hot_sector_decision.py evaluate examples/robotics.json
```
