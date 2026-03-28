import { mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { basename, join, resolve } from "node:path";

import { parseSkillOutput } from "../src/lib/adapter";
import { buildDataset } from "../src/lib/store";
import type { AnalysisRecord, TimelineEvent } from "../src/types";

const projectRoot = process.cwd();
const rawDir = resolve(projectRoot, "data", "raw");
const outputDir = resolve(projectRoot, "public", "data");
const outputFile = join(outputDir, "dataset.json");

const files = readdirSync(rawDir).filter((file) => file.endsWith(".md"));
const allRecords: AnalysisRecord[] = [];
const allEvents: TimelineEvent[] = [];

for (const file of files) {
  const text = readFileSync(join(rawDir, file), "utf8");
  const parsed = parseSkillOutput(text, basename(file, ".md"));
  allRecords.push(...parsed.records);
  allEvents.push(...parsed.events);
}

mkdirSync(outputDir, { recursive: true });
writeFileSync(outputFile, JSON.stringify(buildDataset(allRecords, allEvents), null, 2));

console.log(`Wrote ${outputFile}`);
