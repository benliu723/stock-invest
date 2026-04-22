# Workflows

## Create Or Maintain A Topic

1. 将 topic ID 规范化为 lower-kebab-case。
2. 在当前 skill 项目的 `topics/` 下创建或维护 `topics/<topic-id>/`。
3. 如果缺少 `sources.yaml`，创建一个空 sources 模板，包含 `topic` 和 `sources: []`。
4. 将用户意图写入 `topic.purpose`。
5. 可以建议 starter sources，但写入 `sources.yaml` 前必须得到用户确认。
6. 添加 sources 时按 `references/sources-schema.md` 填写；每个 source 必须包含 `url_type`。
7. 保留解释 source 价值的 notes。

## Collect Into Inbox

目标：从 `topics/<topic-id>/sources.yaml` 收集新原材料到 `inbox/`。

边界：

- 收集前读取全部 `inbox/*.yaml` 做去重，不论 status 是 `pending`、`draft` 还是 `archive`；去重优先使用 `candidate.url`。
- 收集阶段只创建 `status: pending` 的 inbox item。
- 收集阶段不写 records，也不修改已有 inbox item 的 status。
- 具体执行步骤使用 `assets/collect-topic.prompt.md`。

## Process Inbox

目标：处理 `status: pending` 的 inbox item。

边界：

- 每个 pending item 只做两类决定：`draft` 或 `record`。
- `draft` 表示丢弃、不正式审核：更新该 inbox item 为 `status: draft`，并填写 `processing.processed_at` 和 `processing.decision_reason`。
- `record` 表示正式审核：创建 record，并将该 inbox item 更新为 `status: archive`，同时填写 `processing.record_id`、`processing.record_path`、`processing.processed_at` 和 `processing.decision_reason`。
- record 内部必须设置 `review.status=accepted` 或 `review.status=rejected`。
- accepted record 必须填写 `review.confidence`；rejected record 使用 `review.confidence=null` 并写清楚拒绝原因。
- Process 阶段不移动 inbox 文件，只更新 YAML 字段。
- 只有 record 文件创建成功后，才能将 inbox item 更新为 `status: archive`；失败时保持 `status: pending`。
- 具体执行步骤使用 `assets/process-inbox.prompt.md`。

## Maintenance Review

当用户要求 review 系统时：

- 识别 stale sources
- 识别 duplicate sources
- 找出长期停留在 `status: pending` 的 inbox items
- 找出可能应清理或重新处理的 `status: draft` inbox items
- 检查 `status: archive` 的 inbox items 是否都有对应 record
- 找出缺少 required fields 或 review 状态不完整的 records
