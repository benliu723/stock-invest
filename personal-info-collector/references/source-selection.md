# 数据源选择规则

## 目标

数据源选择决定哪些稳定的信息入口可以写入 `topics/<topic-id>/sources.yaml`。

目标是在前期保持轻量运行，同时让 topic 方向变得明确。如果数据源方向错了，后续 collect 和 process 阶段无法可靠修复输出质量。

## 全局规则

- 如果存在 RSS 或 Atom feed，优先使用 feed；没有 feed 时再使用稳定页面。
- 优先采纳一手来源、官方页面、研究发布、开源项目页面和垂直行业来源。
- 泛泛新闻页默认不采纳，除非它能补足一个明确的信息缺口。
- 单篇文章、搜索结果、临时落地页和一次性公告不是有效 source。
- 每个 source candidate 必须说明它服务的方向、质量类别、预期信号和风险。
- 如果找不到强候选，直接说明，不要用弱 source 填充 `sources.yaml`。

## Topic Source Brief

每个 topic 可以在 `sources.yaml` 旁边定义一个简短的 source brief：

```text
topics/<topic-id>/source-brief.md
```

brief 用于收窄该 topic 的数据源方向。保持简短，并使用固定结构：

```markdown
# Source Brief: <topic-id>

## Focus
这个 topic 的核心关注方向。

## Include
- 应该纳入这个 topic 的来源或内容类型。

## Exclude
- 即使看起来相关，也不应该加入的来源或内容类型。

## Keywords
用于判断 source 是否匹配的关键词。
```

如果 topic 没有 `source-brief.md`，先在回复中给出简短的内联方向假设，再提出 candidates；只有用户明确要求固化方向时，才创建或更新 `source-brief.md`。

如果用户不想维护 topic brief，可以只使用全局规则继续，但需要说明此时 source 方向约束较弱。

## Candidate 输出结构

提出 source candidates 时，必须读取本文件；如果存在 `topics/<topic-id>/source-brief.md`，也必须读取。

使用简短、固定的 candidate 结构：

```yaml
name:
type:
url:
url_type:
matched_global_rule:
matched_topic_rule:
source_quality: primary | vertical | aggregator
expected_signal:
risk:
recommendation: include | maybe | exclude
```

- `include` 表示该 source 适合在用户确认后写入。
- `maybe` 表示默认不写入。
- `exclude` 表示不应写入；列出它只是为了说明拒绝原因。
- `type` 使用 `references/sources-schema.md` 中的 source types。

如果 candidate 符合全局规则，但与 topic brief 冲突，应标记为 `maybe` 或 `exclude`，不能标记为 `include`。

## 确认流程

1. 读取本全局数据源选择规则。
2. 如果存在当前 topic 的 `source-brief.md`，读取它；如果不存在，在回复中给出简短的内联方向假设。
3. 只有用户明确要求固化方向时，才创建或更新 `source-brief.md`。
4. 按 candidate 输出结构提出 source candidates。
5. 只把用户确认采纳的 `include` candidates 写入 `sources.yaml`。

除非用户明确要求覆盖推荐结果，否则不要把 `maybe` 或 `exclude` candidates 写入 `sources.yaml`。
