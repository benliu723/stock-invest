---
name: middle-east-war-trend
description: Analyze Middle East war trends with a three-layer probability model. Use this skill whenever the user wants to track, assess, or compare escalation risk in the Middle East, especially for daily war trend updates, scenario probabilities, military news interpretation, aviation or shipping disruption analysis, Brent-led market confirmation, or turning conflict signals into "escalation / stalemate / de-escalation" style judgments.
---

# Middle East War Trend

Use this skill to turn daily conflict information into a structured scenario view.

The goal is to output probabilities for three scenarios:
- `escalation`
- `stalemate`
- `de-escalation`

The working model has three layers:
- `information layer`
- `facts layer`
- `market layer`

Default weights:
- information `30%`
- facts `40%`
- market `30%`

## When to use

Use this skill when the user asks for any of the following:
- daily Middle East war trend analysis
- probability of escalation vs prolonged war vs easing tensions
- interpretation of military headlines, official statements, or troop movements
- interpretation of aviation, shipping, Strait of Hormuz, airspace, or port disruption
- interpretation of Brent crude and related war-risk pricing
- a repeatable template for tracking conflict changes over time
- backtesting, trend charts, probability history, or date-by-date comparison
- data provenance, source tracing, evidence review, or follow-up questions about where a judgment came from

Do not use this skill for generic investing advice unless the user explicitly wants the war-trend judgment first.

## Core principle

Do not rely on one signal alone.

Use three layers together:
1. `information layer` asks: what do public signals imply?
2. `facts layer` asks: what has actually changed in real-world operations?
3. `market layer` asks: what is the market already pricing?

Treat the model as a probability engine, not a certainty engine.

## Response modes

Choose the lightest mode that satisfies the user.

- `daily mode`
  - use for normal daily judgment
  - output the three probabilities, primary scenario, main logic, and largest uncertainty

- `audit mode`
  - use when the user asks for data sources, evidence, why a probability was assigned, or wants to challenge a conclusion
  - include `关键依据` and `来源清单`

- `backtest mode`
  - use when the user asks for date-by-date review, trend comparison, backtesting, charts, or historical scenario evolution
  - include a date table, probability changes, and chart-ready series

## Layer definitions

### 1. Information layer

Purpose:
- judge whether public information suggests the direction of conflict is changing

Typical inputs:
- Reuters
- AP
- official government statements
- military statements
- credible journalist reporting

Key idea:
- assess `credibility + impact`

Scoring anchors:
- `0`: no effective signal
- `1`: weak or noisy signal
- `2`: early usable signal
- `3`: clear signal
- `4`: strong multi-source signal
- `5`: extremely strong signal, usually official and already consequential

Discipline:
- do not give `4-5` from a single unconfirmed headline
- if evidence conflicts, reduce the score by one notch
- if unsure, score lower rather than higher

### 2. Facts layer

Purpose:
- judge whether conflict is visibly disrupting real-world operations

Typical inputs:
- flight cancellations
- rerouting
- airspace closures
- shipping delays or diversions
- port restrictions
- Strait of Hormuz or Red Sea operating status

Key idea:
- assess `real-world disruption intensity`

Scoring anchors:
- `0`: normal operations
- `1`: light disruption
- `2`: widening disruption but still functioning
- `3`: clear operational disruption
- `4`: strong broad disruption
- `5`: effective breakdown or severe interruption in key routes

Discipline:
- facts outrank headlines when they conflict
- do not give high scores without operational evidence
- short-lived anomalies should not be treated as full-system disruption

### 3. Market layer

Purpose:
- judge whether the market is pricing a war scenario

Typical inputs:
- Brent crude
- war-risk insurance
- freight or tanker costs
- broad risk-off behavior if relevant

Key idea:
- assess `pricing intensity`

Scoring anchors:
- `0`: little or no pricing response
- `1`: light move
- `2`: early pricing response
- `3`: clear pricing response
- `4`: strong pricing response with reinforcement
- `5`: shock-like pricing

