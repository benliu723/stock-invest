# middle-east-war-note

`middle-east-war-note` 是中东战争长期趋势系统的证据采集与存储层。

MVP 只聚焦 note 层本身：把手写笔记升级为原子 `evidence`，并提供订阅式抓取入口，降低人工复制新闻和人物言论的成本。它不负责生成长期趋势结论，也不设计下游 `data service` 的消费规则。

## MVP 边界

当前实现做：

1. 原子 `evidence` 的校验、保存和读取
2. 三类 evidence：`statement`、`news`、`personal_note`
3. 固定订阅源配置 `sources.yaml`
4. RSS / 简单页面列表抓取
5. 元数据级导入：标题、链接、发布时间、来源、摘要
6. URL 去重
7. 所有自动导入 evidence 默认 `confidence=3`

当前实现不做：

- 日聚合
- 三段状态
- 全文抓取
- 自动关键词搜索
- 复杂反爬
- AI 自动分类
- 跨模块消费逻辑

## Evidence Schema

统一字段：

```yaml
id: evidence-ap-middle-east-4f4d6d9e7d20
type: news
captured_at: '2026-04-19T09:00:00+08:00'
event_at: '2026-04-19T08:30:00+08:00'
confidence: 3
summary: US officials said additional forces arrived in the region.
source:
  id: ap-middle-east
  name: AP Middle East
  url: https://example.com/ap/story-1
  feed_url: https://example.com/ap/rss
details:
  headline: US adds forces in the Middle East
  outlet: AP Middle East
  key_points:
    - US officials said additional forces arrived in the region.
```

字段说明：

- `id`
  evidence 主键，必须以 `evidence-` 开头。
- `type`
  `statement | news | personal_note`。
- `captured_at`
  系统采集/录入时间，必须带时区。
- `event_at`
  新闻发布时间或言论发生时间，可为空。
- `confidence`
  `0-5`，自动导入默认 `3`。
- `summary`
  元数据级摘要；RSS 缺摘要时 fallback 为标题。
- `source`
  本条 evidence 的来源。
- `details`
  按 `type` 存放少量专属字段。

`details` 规则：

- `statement`: `speaker`、`quote`、`context`
- `news`: `headline`、`outlet`、`key_points[]`
- `personal_note`: `note_text`、`basis`

## Source Config

订阅源配置位于：

```text
/Users/benliu/Documents/Invest/middle-east-war-note/sources.yaml
```

格式：

```yaml
sources:
  - id: ap-middle-east
    name: AP Middle East
    kind: news_source
    url: https://example.com/ap/rss
    enabled: false
    parser: rss
    default_confidence: 3
```

字段：

- `kind=statement_source` 会生成 `statement`
- `kind=news_source` 会生成 `news`
- `parser=rss` 解析 RSS / Atom
- `parser=page` 解析简单 HTML 链接列表
- `enabled=false` 的来源不会抓取
- `url_contains` 可限制页面链接路径
- `title_contains` 可限制标题关键词，避免页面导航和无关新闻进入 evidence
- `max_items` 可限制单个 source 每次最多导入多少条

没有稳定入口的核心来源可以先放在配置里并关闭，不阻塞 MVP。

## CLI

保存一条手写 evidence：

```bash
python3 /Users/benliu/Documents/Invest/middle-east-war-note/note_service.py \
  put \
  --evidence-dir /Users/benliu/Documents/Invest/middle-east-war-note/evidence \
  /path/to/evidence.yaml
```

读取 evidence：

```bash
python3 /Users/benliu/Documents/Invest/middle-east-war-note/note_service.py \
  get \
  --evidence-dir /Users/benliu/Documents/Invest/middle-east-war-note/evidence \
  evidence-manual-personal-note-2026-04-19-01
```

从启用的订阅源导入：

```bash
python3 /Users/benliu/Documents/Invest/middle-east-war-note/note_service.py \
  import-subscriptions \
  --evidence-dir /Users/benliu/Documents/Invest/middle-east-war-note/evidence \
  --sources /Users/benliu/Documents/Invest/middle-east-war-note/sources.yaml
```

## Legacy Notes

`notes/` 中的旧 `note-*` 文件是前一版轻量 note 的历史兼容数据。新 MVP 的核心数据目录是 `evidence/`。

## Verification

```bash
python3 -m unittest discover \
  -s /Users/benliu/Documents/Invest/middle-east-war-note/tests \
  -p 'test_*.py'
```
