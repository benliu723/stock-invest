# Collect Topic Prompt

用于为单个 topic 收集候选信息。

```text
Collect new information candidates for topic: <topic-id>.

Inputs:
- Topic directory: topics/<topic-id>
- Sources file: topics/<topic-id>/sources.yaml
- Inbox directory: inbox/

Instructions:
1. 读取 sources.yaml，并遵循 topic purpose、source notes 和 source url_type。
2. 只检查未禁用的 sources；`enabled` 缺省视为 true。
3. 读取全部 inbox/*.yaml，按 candidate.url、标题和明显相同的内容摘要检查重复；不论 status 是 pending、draft 还是 archive，只要已存在就不要重复写入。
4. 对 current/latest information，必须基于每个 source 的 url 和 url_type 实际访问来源；url_type=page 时读取页面，url_type=feed 时读取 RSS/Atom feed。
5. 保留 source URL 作为来源入口；优先保留 candidate URL、publication timestamps、source name 和访问失败原因。
6. 按 inbox item schema 将每条非重复 candidate 写成一个 YAML 文件，保存到 inbox/input-<topic-id>-YYYY-MM-DD-NNN.yaml。
7. 新建 inbox item 必须设置 status: pending。
8. 如可获得，包含 short summaries、key points 和 short excerpts。
9. 对 skipped、inaccessible、failed 或 duplicate candidates 记录原因。
10. 未知字段标记为 unknown 或使用 null。
11. 不要写入 records。
12. 不要修改已有 inbox item 的 status。
13. 不要依赖记忆，不要编造 source details、quotes、dates 或 authors。

After writing the inbox, summarize:
- sources checked
- candidates added
- skipped, failed, or duplicate candidates
```
