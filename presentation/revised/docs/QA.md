# Rendered verification

This is a presentation delivery check, not a new model experiment or a claim of
scientific replication.

## Rendering actually used

The shipped presentation uses a persistent Three.js perspective/geometry layer
projected to Canvas, and authored SVG/HTML compositions in the foreground.
All explanatory objects, text and calculations render without WebGL. Animations
run locally. The selected implementation does not depend on a GPU context.

## Executed checks

- Chromium, 1600 × 900 logical stage: all 30 scenes and all 98 authored states.
- A separate pass checked 204 quarter-, half- and three-quarter transition states.
- Measured SVG text boundaries and visible text collisions: zero remaining findings.
- HTML question-card and prompt-panel overflow checks: zero remaining findings.
- JavaScript page errors: zero in both passes.
- HTTP requests during local presentation playback: zero.
- Live weight control: 0.400 gives 57.93%, 0.200 gives 46.01% in the worked example.
  The input node remains mounted while the downstream calculation changes.
- Stored coefficient: Astra 0.1278217; Sol 0.1528217.
- Exact Adult prompt opens. The archived joint prompt is accompanied by its historical
  context instead of changing the recorded source text.
- Scene transition is active at 600 ms and reaches its completed state.
- Viewports: 1280 × 720, 1440 × 900 and 1920 × 1080.
- Turkish PDF checked visually for text layout and Turkish characters. Presentation
  backup checked as rendered pages. Source language remains English; spoken script is Turkish.

The recorded summaries are in qa/browser-checks.json and qa/motion-states.json.
The shipped sources contain the scripts used for these checks.

## Corrections made after inspection

1. Removed a redundant opening caption overlapping the source-page composition.
2. Moved arithmetic connectors away from their number labels.
3. Bounded right-edge explanatory labels by their actual available width.
4. Separated the selected-zero label from the large zero and its explanation.
5. Preserved input controls during live number updates.
6. Separated the two cooperative-step captions during their intermediate crossfade.
7. Faded heading/summary layers separately so old and new long titles do not overlap.

## Environment boundaries

This container blocks file:// navigation by administrator policy. Tests therefore
loaded the exact self-contained HTML using Playwright set_content. No browser policy
was changed. Direct double-click operation, macOS, Safari and a physical projector
were not tested here. WebGL was unavailable and is not needed by this renderer.

The preview video contains rendered excerpts, without narration. It is not a
recording of a complete 45-minute live delivery. The 45-minute value is the sum of
authored scene timing recommendations, including explanation and visual pauses.
