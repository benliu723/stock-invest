# Inbox Item Schema

Inbox 文件是 YAML。每个文件只保存一条收集到的原材料，并通过 `status` 表达状态。

## File Name

```text
input-<topic-id>-YYYY-MM-DD-NNN.yaml
```

## Schema

```yaml
---
id: input-ai-investing-2026-04-21-001
topic: ai-investing
status: pending
captured_at: '2026-04-21T09:00:00+08:00'
source:
  id: stratechery
  name: Stratechery
  url: https://stratechery.com
  author: unknown
candidate:
  title: Example title
  url: https://stratechery.com/example-title
  published_at: '2026-04-20T18:30:00-04:00'
  type: blog_post
  relevance: high
  summary: 原材料摘要。
  key_points:
    - 关键点。
  excerpt: Short source excerpt, if available.
collection_notes: 访问限制、不确定性、重复风险或收录原因。
processing:
  record_id: null
  record_path: null
  processed_at: null
  decision_reason: null
```

## Status Values

- `pending`：待处理。
- `draft`：决定丢弃，不进入正式审核。
- `archive`：已经正式审核，并应有对应 record。

## Required Fields

- `id`
- `topic`
- `status`
- `captured_at`
- `source.id`
- `source.name`
- `source.url`
- `candidate.title`
- `candidate.url`
- `candidate.summary`

## Rules

- 一个 inbox 文件只保存一条原材料。
- 收集阶段新建 inbox item 时，必须设置 `status: pending`。
- `source.url` 是来源入口 URL；`candidate.url` 是具体文章、帖子、公告或条目的 URL。
- 收集阶段必须读取全部 `inbox/*.yaml` 做去重；只要 `candidate.url` 或明显同一内容已存在，不论 status 是什么，都不要重复写入。
- Process 阶段不要移动文件；只更新 `status` 和 `processing` 字段。
- 决定丢弃时，设置 `status: draft`，并填写 `processing.processed_at` 和 `processing.decision_reason`。
- 正式审核并创建 record 后，设置 `status: archive`，并填写 `processing.record_id`、`processing.record_path`、`processing.processed_at` 和 `processing.decision_reason`。
- 未知字段标记为 `unknown` 或使用 `null`，不要猜。
- excerpt 保持简短，并保留 source link。
