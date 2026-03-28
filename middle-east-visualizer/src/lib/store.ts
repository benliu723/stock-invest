import type { AnalysisRecord, TimelineEvent, VisualizationDataset } from "../types";

export function buildDataset(
  records: AnalysisRecord[],
  events: TimelineEvent[]
): VisualizationDataset {
  const series = [...records].sort((left, right) => left.asOf.localeCompare(right.asOf));
  if (series.length === 0) {
    throw new Error("No analysis records found");
  }

  const sortedEvents = [...events].sort((left, right) => {
    const dateOrder = right.date.localeCompare(left.date);
    if (dateOrder !== 0) return dateOrder;
    return right.eventId.localeCompare(left.eventId);
  });

  return {
    latest: series[series.length - 1],
    series,
    events: sortedEvents
  };
}
