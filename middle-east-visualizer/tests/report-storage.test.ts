import { mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { describe, expect, test } from "vitest";

import { saveRawReport } from "../src/lib/report-file";

describe("saveRawReport", () => {
  test("writes the incoming report text into the raw store", () => {
    const root = mkdtempSync(join(tmpdir(), "mev-"));
    const report = "日期：2026-03-29\n\n概率：\n- 升级：35%\n";

    const target = saveRawReport(root, report, "今日中东局势分析");

    expect(target.endsWith("2026-03-29-今日中东局势分析.md")).toBe(true);
    expect(readFileSync(target, "utf8")).toBe(report);
  });
});
