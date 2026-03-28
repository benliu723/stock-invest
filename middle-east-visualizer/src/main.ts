import "./styles.css";

import type { AnalysisRecord, Scenario, TimelineEvent, VisualizationDataset } from "./types";

const impactLabels: Record<Scenario, string> = {
  escalation: "推升升级",
  stalemate: "支持持久战",
  deescalation: "支持缓和"
};

const scenarioLabels: Record<Scenario, string> = {
  escalation: "升级",
  stalemate: "持久战",
  deescalation: "缓和"
};

const app = document.querySelector<HTMLDivElement>("#app");

async function bootstrap() {
  if (!app) return;

  const response = await fetch("/data/dataset.json");
  const dataset = (await response.json()) as VisualizationDataset;

  app.innerHTML = `
    <main class="page">
      <section class="hero">
        <div>
          <p class="eyebrow">Middle East Conflict Visualizer</p>
          <h1>中东冲突分析首版可视化</h1>
          <p class="subtitle">聚焦历史概率对比与信息层重点事件，不把模型判断淹没在大段文本里。</p>
        </div>
        ${renderLatest(dataset.latest)}
      </section>
      <section class="panel">
        <div class="panel-head">
          <div>
            <p class="eyebrow">Probability History</p>
            <h2>历史三场景概率</h2>
          </div>
        </div>
        ${renderChart(dataset.series)}
      </section>
      <section class="panel">
        <div class="panel-head">
          <div>
            <p class="eyebrow">Signal Timeline</p>
            <h2>信息层重点事件</h2>
          </div>
        </div>
        ${renderTimeline(dataset.events)}
      </section>
    </main>
  `;
}

function renderLatest(record: AnalysisRecord) {
  return `
    <div class="latest-card">
      <div class="latest-head">
        <span class="chip">${record.asOf}</span>
        <span class="chip chip-${record.summary.primaryScenario}">${scenarioLabels[record.summary.primaryScenario]}</span>
      </div>
      <h2>${record.summary.headline}</h2>
      <div class="prob-grid">
        ${renderProbabilityCell("升级", record.probabilities.escalation)}
        ${renderProbabilityCell("持久战", record.probabilities.stalemate)}
        ${renderProbabilityCell("缓和", record.probabilities.deescalation)}
      </div>
      <div class="latest-copy">
        <p><strong>主逻辑：</strong>${record.summary.mainLogic[0] ?? "未提供"}</p>
        <p><strong>最大变数：</strong>${record.summary.largestUncertainty}</p>
      </div>
    </div>
  `;
}

function renderProbabilityCell(label: string, value: number) {
  return `
    <div class="prob-cell">
      <span>${label}</span>
      <strong>${value}%</strong>
    </div>
  `;
}

function renderChart(series: AnalysisRecord[]) {
  const width = 960;
  const height = 360;
  const padding = 44;
  const innerWidth = width - padding * 2;
  const innerHeight = height - padding * 2;
  const maxPoints = Math.max(series.length - 1, 1);
  const x = (index: number) => padding + (innerWidth / maxPoints) * index;
  const y = (value: number) => padding + innerHeight - (value / 100) * innerHeight;

  const scenarios: Array<{ key: Scenario; color: string }> = [
    { key: "escalation", color: "#c74634" },
    { key: "stalemate", color: "#3e5ec9" },
    { key: "deescalation", color: "#2d8f62" }
  ];

  const grid = [0, 25, 50, 75, 100]
    .map((value) => {
      const yPos = y(value);
      return `
        <line x1="${padding}" y1="${yPos}" x2="${width - padding}" y2="${yPos}" class="grid-line" />
        <text x="8" y="${yPos + 4}" class="axis-label">${value}%</text>
      `;
    })
    .join("");

  const lines = scenarios
    .map(({ key, color }) => {
      const points = series
        .map((record, index) => `${x(index)},${y(record.probabilities[key])}`)
        .join(" ");
      const dots = series
        .map(
          (record, index) => `
            <circle cx="${x(index)}" cy="${y(record.probabilities[key])}" r="4" fill="${color}">
              <title>${record.asOf} ${scenarioLabels[key]} ${record.probabilities[key]}%</title>
            </circle>
          `
        )
        .join("");

      return `<polyline fill="none" stroke="${color}" stroke-width="3" points="${points}" />${dots}`;
    })
    .join("");

  const xLabels = series
    .map(
      (record, index) =>
        `<text x="${x(index)}" y="${height - 12}" text-anchor="middle" class="axis-label">${record.asOf.slice(5)}</text>`
    )
    .join("");

  return `
    <div class="chart-wrap">
      <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="历史三场景概率趋势图">
        ${grid}
        ${lines}
        ${xLabels}
      </svg>
      <div class="legend">
        <span><i class="swatch escalation"></i>升级</span>
        <span><i class="swatch stalemate"></i>持久战</span>
        <span><i class="swatch deescalation"></i>缓和</span>
      </div>
    </div>
  `;
}

function renderTimeline(events: TimelineEvent[]) {
  if (events.length === 0) {
    return `<p class="empty">当前没有可展示的信息层重点事件。</p>`;
  }

  return `
    <div class="timeline">
      ${events
        .map(
          (event) => `
            <article class="timeline-item">
              <div class="timeline-marker timeline-marker-${event.impact}"></div>
              <div class="timeline-body">
                <div class="timeline-meta">
                  <span class="chip">${event.date}</span>
                  <span class="chip chip-${event.impact}">${impactLabels[event.impact]}</span>
                  <span class="chip">${event.strength}</span>
                </div>
                <h3>${event.title}</h3>
                <p>${event.summary}</p>
                <p class="source">来源片段：${event.sourceText}</p>
              </div>
            </article>
          `
        )
        .join("")}
    </div>
  `;
}

void bootstrap();
