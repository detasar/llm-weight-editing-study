# Publication validation

The v1.0.0 publication uses frozen numerical manifest
`8f8869a113d93000bb8fffd547258b36ab955a6bf7a7f8ddbe589fbdbd231d38`.
The checks below concern the released measurements and publication software;
they do not add experimental observations.

| Check | Evidence from the release process |
| --- | --- |
| Native export | All seven Adult prediction arrays and both completed LM v2 task arrays matched the saved native values and paired order. The six frozen numerical files remained byte-identical during visual production. |
| Offline analysis | `verify` and `analyse` completed in a fresh analysis-only environment with network access disabled and without PyTorch or Transformers installed. |
| Reproduction software | 23 focused tests passed; saved-data checks and synthetic execution boundaries were independently reviewed. The portable new-experiment commands have not been claimed as a new real-model replication. |
| Browser behavior | 290 checks passed, including navigation, direct scene links, method/candidate selection, final-only decision attribution, presenter notes, pause, reduced motion, 2D fallback and layout at 1920, 1280 and 390-pixel widths. |
| Visual inspection | Every main scene, all 22 report pages and all 28 deck pages were rendered and visually inspected. The final corrected mask and decision pages were inspected again; unchanged pages were compared pixelwise. |
| Local presentation walkthrough | All 22 scenes were traversed with presenter notes and controls. Local headless Chrome sampling of three 3D scenes was approximately 60 frames/second. This was an automated interaction walkthrough, not a timed spoken rehearsal. |
| Independent review | Separate OpenAI GPT-6.1 Sol review sessions accepted the exact reproduction and presentation candidates. Sonnet was not admitted; the OpenAI route was the authorized independent alternative. |

The visual source candidate reviewed before PDF/ZIP production was
`594575fbfc9fed1c42898b99b7b3c71d5d6ea4f8bc751fcda458ae4dacaac713`.
The reproduction candidate was
`e5bc83c24888561dfbe771eb924d1b31d9ff9c428b1bdc2cd5bf0507358c8baa`.
These are review-package identities, distinct from the publication Git commit.

Run the numerical checks with the commands in [REPRODUCE.md](REPRODUCE.md).
Run interface checks with `npm --prefix web run test`; browser artifacts are
written to the ignored `artifacts/qa` directory. Export both PDFs and page
rasters with `npm --prefix web run export:pdf` after a successful build.
