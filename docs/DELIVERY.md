# Publication delivery

BBVA AI Innovation — final 30-scene presentation, English slides and Turkish narration.
The existing scientific snapshot and the 26-page research report are preserved.

| Material | Current artifact |
| --- | --- |
| 45-minute presentation, 30 scenes | [START_PRESENTATION.html](../publication/2026-11-04/START_PRESENTATION.html) |
| Turkish speaking script | [PDF](../publication/2026-11-04/TURKCE_ANLATIM.pdf) · [HTML](../publication/2026-11-04/TURKCE_ANLATIM.html) · [Markdown](../publication/2026-11-04/TURKCE_ANLATIM.md) |
| Presentation backup, 30 pages | [PDF](../publication/2026-11-04/PRESENTATION_BACKUP.pdf) |
| Motion preview | [MP4](../publication/2026-11-04/MOTION_PREVIEW.mp4) |
| Existing 26-page research report | [PDF](../publication/2026-11-04/RESEARCH_REPORT.pdf) · [HTML](../publication/2026-11-04/RESEARCH_REPORT.html) |
| Complete offline delivery | [ZIP](../publication/2026-11-04/BBVA_RESEARCH_OFFLINE.zip) |
| Instructions and licenses | [README](../publication/2026-11-04/README.txt) · [Notices](../publication/2026-11-04/THIRD_PARTY_NOTICES.txt) |
| Sizes and hashes | [Artifact manifest](../publication/2026-11-04/artifact-manifest.json) |

Unzip and double-click START_PRESENTATION.html. The first scene opens directly.
Right/Space advances, Left goes back, R replays, G opens the scene map, N opens
Turkish narration and F toggles fullscreen. The narration panel can open a separate
speaker window; Play 45 min provides timed playback.

Playback uses self-contained HTML, with Three.js geometry projected to Canvas
and SVG/HTML compositions. No runtime server or API key is required.

The same canonical URLs are used by the public landing and existing bookmarks.
`web/prepare.mjs` verifies and stages the deliverables. Original renderer checks
and their environment limits are recorded in `presentation/revised/docs/QA.md`.
The integration itself is packaging and routing, not a new scientific run.
