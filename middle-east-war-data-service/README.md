# middle-east-war-data-service

`middle-east-war-data-service` 是 `notes -> trend` 之间唯一可信的数据层。

它当前不负责自动从新闻里“算出”权重，而是负责把分析后的 `actor + factor` 判断保存为带时间维度的标准快照，并稳定提供两类输出：

1. 某个时间点最近有效的标准快照
2. 旧版 `middle-east-war-long-term-trend` 可直接消费的兼容场景数据

## 1. 系统结构理解

基于 [/Users/benliu/Documents/Invest/middle-east-war-system-design.md](/Users/benliu/Documents/Invest/middle-east-war-system-design.md)，当前系统应拆成三层：

1. `middle-east-war-note`
   原始证据层，只负责记录和管理新闻、推文、航运、航空等原始信息。
2. `middle-east-war-data-service`
   核心中间层，负责把 notes 支撑的人工/AI 分析结果，固化为带 `as_of` 的结构化快照。
3. `middle-east-war-long-term-trend`
   推理层，不再回头读 notes，只消费 data service 快照并复用旧算法骨架。

这意味着 v1 的关键不是“让 trend 更复杂”，而是先把快照生产和查询标准化。

## 2. 文档里不够明确的点与最小补充方案

当前设计文档已经给出主方向，但还有 4 个实现层缺口需要补齐：

1. `notes` 的物理格式未定义。
   最小补充：v1 不自动解析 notes 内容，只要求快照写入时显式带上 `source_notes`。
2. `data service` 的“分析过程”如何进入代码未定义。
   最小补充：v1 先把“分析后结构化结果”当成 service 的写入输入，service 负责校验、存储、查询，不负责自动抽取。
3. 快照文件命名规则未定义。
   最小补充：用精确时间戳文件名，`as_of` 仍是唯一事实来源，查询不依赖人工序号。
4. 新快照权重是 `0-5`，旧 trend 仍要求 `0-100`。
   最小补充：`0-5` 保持为 data service 的规范存储，兼容导出时统一乘以 `20` 转成旧结构。

## 3. 最小输入输出接口

### 写入接口

最小写入单位就是一份已经分析完成的快照：

```yaml
as_of: 2026-04-19T09:00:00+08:00
source_notes:
  - note-2026-04-19-01
actors:
  - actor: 美国
    actor_weight: 4
    factors:
      - id: us_avoid_regional_war
        text: 避免中东全面失控
        kind: core
        weight: 5
        direction: 僵持
```

也就是：

- 输入不是原始新闻文本
- 输入是“已经完成分析的结构化快照草案”
- `source_notes` 只是证据引用，不要求 service 自己回推内容

### 读取接口

v1 只保留两个读取能力：

1. `get_snapshot(as_of)`：
   返回 `as_of` 时点最近且不晚于该时点的有效快照。
2. `export_legacy_scenario(as_of)`：
   返回旧版 `middle-east-war-long-term-trend/analyzer.py` 可直接读取的 JSON 结构。

### 当前实现的 CLI

```bash
python3 /Users/benliu/Documents/Invest/middle-east-war-data-service/service.py \
  get \
  --state-dir /Users/benliu/Documents/Invest/middle-east-war-data-service/state \
  --as-of 2026-04-19T12:00:00+08:00
```

```bash
python3 /Users/benliu/Documents/Invest/middle-east-war-data-service/service.py \
  export-legacy \
  --state-dir /Users/benliu/Documents/Invest/middle-east-war-data-service/state
```

```bash
python3 /Users/benliu/Documents/Invest/middle-east-war-data-service/service.py \
  put \
  --state-dir /Users/benliu/Documents/Invest/middle-east-war-data-service/state \
  /Users/benliu/Documents/Invest/middle-east-war-data-service/state/current.yaml
```

## 4. v1 快照文件结构与按日期查询逻辑

### 目录结构

```text
middle-east-war-data-service/
├── service.py
├── state/
│   ├── current.yaml
│   └── snapshots/
│       └── 2026-04-19T09-00-00+0800.yaml
└── tests/
```

### 快照规范字段

顶层：

- `as_of`
  带时区的 ISO 8601 时间，是真实查询主键。
- `source_notes`
  本次快照引用的 note id 列表。
- `actors`
  当前时点的 actor 快照列表。

`actors[]`：

- `actor`
- `actor_weight`
  `0-5` 粗粒度影响等级。
- `factors`

`factors[]`：

- `id`
  稳定机器 id。
- `text`
  给人看的 factor 文本。
- `kind`
  v1 固定为 `core | stage`。
- `weight`
  `0-5` 粗粒度重要度等级。
- `direction`
  `缓和 | 僵持 | 升级`

### 查询规则

`get_snapshot(as_of)` 的规则固定为：

1. 枚举 `state/snapshots/*.yaml`
2. 读取每份快照的 `as_of`
3. 过滤出 `snapshot.as_of <= query_as_of`
4. 返回其中时间最近的一份
5. 若没有任何候选，抛出 `LookupError`

`current.yaml` 只代表“目前已知最新快照”，不是独立数据源。

## 5. 旧版 long-term-trend 的最小兼容字段

旧版 [/Users/benliu/Documents/Invest/middle-east-war-long-term-trend/analyzer.py](/Users/benliu/Documents/Invest/middle-east-war-long-term-trend/analyzer.py) 当前最小需要：

```json
{
  "name": "scenario-name",
  "actor_profiles": [
    {
      "actor": "美国",
      "actor_weight": 80,
      "factors": [
        {
          "name": "避免中东全面失控",
          "weight": 100,
          "direction": "僵持"
        }
      ]
    }
  ]
}
```

因此真正不能丢的兼容字段只有：

- 顶层：`name`、`actor_profiles`
- actor：`actor`、`actor_weight`、`factors`
- factor：`name`、`weight`、`direction`

新快照和旧结构之间有两个明确差异：

1. 新结构用 `text`，旧结构用 `name`
2. 新结构权重是 `0-5`，旧结构权重是 `0-100`

当前实现里由 `export_legacy_scenario()` 统一做这层适配：

- `text -> name`
- `grade * 20 -> legacy weight`

## 6. 最小可用实现方案

v1 只做四件事：

1. 校验快照字段是否合法
2. 把快照写入 `state/snapshots/` 并维护 `current.yaml`
3. 按 `as_of` 查询最近有效快照
4. 导出旧 trend 可直接消费的兼容 JSON

这版实现刻意不做：

- 自动从 notes 抽取 actor/factor
- 变化日志
- 复杂索引
- 多下游共享协议

## 7. 验证

运行：

```bash
python3 -m unittest discover \
  -s /Users/benliu/Documents/Invest/middle-east-war-data-service/tests \
  -p 'test_*.py'
```

当前测试覆盖：

- 快照保存与 `current.yaml` 更新
- 按日期查询最近有效快照
- 查询早于首份快照时抛错
- `0-5 -> 0-100` 兼容转换
- 导出结果可被旧 `analyzer.py` 直接消费
