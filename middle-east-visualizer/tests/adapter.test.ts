import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, test } from "vitest";

import { parseSkillOutput } from "../src/lib/adapter";

const fixture = (name: string) =>
  readFileSync(join(process.cwd(), "tests", "fixtures", name), "utf8");

describe("parseSkillOutput", () => {
  test("parses a daily report into one analysis record and timeline events", () => {
    const result = parseSkillOutput(fixture("daily-report.md"), "daily-report.md");

    expect(result.records).toHaveLength(1);
    expect(result.records[0]).toMatchObject({
      asOf: "2026-03-23",
      probabilities: {
        escalation: 38,
        stalemate: 47,
        deescalation: 15
      },
      summary: {
        primaryScenario: "stalemate"
      }
    });
    expect(result.records[0].summary.mainLogic.length).toBeGreaterThan(0);
    expect(result.events.length).toBeGreaterThan(0);
    expect(result.events[0]?.impact).toBe("escalation");
  });

  test("normalizes alias probability labels", () => {
    const result = parseSkillOutput(fixture("alias-report.md"), "alias-report.md");

    expect(result.records[0]?.probabilities).toEqual({
      escalation: 30,
      stalemate: 45,
      deescalation: 25
    });
  });

  test("parses a backtest table into historical analysis records", () => {
    const result = parseSkillOutput(fixture("backtest-report.md"), "backtest-report.md");

    expect(result.records).toHaveLength(3);
    expect(result.records.map((record) => record.asOf)).toEqual([
      "2026-02-27",
      "2026-02-28",
      "2026-03-02"
    ]);
    expect(result.records[2]?.summary.primaryScenario).toBe("escalation");
    expect(result.events).toHaveLength(3);
  });
});
