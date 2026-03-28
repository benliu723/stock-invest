import { readFileSync, } from "node:fs";
import { resolve } from "node:path";
import { stdin as input } from "node:process";

import { saveRawReport } from "../src/lib/report-file";

async function main() {
  const projectRoot = process.cwd();
  const rawDir = resolve(projectRoot, "data", "raw");
  const args = process.argv.slice(2);

  const label = readFlag(args, "--label") ?? "today-report";
  const fileArg = findPositionalArg(args, new Set(["--label"]));
  const text = fileArg ? readFileSync(resolve(projectRoot, fileArg), "utf8") : await readStdin();

  if (!text.trim()) {
    throw new Error("No report text provided");
  }

  const target = saveRawReport(projectRoot, text, label);

  console.log(target);
}

function readFlag(args: string[], name: string) {
  const index = args.indexOf(name);
  if (index === -1) return undefined;
  return args[index + 1];
}

function findPositionalArg(args: string[], flagsWithValue: Set<string>) {
  for (let index = 0; index < args.length; index += 1) {
    const value = args[index];
    if (value.startsWith("--")) {
      if (flagsWithValue.has(value)) {
        index += 1;
      }
      continue;
    }
    return value;
  }
  return undefined;
}

function readStdin() {
  return new Promise<string>((resolvePromise, rejectPromise) => {
    let chunks = "";
    input.setEncoding("utf8");
    input.on("data", (chunk) => {
      chunks += chunk;
    });
    input.on("end", () => resolvePromise(chunks));
    input.on("error", rejectPromise);
  });
}

void main();
