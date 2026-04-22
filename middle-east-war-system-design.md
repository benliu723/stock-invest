# 中东战争长期趋势系统设计文档

## 文档目的

本文件用于给新的 Codex 窗口提供统一背景、设计目标与实现边界，避免重新解释上下文。

## 一句话定义

这套系统不是直接从新闻推导长期战争结论，而是先通过 `notes + data service` 生成带时间维度的结构化博弈方数据，再由 `long-term-trend` 基于这些数据推理长期战争趋势。

## 背景与旧项目痛点

旧版 `middle-east-war-long-term-trend` 的核心问题，不是算法骨架本身，而是它直接依赖：

- `actor_weight`
- `factor.weight`

但这些值缺少可靠的数据生产过程，因此容易陷入“精度陷阱”：

- 看起来严谨
- 实际输入不稳
- 容易把主观判断伪装成精确参数

本次新设计的核心目标，就是补上这段缺失的数据生产链路。

## 设计目标

1. 保留旧版 `middle-east-war-long-term-trend` 的算法骨架与兼容数据结构。
2. 不再让 `trend` 直接处理原始信息。
3. 新增 `notes` 和 `data service` 两层，负责从信息到结构化输入的转换。
4. 将原本伪精确的权重，降级为 `0-5` 的粗粒度等级。
5. 让系统支持按时间查询某个时间点的结构化博弈方数据。

## 总体架构

```text
middle-east-war-note
-> middle-east-war-data-service
-> middle-east-war-long-term-trend
```

也可理解为：

```text
原始信息
-> notes 收集与管理
-> data service 分析并生成 actor/factor 快照
-> long-term-trend 基于快照推理长期战争趋势
```

## 模块职责

### 1. `middle-east-war-note`

职责：

- 负责信息管理
- 记录新闻、Twitter、航空、航运、博客等信息
- 支持手动补充信息
- 当前阶段不共享给其他系统，只为 `data service` 服务
- 不直接产出长期趋势结论

定位：

- 原始证据层

### 2. `middle-east-war-data-service`

职责：

- 是系统核心
- 负责读取 `notes`
- 内部包含分析过程，不再单独拆出 `analysis` 项目
- 通过人工观察、推理、与 AI 辅助讨论，生成结构化博弈方数据
- 维护带时间维度的 `actor + factor` 快照
- 对外提供“某个时间点的数据快照”查询服务
- 为 `long-term-trend` 提供唯一标准输入

定位：

- 中间数据生成/服务层
- 是整套系统最核心的模块

### 3. `middle-east-war-long-term-trend`

职责：

- 不管理原始信息
- 不直接读取 `notes`
- 只读取 `data service` 提供的快照
- 复用旧算法骨架
- 输出长期战争趋势判断

定位：

- 趋势推理层
- 相对较薄，重点在消费 `data service` 的结果

## 核心设计原则

1. `data service` 是唯一可信的数据层。
2. `trend` 只消费 `data service` 的快照，不回头读取 `notes`。
3. 系统不再追求精确权重，而只保留粗粒度等级。
4. 这是“受约束的主观判断系统”，不是客观精确模型。
5. 当前优先目标是打通 `notes -> data service -> trend` 主链路，不追求过早抽象与共享。

## 数据模型设计

### 1. 对 `trend` 的输出快照

`middle-east-war-data-service` 对 `long-term-trend` 的输出应尽量自包含，并兼容旧版算法结构：

```yaml
as_of: 2026-04-19T09:00:00+08:00
source_notes:
  - note-2026-04-19-01
  - note-2026-04-19-02

actors:
  - actor: 美国
    actor_weight: 4
    factors:
      - id: us_avoid_regional_war
        text: 避免中东全面失控
        kind: core
        weight: 5
        direction: 僵持
      - id: us_prevent_iran_nuclear
        text: 阻止伊朗拥核
        kind: core
        weight: 4
        direction: 升级

  - actor: 伊朗
    actor_weight: 4
    factors:
      - id: iran_preserve_regime_security
        text: 避免政权安全受损
        kind: core
        weight: 5
        direction: 僵持
      - id: iran_retaliate_against_israel
        text: 对以色列进行反击
        kind: stage
        weight: 4
        direction: 升级
```

### 2. 字段语义

- `actor_weight`
  - 范围：`0-5`
  - 含义：该 actor 当前阶段的影响等级
  - 不是精确客观权重

- `weight`
  - 范围：`0-5`
  - 含义：该 factor 当前的重要度等级
  - 不是精确因素权重

- `0`
  - 当前不参与推理

- `3`
  - 默认中性值

- `kind`
  - 建议至少区分：
    - `core`
    - `stage`

- `direction`
  - 保留给旧版 `trend` 算法使用

## 时间维度设计

v1 推荐以“时间快照”作为主存储，因为它最简单，也最适合与旧算法直接对接。

建议目录：

```text
state/
├── snapshots/
│   ├── 2026-04-19-01.yaml
│   ├── 2026-04-20-01.yaml
│   └── ...
└── current.yaml
```

说明：

- `snapshots/`
  - 保存历史快照
- `current.yaml`
  - 保存最新快照
- 按日期查询时
  - 返回目标时间点最近的一份有效快照

说明：

- v1 不强制实现变化日志
- 若后续需要更细粒度的变更追踪，再增加 change log

## 完整流程

1. `middle-east-war-note` 收集原始信息。
2. `middle-east-war-data-service` 读取相关 notes。
3. `data service` 内部完成观察、推理与结构化判断。
4. `data service` 生成某时间点的 `actor + factor` 快照并落库。
5. `middle-east-war-long-term-trend` 读取该快照。
6. `long-term-trend` 运行旧算法骨架。
7. 输出长期战争趋势。

## 为什么这版设计更合理

相对于旧版：

- 保留了旧版最有价值的部分：结构化推理算法
- 修复了旧版最致命的问题：权重无从而来
- 不再追求伪精确，而是接受粗粒度判断
- 把真正困难的问题放在 `data service` 层解决
- 一旦 `data service` 走通，`long-term-trend` 就会变轻

## 非目标

本设计当前不追求：

- 自动学习出客观真实权重
- 高精度长期预测
- 一开始就构建完美 factor 库
- 当前阶段让 `notes` 同时服务多个下游系统

## 实现优先级

1. 先实现 `middle-east-war-note`
2. 再实现 `middle-east-war-data-service`
3. 最后改造 `middle-east-war-long-term-trend` 对接快照

## 当前结论

当前系统真正的核心不是 `middle-east-war-long-term-trend`，而是 `middle-east-war-data-service`。

只要 `data service` 能稳定地产生带时间维度的 `actor + factor` 快照，`long-term-trend` 基本就能顺利落地。

## 给新 Codex 窗口的直接任务建议

若在新窗口中继续推进，建议优先做以下事情：

1. 细化 `middle-east-war-data-service` 的输入输出接口
2. 定义快照文件结构与按日期查询逻辑
3. 再确认旧版 `middle-east-war-long-term-trend` 需要的最小兼容字段
4. 最后开始实现最小可用版本
