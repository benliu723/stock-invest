# Source Selection Design

## Context

`personal-info-collector` currently keeps source selection simple: the agent proposes candidate sources, the user confirms which ones to add, and accepted sources are written to `topics/<topic-id>/sources.yaml`.

That flow is workable, but it leaves the most important judgment implicit: whether the proposed sources match the intended direction of the topic. If the topic direction is wrong or too broad, later collection and processing optimizations will not fix the output quality.

The goal is to improve source acquisition and confirmation rules without making the early-stage workflow heavy.

## Design Goals

- Keep source selection lightweight enough for early use.
- Make source direction explicit before sources enter `sources.yaml`.
- Reduce drift from broad news or generic AI sources.
- Allow each topic to narrow global source rules without inventing a full scoring system.
- Preserve the current `sources.yaml -> inbox -> records` lifecycle.

## Non-Goals

- No source scoring model.
- No source lifecycle states beyond the existing `enabled` field.
- No automated source discovery pipeline.
- No mandatory trial-run workflow before adding a source.
- No complex crawler configuration in `sources.yaml`.

## Proposed Model

Add two layers of source selection guidance.

### Global Source Policy

Create a global source selection guide in the `personal-info-collector` skill, likely at:

```text
personal-info-collector/references/source-selection.md
```

This guide defines rules that apply to every topic:

- Prefer RSS or Atom feeds when available; use stable pages when feeds are not available.
- Prefer primary sources, official pages, research publications, open-source project pages, and vertical industry sources.
- Generic broad news pages are not accepted by default unless they fill a clear gap.
- Single articles, search results, temporary landing pages, and one-off announcements are not valid sources.
- Every source candidate must state the direction it serves, its quality class, expected signal, and risk.

### Topic Source Brief

Each topic may define a short source brief next to `sources.yaml`:

```text
personal-info-collector/topics/<topic-id>/source-brief.md
```

The brief narrows the global policy for that topic. It should stay short and use a fixed shape:

```markdown
# Source Brief: <topic-id>

## Focus
What this topic is primarily about.

## Include
- Source or content types that belong in this topic.

## Exclude
- Source or content types that should not be added even if broadly related.

## Keywords
Relevant terms that help judge source fit.
```

For `ai-robotics`, the brief should make robotics, embodied AI, physical AI, robot commercialization, and robotics supply chain the center of gravity. Generic AI product launches, enterprise SaaS agent news, and ordinary model API updates should be excluded unless they clearly connect to robotics or physical AI.

### Source Candidate Output

When the agent proposes source candidates, it must read both:

- `references/source-selection.md`
- `topics/<topic-id>/source-brief.md`, if present

Candidate output should use a compact shape:

```yaml
name:
url:
url_type:
matched_global_rule:
matched_topic_rule:
source_quality: primary | vertical | aggregator
expected_signal:
risk:
recommendation: include | maybe | exclude
```

Only `include` candidates should be written to `sources.yaml` after user confirmation. `maybe` candidates are not written by default. `exclude` candidates are shown only to explain why they should not be used.

## Workflow Changes

The existing "Determine Sources" workflow should change from:

1. Agent proposes sources.
2. User accepts or rejects each source.
3. Accepted sources are written to `sources.yaml`.

To:

1. Agent reads the global source policy.
2. Agent reads or drafts the topic source brief.
3. User confirms the topic source brief if it is new or materially changed.
4. Agent proposes source candidates using the compact candidate shape.
5. User confirms only the `include` candidates to write.
6. Agent writes confirmed sources to `sources.yaml`.

This keeps confirmation lightweight while making topic direction explicit.

## Data Flow

```text
references/source-selection.md
        +
topics/<topic-id>/source-brief.md
        |
        v
source candidate recommendations
        |
        v
user confirms include candidates
        |
        v
topics/<topic-id>/sources.yaml
        |
        v
collect -> inbox/*.yaml
```

## Error Handling

- If the topic has no `source-brief.md`, the agent should draft one before proposing sources.
- If the user does not want a topic brief, the agent may proceed with only the global policy, but should state that source direction is less constrained.
- If a candidate matches the global policy but conflicts with the topic brief, it should be marked `exclude` or `maybe`, not `include`.
- If no strong candidates are found, the agent should report that rather than filling `sources.yaml` with weak sources.

## Testing And Review

Add focused eval coverage for:

- Proposing sources with both global policy and topic brief.
- Rejecting generic broad sources when the topic brief excludes them.
- Drafting a missing topic source brief before source proposal.
- Writing only confirmed `include` candidates to `sources.yaml`.

Manual review should check that `ai-robotics` source proposals prioritize robotics and physical AI rather than general AI platform news.
