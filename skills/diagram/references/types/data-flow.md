# Type: data-flow

## Purpose
Show how data moves: sources → transformations → sinks. Each arrow carries a payload type, volume, or rate. Audience: data engineers, analysts.

## When to use
Trigger words:
- "data flow", "pipeline", "ETL", "ELT", "ingestion"
- "sources / sinks", "transformations"
- mentions of upstream/downstream, batching, streaming

## Visual conventions
- Source: cylinder OR external-system box (dashed border) at the left edge
- Transformation node: rounded rectangle service
- Sink: cylinder (warehouse) or service-shape (dashboard)
- Buffer / queue: horizontal pipe shape
- Arrow labels: payload format + volume/rate (e.g. `JSON · 1k/s`, `Avro · batch`)

## Layout direction
**Left → right.** Upstream on the left, downstream on the right. Optional vertical fan-out for parallel sinks.

## Level of detail
Include: every node where data is transformed/persisted, payload format, volume hint when known.
Exclude: schema details, retention policies (link out instead).

## Image-prompt template
```
Technical data-flow diagram, flat vector, left-to-right pipeline. Calm aesthetic, clean lines.

Sources: {sources}
Transformations: {transformations}
Sinks: {sinks}
Connections (with payload labels): {relationships}

Style: the surface background color, primary-color borders, accent color highlights on key transformations, muted color for grouping. Solid arrows for sync, dashed for async/streaming. 2px primary lines.

Typography: sans-serif for node names, monospace for payload labels (JSON, Avro, Parquet, k/s). 14pt minimum.

Layout: strict left-to-right. Sources at x≈0–15%, transformations in the middle, sinks at x≈85–100%. Buffer/queue shapes between transformations when batching is implied. ≥40px breathing room. ≤15 elements.

Do NOT invent sources or sinks. Do NOT use rainbow colors. Maximum 5 colors total.
```

## SVG-prompt template
```
Output ONLY valid SVG 1.1 per the SVG contract. Layer ordering: boundaries → services → connections → labels. Use class names .service, .datastore, .queue, .external-system, .connection-sync, .connection-async.

Sources: {sources}
Transformations: {transformations}
Sinks: {sinks}
Connections (with payload labels above arrows): {relationships}

viewBox="0 0 1600 900". Strict left-to-right flow. <style> block with style-tokens colors. <defs> arrow markers. Payload labels in monospace via class="code".
```

## Golden examples

### Example 1
**User input:** "Kafka topic 'events' → Spark streaming job aggregates by user_id → writes to ClickHouse → Grafana dashboard reads"
**Refined image prompt (excerpt):**
> Data-flow diagram, flat vector, left-to-right. Source: Kafka pipe shape (left, label "events"). Transformation: Spark service (center, accent highlight, label "streaming job, group by user_id"). Sink 1: ClickHouse cylinder (right). Sink 2: Grafana service (far right). Arrows: Kafka → Spark labeled "Avro · 5k/s" in monospace; Spark → ClickHouse labeled "rows · 1k/s"; ClickHouse → Grafana labeled "SQL · on-read"...

### Example 2
**User input:** "S3 raw json drops, Lambda parses to Parquet, Glue catalog, Athena queries"
**Refined image prompt (excerpt):**
> Data-flow diagram, flat vector. Source: S3 cylinder (left, label "raw events.json"). Lambda service (center-left, label "parser"). S3 cylinder (center, label "parquet"). Glue catalog service (center-right). Athena service (right, accent highlight). Arrows labeled "JSON · batch", "Parquet · partitioned", "schema", "SQL"...

## Common mistakes to avoid
- Do NOT skip the payload labels - they are the point of a data-flow diagram.
- Do NOT mix flow direction (top-down + left-right). Pick one (left-right).
- Do NOT label every arrow the same. Differentiate by payload format and volume.
- Do NOT include a "user" actor unless the user is part of the data path.
