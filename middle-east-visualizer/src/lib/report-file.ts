import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";

export function extractAsOfDate(text: string, fallbackDate = todayIsoDate()) {
  const match = text.match(/^日期：([0-9-]+)$/m);
  return match?.[1] ?? fallbackDate;
}

export function buildRawReportFilename(asOf: string, label = "report") {
  const slug = slugify(label);
  return `${asOf}-${slug || "report"}.md`;
}

export function saveRawReport(projectRoot: string, text: string, label = "report") {
  const asOf = extractAsOfDate(text);
  const filename = buildRawReportFilename(asOf, label);
  const target = join(projectRoot, "data", "raw", filename);

  mkdirSync(dirname(target), { recursive: true });
  writeFileSync(target, text.endsWith("\n") ? text : `${text}\n`);

  return target;
}

function slugify(input: string) {
  return input
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^\p{Letter}\p{Number}]+/gu, "-")
    .replace(/^-+|-+$/g, "")
    .toLowerCase();
}

function todayIsoDate() {
  return new Date().toISOString().slice(0, 10);
}
