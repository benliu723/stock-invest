---
name: personal-info-collector
description: Use when the user wants to maintain, collect, process, or automate topic-based personal information sources, inbox items, and reviewed records for news, blogs, public statements, research materials, or watchlists.
---

# Personal Info Collector

## Overview

使用这个 skill 维护个人信息收集系统：按 topic 管理 sources，收集原材料到 inbox，并将处理过的信息沉淀为 reviewed records。

## Core Model

```text
sources.yaml -> collect -> inbox/*.yaml(status: pending)
inbox item -> discard -> status: draft
           -> review  -> records/*.yaml + status: archive
```

- `topics/<topic-id>/sources.yaml` 是 topic 的数据源列表，用于 prompt / program crawler 的输入。
- `inbox/*.yaml` 保存原材料；`status` 表示 `pending`、`draft` 或 `archive`。
- `records/` 保存已经处理/审核过的记录；record 可以是 `accepted`，也可以是 `rejected`。

## First Step

行动前先判断用户意图：

| Intent | Use |
| --- | --- |
| 创建或维护 topic | `references/layout.md`, `references/sources-schema.md` |
| 确定数据源 | `references/source-selection.md`, `references/workflows.md`, `references/sources-schema.md` |
| 添加、删除、审阅 sources | `references/source-selection.md`, `references/sources-schema.md` |
| 收集最新信息 | `references/workflows.md`, `assets/collect-topic.prompt.md` |
| 处理 inbox item | `references/workflows.md`, `references/record-schema.md`, `assets/process-inbox.prompt.md` |
| 设置定时自动化 | `references/automation.md` |

## Operating Rules

- 所有数据只使用当前 skill 项目内的 `topics/`、`inbox/`、`records/`。
- 收集只创建 `status: pending` 的 inbox item；处理阶段才更新 inbox status 或创建 record。
- Collect 必须按 `candidate.url` 扫描全部 `inbox/*.yaml` 去重。
- Records 是审核记录，不等于完全可用数据；后续使用时应过滤 `review.status` 和 `review.confidence`。
- 对最新/当前信息，必须基于 `sources.yaml` 中的 `url` 和 `url_type` 实际访问来源；不要依赖记忆，不要编造来源字段。

## References

- `references/layout.md`：目录结构和命名规则。
- `references/source-selection.md`：数据源获取、筛选和确认规则。
- `references/sources-schema.md`：数据源列表字段和示例。
- `references/inbox-format.md`：inbox item schema 和 status 规则。
- `references/record-schema.md`：已处理/已审核 record 的 schema。
- `references/workflows.md`：创建、维护、收集、处理流程边界。
- `references/automation.md`：Codex 自动化指导。
- `assets/collect-topic.prompt.md`：可复用的信息收集 prompt。
- `assets/process-inbox.prompt.md`：可复用的 inbox 处理 prompt。
