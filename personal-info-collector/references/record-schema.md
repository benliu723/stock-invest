# Record Schema

Records 是对 inbox 原材料进行处理/审核后产生的结构化 YAML 文件。Record 不等于“完全可用的数据”；它表示“这条信息已经被审核过”，审核结果可以是 `accepted` 或 `rejected`。

Record 只引用 inbox 原材料，不复制 `source` 和 `candidate`。原材料细节以 `reviewed_from` 指向的 inbox item 为准。

## File Name

```text
record-<topic-id>-YYYY-MM-DD-NNN.yaml
```

## Schema

```yaml
---
id: record-ai-investing-2026-04-21-001
topic: ai-investing
type: blog_post
created_at: '2026-04-21T09:30:00+08:00'
reviewed_from: inbox/input-ai-investing-2026-04-21-001.yaml
review:
  status: accepted
  confidence: 4
  reason: 来源可信，主题相关性高，信息对 AI 云基础设施投资判断有参考价值。
normalized:
  summary: 文章讨论模型平台化可能如何改变云厂商的商业模式。
  tags:
    - ai-infrastructure
    - cloud
  entities:
    people: []
    companies:
      - Microsoft
      - OpenAI
    technologies:
      - large language models
  key_points:
    - First durable point.
    - Second durable point.
  excerpt: Short source excerpt, if available.
  notes: Optional processing notes.
```

审核拒绝的 record 也使用同一个 schema：

```yaml
---
id: record-ai-investing-2026-04-21-002
topic: ai-investing
type: news_article
created_at: '2026-04-21T09:40:00+08:00'
reviewed_from: inbox/input-ai-investing-2026-04-21-002.yaml
review:
  status: rejected
  confidence: null
  reason: 来源主要是二次转载，缺少原始出处，且与当前 topic 相关性弱。
normalized: null
```

## Required Fields

- `id`
- `topic`
- `type`
- `created_at`
- `reviewed_from`
- `review.status`
- `review.reason`

## Review Status

- `accepted`：审核通过，可以作为后续研究输入；必须填写 `review.confidence`。
- `rejected`：已审核但拒绝，不作为后续研究输入；`review.confidence` 使用 `null`。

## Confidence

`review.confidence` 使用 `0-5`：

- `0`：几乎不可用，仅保留审核轨迹。
- `1-2`：低置信度，需要强人工复核。
- `3`：中等置信度，可作为弱信号。
- `4`：高置信度，可作为研究输入。
- `5`：很高置信度，通常来自一手来源或高度可信来源。

## Rules

- 每条被正式审核的 pending input 都应产生一条 record。
- Record 必须追溯回原 inbox item：`reviewed_from` 指向 `inbox/input-*.yaml`。
- 审核通过不代表绝对真实，只代表在当前流程中可用，并带有置信度。
- 审核拒绝的信息仍然可以产生 record，因为它也是一条明确的审核结果。
- `normalized` 只用于 `accepted` record；`rejected` record 可设为 `null`。
- 写入新 record 前，检查现有 `records/` 中是否已有相同 `reviewed_from`。
- 创建 record 文件成功后，才能把对应 inbox item 更新为 `status: archive`。
- 除非用户提供全文且有明确理由，不要保存完整版权文章；优先保存摘要和短 excerpt。
