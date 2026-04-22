# Layout

## Scope

这个 skill 只使用当前 skill 项目内的顶层目录，不负责创建独立信息系统脚手架，也不支持用户自定义根目录。

## Top-Level Layout

```text
personal-info-collector/
  topics/
    <topic-id>/
      sources.yaml
  inbox/
    input-<topic-id>-YYYY-MM-DD-NNN.yaml
  records/
    record-<topic-id>-YYYY-MM-DD-NNN.yaml
```

## Topic Layout

topic 目录只负责来源配置：

```text
topics/
  <topic-id>/
    sources.yaml
```

所有路径都相对于 `personal-info-collector/` skill 项目根目录。

## Topic IDs

topic ID 使用稳定的 lower-kebab-case：

- `ai-investing`
- `middle-east-war`
- `public-figures`
- `semiconductor-supply-chain`

避免日期、空格，以及 `misc` 这类过于模糊的名字。

## Inbox Files

每条收集到的原材料使用一个 YAML inbox 文件：

```text
inbox/input-<topic-id>-YYYY-MM-DD-NNN.yaml
```

状态写在文件内部：

```yaml
status: pending # pending | draft | archive
```

- `pending`：待处理。
- `draft`：已丢弃、不处理。
- `archive`：已处理并审核过，应该有对应 record。

同一个 inbox 文件在整个生命周期内路径保持不变，只更新 `status` 和相关处理字段。

## Record Files

每条被处理/审核过的 inbox item 生成一个 YAML record 文件：

```text
records/record-<topic-id>-YYYY-MM-DD-NNN.yaml
```

文件名日期优先使用发布时间；没有发布时间时使用收集日期。Record 可以是审核通过，也可以是审核拒绝。
