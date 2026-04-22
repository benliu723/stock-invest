# Automation Guidance

当用户希望定时收集、提醒处理 inbox，或周期性 review sources 时，使用 Codex automations。

## Default Automation Behavior

- 如果用户希望延续当前对话上下文，优先使用 thread heartbeat。
- 如果用户希望在 workspace 中运行独立定时任务，使用 cron automation。
- 定时收集默认只创建 `status: pending` 的 inbox YAML。
- 除非用户明确授权 auto-processing，否则不要自动创建 records。

## Collection Automation Prompt Shape

automation prompt 只描述任务本身，不要把 schedule details 写进 prompt。

推荐 prompt：

```text
Use the personal-info-collector workflow to collect new candidates for the <topic-id> topic. Read the topic's sources.yaml, check sources that are not disabled for relevant new public information by using each source's url and url_type, deduplicate against all inbox YAML files regardless of status using candidate.url first, write each new candidate as one status: pending YAML item in inbox, include skipped or failed sources with reasons, and do not write records.
```

## Processing Automation Prompt Shape

只有当用户希望周期性清理 inbox 时，才使用 processing automation：

```text
Use the personal-info-collector workflow to process pending inbox YAML items for the <topic-id> topic. For each pending item, choose draft or record. If draft, update the inbox item status to draft and fill processing.processed_at and processing.decision_reason. If record, write a record with review.status accepted or rejected, include confidence for accepted records, then update the inbox item status to archive and fill processing.record_id, processing.record_path, processing.processed_at, and processing.decision_reason. Ask for confirmation before writing records or updating inbox status unless prior authorization is already documented.
```

## Safety Defaults

- 每次运行都打开一个 pending inbox item 或给出运行报告。
- 报告访问失败和跳过的 sources。
- 不要在 prompts、sources 或 automation config 中保存 credentials 和 private data。
- 如果目标 inbox 或 record 文件已存在，选择下一个编号文件；不要覆盖。
- 除处理阶段明确更新 `status` 和 `processing` 字段外，不要修改已有 inbox 文件。
