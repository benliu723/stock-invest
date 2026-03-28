import { describe, expect, test } from "vitest";

import { buildDataset } from "../src/lib/store";
import type { AnalysisRecord, TimelineEvent } from "../src/types";

const records: AnalysisRecord[] = [
  {
    analysisId: "a-1",
    asOf: "2026-02-27",
    probabilities: { escalation: 41, stalemate: 47, deescalation: 12 },
    summary: {
      primaryScenario: "stalemate",
      headline: "持久战仍为基准场景",
      mainLogic: ["信息强但事实弱"],
      largestUncertainty: "事实层是否补位"
    },
    raw: { text: "first" }
  },
  {
    analysisId: "a-2",
    asOf: "2026-03-02",
    probabilities: { escalation: 63, stalemate: 30, deescalation: 7 },
    summary: {
      primaryScenario: "escalation",
      headline: "升级成为主场景",
      mainLogic: ["三层接近同向"],
      largestUncertainty: "外部强干预"
    },
    raw: { text: "second" }
  }
];

const events: TimelineEvent[] = [
  {
    eventId: "e-1",
    analysisId: "a-1",
    date: "2026-02-27",
    title: "公开信号偏紧",
    summary: "公开信号偏紧",
    impact: "stalemate",
    strength: "medium",
    sourceText: "公开信号偏紧"
  }
];

describe("buildDataset", () => {
  test("sorts records and selects latest summary data", () => {
    const dataset = buildDataset(records, events);

    expect(dataset.latest.analysisId).toBe("a-2");
    expect(dataset.series.map((item) => item.asOf)).toEqual([
      "2026-02-27",
      "2026-03-02"
    ]);
  });

  test("keeps timeline usable when some records have no events", () => {
    const dataset = buildDataset(records, events);

    expect(dataset.events).toHaveLength(1);
    expect(dataset.events[0]?.analysisId).toBe("a-1");
  });
});
