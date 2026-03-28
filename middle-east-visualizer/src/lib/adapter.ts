import type { AnalysisRecord, EventStrength, Scenario, TimelineEvent } from "../types";

const PROBABILITY_LABELS: Record<string, Scenario> = {
  "升级": "escalation",
  "战争持续升级": "escalation",
  "持久战": "stalemate",
  "长期持久战": "stalemate",
  "缓和": "deescalation",
  "战争逐渐缓和": "deescalation"
};

export function parseSkillOutput(text: string, sourceName: string) {
  const normalized = text.replace(/\r\n/g, "\n").trim();
  const records = normalized.includes("概率时间表：")
    ? parseBacktestReport(normalized, sourceName)
    : [parseDailyReport(normalized, sourceName)];

  return {
    records,
    events: records.flatMap((record) => extractTimelineEvents(record))
  };
}

function parseDailyReport(text: string, sourceName: string): AnalysisRecord {
  const asOf = matchRequired(text, /^日期：([0-9-]+)$/m, "日期");
  const probabilities = parseProbabilityBlock(text);
  const primaryScenario = parsePrimaryScenario(
    stripBullet(matchSection(text, "主场景").split("\n")[0] ?? ""),
    probabilities
  );
  const mainLogic = parseBullets(matchSection(text, "主逻辑"));
  const largestUncertainty = parseBullets(matchSection(text, "最大变数"))[0] ?? "未提供";

  return {
    analysisId: buildAnalysisId(sourceName, asOf),
    asOf,
    probabilities,
    summary: {
      primaryScenario,
      headline: parseHeadline(primaryScenario, probabilities),
      mainLogic,
      largestUncertainty
    },
    raw: { text }
  };
}

function parseBacktestReport(text: string, sourceName: string): AnalysisRecord[] {
  const table = matchSection(text, "概率时间表");
  const rows = table
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.startsWith("|") && !line.includes("---"));
  const pivotNotes = parseBullets(matchSection(text, "拐点说明"));

  return rows.slice(1).map((row) => {
    const cells = row
      .split("|")
      .map((cell) => cell.trim())
      .filter(Boolean);
    const [asOf, escalationRaw, stalemateRaw, deescalationRaw, primaryLabel] = cells;
    const mainLogic = pivotNotes.find((note) => note.startsWith(asOf))
      ? [pivotNotes.find((note) => note.startsWith(asOf)) ?? ""]
      : ["来自回测表格导入"];

    return {
      analysisId: buildAnalysisId(sourceName, asOf),
      asOf,
      probabilities: {
        escalation: parsePercent(escalationRaw),
        stalemate: parsePercent(stalemateRaw),
        deescalation: parsePercent(deescalationRaw)
      },
      summary: {
        primaryScenario: normalizeScenario(primaryLabel),
        headline: parseHeadline(normalizeScenario(primaryLabel), {
          escalation: parsePercent(escalationRaw),
          stalemate: parsePercent(stalemateRaw),
          deescalation: parsePercent(deescalationRaw)
        }),
        mainLogic,
        largestUncertainty: "回测记录未提供单独最大变数"
      },
      raw: { text }
    };
  });
}

function parseProbabilityBlock(text: string) {
  const block = matchSection(text, "概率");
  const probabilities: Partial<Record<Scenario, number>> = {};

  for (const bullet of parseBullets(block)) {
    const match = bullet.match(/^(.+?)：\s*(\d+)%$/);
    if (!match) continue;
    const scenario = PROBABILITY_LABELS[match[1].trim()];
    if (!scenario) continue;
    probabilities[scenario] = Number(match[2]);
  }

  if (
    probabilities.escalation === undefined ||
    probabilities.stalemate === undefined ||
    probabilities.deescalation === undefined
  ) {
    throw new Error("概率区块缺少必要字段");
  }

  return probabilities as Record<Scenario, number>;
}

function extractTimelineEvents(record: AnalysisRecord): TimelineEvent[] {
  const candidates = record.summary.mainLogic.filter((line) => line.includes("信息层："));
  const sourceLines = candidates.length > 0 ? candidates : record.summary.mainLogic.slice(0, 1);

  return sourceLines.map((line, index) => {
    const summary = line.replace(/^信息层：/, "").trim();
    const impact = inferImpact(summary, record.summary.primaryScenario);
    const strength = inferStrength(summary);

    return {
      eventId: `${record.analysisId}-event-${index + 1}`,
      analysisId: record.analysisId,
      date: record.asOf,
      title: buildEventTitle(summary, impact),
      summary,
      impact,
      strength,
      sourceText: line
    };
  });
}