Discipline:
- avoid high scores from one asset alone unless the move is truly exceptional
- if macro factors unrelated to war appear dominant, reduce confidence
- the market layer confirms or warns, but should not dominate by itself

## Scenario mapping

Score each layer separately for all three scenarios.

### Escalation

Usually supported by signals like:
- troop buildup
- direct strikes
- retaliatory waves
- energy infrastructure attacks
- evacuation upgrades
- major airspace or shipping deterioration
- sharp Brent upside repricing

### Stalemate

Usually supported by signals like:
- conflict continues without decisive expansion or settlement
- repeated attacks or threats, but no clear breakthrough
- persistent disruption that remains costly but not fully broken
- Brent stays elevated rather than explosively repricing higher

### De-escalation

Usually supported by signals like:
- ceasefire progress
- credible negotiation progress
- force drawdowns
- restored routes or fewer restrictions
- easing war-risk premium and softer Brent

Use a higher confirmation bar for `de-escalation` than for `escalation`.

## Conflict handling rules

When layers disagree, use these defaults:

- `information strong, facts weak`
  - treat as warning, not full confirmation
  - raise escalation modestly, not aggressively

- `facts strong, information weak`
  - trust facts first
  - reality can outrun the news cycle

- `market strong, information and facts weak`
  - treat as market front-running
  - raise risk modestly and wait for confirmation

- `de-escalation headlines appear, but facts and market do not repair`
  - do not switch to de-escalation quickly
  - keep stalemate or escalation dominant until reality improves

- `all three layers align`
  - confidence is high

- `all three layers split`
  - lean toward `stalemate`

One-line rule:
- when signals agree, follow direction; when they conflict, trust facts; when the picture fragments, lean stalemate

## Calculation method

For each scenario, calculate:

- `scenario score = 0.3 * information + 0.4 * facts + 0.3 * market`

Then normalize the three scenario scores so total probability equals `100%`.

## Evidence ledger and source tracing

When external information is used, maintain a compact evidence ledger.

Source ID format:
- `S1`, `S2`, `S3` for source items
- `D1`, `D2`, `D3` for explicit data points if helpful

Preferred source types:
- Reuters
- AP
- official government or military statements
- airline, airport, shipping, port, or insurer notices
- Brent or market data providers used in the session

Rules:
- tie each major judgment to at least one source ID when sources are available
- separate `headline` evidence from `operational` evidence when possible
- if a score is inferred rather than directly observed, say so clearly
- if the user asks "why" or "source?", answer by mapping the conclusion back to the relevant `S#` and `D#` items
- in `audit mode`, do not leave major conclusions untagged; use explicit `S#`, and use `D#` or `C#` when mapping data points or conclusions
- if using generic source categories instead of concrete links, still keep the numbering stable so the user can ask follow-up questions about `S1`, `S2`, `D1`, or `C1`

When the user wants source transparency, add:

```text
关键依据：
- [S1] ...
- [S2] ...

来源清单：
- [S1] Source name - what it supports
- [S2] Source name - what it supports
```

If no clean source is available, say that the point is an inference rather than pretending it is sourced.

Audit-mode discipline:
- if the answer contains `关键依据`, it should also contain a numbered `来源清单`
- if the answer contains a major conclusion like "持久战概率更高", map it to at least one `S#`
- if the user wants to challenge a judgment, make the answer easy to audit line by line rather than giving only broad prose

## Default workflow

Follow this order:
1. gather the best available public inputs for the day or requested time window
2. summarize each layer in one sentence
3. assign 0-5 scores for `escalation`, `stalemate`, and `de-escalation` in each layer
4. check for layer conflict
5. calculate weighted totals
6. normalize into probabilities
7. explain the dominant scenario and largest uncertainty
8. if the user asks for sources, attach an evidence ledger
9. if the user asks for backtesting, convert the date series into a trend table and chart-ready output

## Preferred input template

Use or infer this structure when possible:

```text
Date: YYYY-MM-DD

Information layer: escal x, stalemate x, de-escal x; one sentence
Facts layer: escal x, stalemate x, de-escal x; one sentence
Market layer: escal x, stalemate x, de-escal x; one sentence
```

