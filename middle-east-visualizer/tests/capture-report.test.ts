import { describe, expect, test } from "vitest";

import { buildRawReportFilename, extractAsOfDate } from "../src/lib/report-file";

describe("report-file helpers", () => {
  test("extracts the report date from daily output", () => {
    const text = `日期：2026-03-29\n\n概率：\n- 升级：35%`;

    expect(extractAsOfDate(text)).toBe("2026-03-29");
  });

  test("falls back to today when the text does not contain 日期", () => {
    const text = "回测区间：2026-02-27 至 2026-03-02";

    expect(extractAsOfDate(text, "2026-03-29")).toBe("2026-03-29");
  });

  test("builds a stable raw report filename", () => {
    expect(buildRawReportFilename("2026-03-29", "今日中东局势分析")).toBe(
      "2026-03-29-今日中东局势分析.md"
    );
  });
});