function buildEventTitle(summary: string, impact: Scenario) {
  const title = summary.split(/[，。；]/)[0]?.trim() ?? summary;
  if (title.length > 0) return title;
  return impact === "escalation"
    ? "升级信号增强"
    : impact === "deescalation"
      ? "缓和信号出现"
      : "持久战信号延续";
}

function inferImpact(summary: string, fallback: Scenario): Scenario {
  if (/(升级|升温|强化|风险抬升|威慑|增兵|打击)/.test(summary)) {
    return "escalation";
  }
  if (/(缓和|停火|谈判|修复|回撤)/.test(summary)) {
    return "deescalation";
  }
  if (/(持续|僵持|未确认|偏弱|预警)/.test(summary)) {
    return "stalemate";
  }
  return fallback;
}

function inferStrength(summary: string): EventStrength {
  if (/(明显|大范围|强确认|全面|共振|非常明确)/.test(summary)) {
    return "strong";
  }
  if (/(持续|开始|抬升|强化|偏紧)/.test(summary)) {
    return "medium";
  }
  return "weak";
}

function parseHeadline(primaryScenario: Scenario, probabilities: Record<Scenario, number>) {
  const label =
    primaryScenario === "escalation"
      ? "升级"
      : primaryScenario === "deescalation"
        ? "缓和"
        : "持久战";
  return `${label}为主场景，升级 ${probabilities.escalation}% / 持久战 ${probabilities.stalemate}% / 缓和 ${probabilities.deescalation}%`;
}

function normalizeScenario(input: string): Scenario {
  if (/(升级)/.test(input)) return "escalation";
  if (/(缓和)/.test(input)) return "deescalation";
  return "stalemate";
}

function parsePrimaryScenario(
  input: string,
  probabilities: Record<Scenario, number>
): Scenario {
  if (/(持久战仍是主场景|持久战偏强|持久战仍领先|长期持久战)/.test(input)) {
    return "stalemate";
  }
  if (/(升级成为主场景|升级已开始占优|主场景：?\s*升级|^升级[。；，]?)/.test(input)) {
    return "escalation";
  }
  if (/(缓和成为主场景|主场景：?\s*缓和|^缓和[。；，]?)/.test(input)) {
    return "deescalation";
  }

  const ordered = Object.entries(probabilities).sort((left, right) => right[1] - left[1]);
  return ordered[0]?.[0] as Scenario;
}

function parseBullets(block: string) {
  return block
    .split("\n")
    .map((line) => stripBullet(line).trim())
    .filter(Boolean);
}

function stripBullet(line: string) {
  return line.replace(/^-+\s*/, "").trim();
}

function matchSection(text: string, title: string) {
  const headingPattern = /^([^\s\-|`][^：\n]*?)：$/gm;
  const headings = Array.from(text.matchAll(headingPattern)).map((match) => ({
    title: match[1],
    index: match.index ?? 0,
    length: match[0].length
  }));
  const current = headings.find((heading) => heading.title === title);
  if (!current) {
    throw new Error(`缺少区块: ${title}`);
  }
  const next = headings.find((heading) => heading.index > current.index);
  const start = current.index + current.length + 1;
  const end = next?.index ?? text.length;
  return text.slice(start, end).trim();
}

function matchRequired(text: string, pattern: RegExp, label: string) {
  const match = text.match(pattern);
  if (!match?.[1]) {
    throw new Error(`缺少字段: ${label}`);
  }
  return match[1].trim();
}

function buildAnalysisId(sourceName: string, asOf: string) {
  const safeSource = sourceName.replace(/[^a-zA-Z0-9]+/g, "-").replace(/^-|-$/g, "");
  return `${asOf}-${safeSource}`.toLowerCase();
}

function parsePercent(value: string) {
  const match = value.match(/(\d+)%/);
  if (!match) {
    throw new Error(`无法解析百分比: ${value}`);
  }
  return Number(match[1]);
}
