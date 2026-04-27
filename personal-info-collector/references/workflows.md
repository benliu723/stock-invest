# Workflows

## Create Or Maintain A Topic

1. 将 topic ID 规范化为 lower-kebab-case。
2. 在当前 skill 项目的 `topics/` 下创建或维护 `topics/<topic-id>/`。
3. 如果缺少 `sources.yaml`，创建一个空 sources 模板，包含 `topic` 和 `sources: []`。
4. 将用户意图写入 `topic.purpose`。

## Determine Sources

1. 先读取 `references/source-selection.md`。
2. 如果存在 `topics/<topic-id>/source-brief.md`，同时读取；如果不存在，先在回复中给出简短的内联方向假设。
3. 根据全局 source 规则和 topic brief 或内联方向假设提出 source candidates，不要直接写入 `sources.yaml`。
4. 每个 candidate 按 `references/source-selection.md` 的 candidate shape 说明 `type`、匹配规则、质量、预期信号、风险和 `recommendation`。
5. source 必须是稳定的信息入口，而不是单篇文章、抽象主题词或临时搜索结果。
6. 当前阶段只接受 `url_type: page` 或 `url_type: feed`。
7. 得到用户确认后，只把确认采纳的 `include` candidates 写入 `sources.yaml`。
8. 写入时按 `references/sources-schema.md` 填写，并保留解释 source 价值的 notes。

## Collect Into Inbox

目标：从 `topics/<topic-id>/sources.yaml` 收集新原材料到 `inbox/`。

边界：

- 收集阶段只负责发现和写入新的候选原材料。
- 读取全部 `inbox/*.yaml` 做去重，不论 status 是什么；去重优先使用 `candidate.url`。
- 只创建 `status: pending` 的 inbox item。
- 不写 records，也不修改已有 inbox item 的 status。
- 具体执行步骤使用 `references/collect-topic.md`。

## Process Inbox

目标：处理 `status: pending` 的 inbox item。

边界：

- 每个 pending item 只做两类决定：`draft` 或 `record`。
- `draft` 表示丢弃、不正式审核；`record` 表示正式审核并沉淀为记录。
- Process 阶段不移动 inbox 文件，只更新 inbox YAML 字段，并在需要时创建 record。
- 只有 record 文件创建成功后，才能把 inbox item 更新为 `status: archive`；失败时保持 `status: pending`。
- 具体执行步骤使用 `references/process-inbox.md`。

## Maintenance Review

当用户要求 review 系统时：

- 识别 stale sources
- 识别 duplicate sources
- 找出长期停留在 `status: pending` 的 inbox items
- 找出可能应清理或重新处理的 `status: draft` inbox items
- 检查 `status: archive` 的 inbox items 是否都有对应 record
- 找出缺少 required fields 或 review 状态不完整的 records
