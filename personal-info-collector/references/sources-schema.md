# Sources Schema

`sources.yaml` 是 topic 的数据源列表，用于 prompt / program crawler 的输入。当前阶段字段保持精简，优先保证人和 agent 都容易维护。

## File Shape

```yaml
---
topic:
  id: ai-investing
  name: AI Investing
  purpose: 关注会影响 AI 基础设施、平台公司、芯片、软件和公开市场投资判断的信息。
sources: []
```

添加 source 时使用：

```yaml
sources:
  - id: reuters-ai
    name: Reuters AI coverage
    type: news
    url: https://www.reuters.com/technology/
    url_type: page
    notes: 关注 AI、芯片、云和大科技公司相关新闻。
```

## Topic Fields

- `id`：稳定的 lower-kebab-case topic ID。
- `name`：人类可读名称。
- `purpose`：这个 topic 为什么存在、重点关注什么。

## Source Fields

必填：

- `id`：稳定的 lower-kebab-case 标识，在当前 topic 内唯一。
- `name`：人类可读的来源名称，可以表示文章来源、发布机构、具体栏目、feed 或页面名，例如 `AP News`、`Reuters AI coverage`、`Stratechery`。
- `type`：来源类别。
- `url`：来源主页、feed、列表页或规范入口。
- `url_type`：URL 类型，只能是 `page` 或 `feed`。

可选：

- `notes`：说明关注什么、忽略什么、为什么重要。
- `enabled`：布尔值；缺省视为 `true`。只有需要暂时停用 source 时才写。

## Source Types

使用少量宽泛类型：

- `news`
- `blog`
- `official`
- `social`
- `research`
- `manual`

如果拿不准，用最接近的类型，不要为单个来源发明新类型。

## URL Types

- `page`：普通网页入口。收集时访问页面，并从页面内容中识别最近更新。
- `feed`：RSS 或 Atom feed。收集时读取 feed 条目，并从条目中识别最近更新。

## Maintenance Rules

- 不要过早把 `sources.yaml` 写成复杂程序爬虫配置；先保持 prompt 爬虫也容易理解。
- 需要关键词、登录说明、频率等细节时，先写进 `notes`。
- 合并重复 source 时，保留最稳定的 URL，并迁移有价值的 notes。
- 初始化 topic 时不要擅自写入 starter sources；可以提出建议，但写入前必须得到用户确认。
- 不要把 credentials、API keys、cookies 或 private tokens 放进 `sources.yaml`。
