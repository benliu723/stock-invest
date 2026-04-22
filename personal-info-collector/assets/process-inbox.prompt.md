# Process Inbox Prompt

用于处理 `status: pending` 的 inbox item：丢弃则改为 `status: draft`；正式审核则生成 record 并改为 `status: archive`。

```text
Process pending inbox item for topic: <topic-id>.

Inputs:
- Topic directory: topics/<topic-id>
- Inbox item file: inbox/input-<topic-id>-YYYY-MM-DD-NNN.yaml
- Records directory: records/

Instructions:
1. 读取 inbox item YAML。
2. 只处理 status: pending 的 item；如果不是 pending，停止并报告当前 status。
3. 只做两类处理决定：draft 或 record。
4. 如果决定不处理、想丢弃，将该 inbox item 的 status 更新为 draft，并填写 processing.processed_at 和 processing.decision_reason；不要创建 record。
5. 如果决定正式审核，创建一个 YAML record。
6. record 内部必须设置 review.status：accepted 或 rejected。
7. accepted record 必须填写 review.confidence，rejected record 使用 review.confidence=null 并写清楚 reason。
8. 只有 record 文件创建成功后，才能将 inbox item 的 status 更新为 archive，并填写 processing.record_id、processing.record_path、processing.processed_at、processing.decision_reason。
9. Process 阶段不要移动 inbox 文件。
10. 使用 stable record IDs。
11. record 只通过 reviewed_from 引用 inbox item，不复制 inbox item 中的 source 和 candidate。
12. 原始 URL、title、publication time 和 collection time 以 reviewed_from 指向的 inbox item 为准；record 只写审核结论和 normalized 摘要、要点、tags、entities、短 excerpt 或处理 notes。
13. summaries 保持事实性。
14. excerpts 保持简短。
15. 不要编造缺失字段；使用 unknown 或 null。
16. 如果 record 创建或写入失败，保持 inbox item 为 status: pending，并报告失败原因。
17. 报告 inbox item 的新 status；如果创建 record，报告 record path 和 accepted/rejected 状态。

写入 record 或更新 inbox item 前先请求确认，除非用户已经明确授权处理这个 pending item。
```
