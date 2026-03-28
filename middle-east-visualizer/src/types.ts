export type Scenario = "escalation" | "stalemate" | "deescalation";
export type EventStrength = "weak" | "medium" | "strong";

export interface AnalysisRecord {
  analysisId: string;
  asOf: string;
  probabilities: Record<Scenario, number>;
  summary: {
    primaryScenario: Scenario;
    headline: string;
    mainLogic: string[];
    largestUncertainty: string;
  };
  raw: {
    text: string;
  };
}

export interface TimelineEvent {
  eventId: string;
  analysisId: string;
  date: string;
  title: string;
  summary: string;
  impact: Scenario;
  strength: EventStrength;
  sourceText: string;
  sourceUrl?: string;
}

export interface VisualizationDataset {
  latest: AnalysisRecord;
  series: AnalysisRecord[];
  events: TimelineEvent[];
}