If the user does not supply scores, infer them from the evidence and say so.

## Preferred output template

Use this structure unless the user asks for something else:

```text
日期：YYYY-MM-DD

概率：
- 升级：xx%
- 持久战：xx%
- 缓和：xx%

主场景：
- ...

主逻辑：
- ...

最大变数：
- ...
```

## Audit-mode add-on

When the user asks for data or sources, append:

```text
关键依据：
- [S1] ...
- [S2] ...

来源清单：
- [S1] 来源名称；用途
- [S2] 来源名称；用途
```

## Backtest mode

Use backtest mode when the user asks for probability history, trend charts, historical comparisons, or wants to review multiple days together.

Backtest input can be:
- a list of dates with already-scored layers
- a list of dates with already-calculated probabilities
- a request to reconstruct dates from evidence in the same framework

Backtest output should contain:
- `回测区间`
- `趋势结论`
- `概率时间表`
- `拐点说明`
- `图表数据`

Preferred backtest template:

```text
回测区间：YYYY-MM-DD 至 YYYY-MM-DD

趋势结论：
- ...

概率时间表：
| 日期 | 升级 | 持久战 | 缓和 | 主场景 |
| --- | --- | --- | --- | --- |
| YYYY-MM-DD | xx% | xx% | xx% | ... |

拐点说明：
- YYYY-MM-DD：...

图表数据：
日期,升级,持久战,缓和
YYYY-MM-DD,xx,xx,xx
```

## Visualization handoff

When the user asks for a current or historical Middle East conflict analysis, append a final `可视化：` section unless the user explicitly says not to.

Use this exact structure:

```text
可视化：
- 入口：[http://localhost:4173](http://localhost:4173)
- 用途：查看历史三场景概率曲线与信息层重点事件时间线
- 同步本次分析：cd /Users/benliu/Documents/Playground/middle-east-visualizer && pbpaste | npm run sync-report -- --label "今日中东局势分析"
```

Rules:
- keep the `可视化：` section at the very end of the answer
- do not rename the localhost URL unless the user provides a different local deployment address
- if the analysis is not "today", replace the label text inside `--label` with the user-requested date or topic
- if the user asks not to include operational commands, keep only the `入口` and `用途` lines

Chart support rules:
- default to a markdown table plus a CSV-style block the user can plot later
- if the user explicitly wants an in-chat chart, provide a simple ASCII trend chart in addition to the table
- do not invent missing dates; if the series is incomplete, say so
- preserve the same scoring framework across all dates in the backtest
- do not auto-fill intermediate dates unless the user explicitly asks for interpolation or reconstruction
- if the user names specific dates, only output those dates unless you clearly label any added dates as inferred
- if a date is missing evidence, omit it or mark it as missing rather than fabricating a clean probability row

## Style guidance

- keep the result concise and decision-oriented
- distinguish between `headline risk` and confirmed operational change
- be explicit when a score is inferred rather than directly observed
- do not overstate confidence when evidence is thin or conflicting
- if the user later wants investment implications, first finish the war-trend judgment cleanly
- when sources are requested, make the evidence chain easy to audit
- when backtesting, optimize for comparability across dates rather than prose length

## Example interpretation patterns

### Pattern A: information strong, facts weak

Example outcome:
- escalation rises
- stalemate remains competitive
- de-escalation stays low

Reason:
- the system is seeing warning signals, not full confirmation

### Pattern B: three layers aligned toward escalation

Example outcome:
- escalation dominates strongly

Reason:
- public information, real-world disruption, and market pricing are all pointing the same way

### Pattern C: de-escalation headline without recovery

Example outcome:
- de-escalation rises only slightly
- stalemate often remains the base case

Reason:
- rhetoric softened before operations normalized

### Pattern D: backtest and source follow-up

Example outcome:
- output a date table, trend summary, turning points, and source-tagged evidence

Reason:
- the user is not only asking for a judgment, but also for replayability and auditability
