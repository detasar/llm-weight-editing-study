# Scientific figure exports

`npm --prefix web run export:pdf` writes selected manifest-bound SVG and high
resolution PNG figures here after source freeze. SVGs embed the bundled Manrope
font. The source is shared with the interactive deck and HTML report:
[`web/src/figures.ts`](../../web/src/figures.ts).

Captures and PDF-page rasters for visual acceptance go to ignored
`artifacts/qa/`. Generated exports must be inspected before release.

The mask scene uses the exact 16×32 permanent-mask matrix; the inspector uses
the same coordinates for executed float32 scalar changes. Decision plots share
a saved-data threshold zoom (all flipped rows) and full-range inset across
the report and deck. The interactive mathematical explanations use **Next
explanation** / **Show all**; static and printed views include all definitions.

After source acceptance, the host must run the build and browser checks, inspect
the 1920- and 1280-wide WebGL label captures (including focus/reset), and render
all report/deck pages. Inspect the mask, scalar close-up, decision zoom, Adult
forest, and LM development/final pages before exporting production PDFs/ZIP.
Packaging uses `zip -X` to omit extra ownership fields.
