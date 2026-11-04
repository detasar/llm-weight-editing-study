# Editing Neural Networks with Language Models

Davut Emre Taşar ([detasar](https://github.com/detasar)) · BBVA AI Innovation · 4 November 2026

**A small classification tradeoff; an unchanged selected language model.**
On UCI Adult, Sol improves balanced accuracy by 0.43 percentage points while
ordinary accuracy and probability quality worsen. On intact SmolLM2-1.7B,
completed v2 searches select the unchanged candidate zero.

![Conceptual network cover, not measured geometry](assets/art/network-cover.png)

[Public landing](https://detasar.github.io/llm-weight-editing-study/)
· [45-minute presentation](publication/2026-11-04/START_PRESENTATION.html)
· [26-page research PDF](publication/2026-11-04/RESEARCH_REPORT.pdf)
· [Research HTML](publication/2026-11-04/RESEARCH_REPORT.html)
· [Presentation PDF backup](publication/2026-11-04/PRESENTATION_BACKUP.pdf)
· [Offline ZIP](publication/2026-11-04/BBVA_RESEARCH_OFFLINE.zip)
· [Reproduce](docs/REPRODUCE.md) · [Delivery](docs/DELIVERY.md)

UCI Adult predicts whether annual census income exceeds $50,000. Its small
classifier starts with a permanent weight lesion. SmolLM2-1.7B starts intact
and answers ARC-Easy science questions and PIQA physical-reasoning questions.
Sol and Astra propose edits independently from the same origin; joint starts
from that origin with access to their development histories. Balanced accuracy
(BA) weights each class equally; LM acc_norm uses character-normalized answer
likelihood. The unchanged candidate zero remains eligible for selection.

*UCI Adult: rounded held-out metrics, 16,281 examples in every row. BA and
accuracy are percentages; AUC, log-loss and Brier are unitless. Exact values and
paired intervals remain in [the manifest](data/manifest.json).*

| Adult state | BA ↑ | Accuracy ↑ | ROC-AUC ↑ | Log-loss ↓ | Brier ↓ |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline | 78.59% | 82.86% | 0.8899 | 0.3783 | 0.1205 |
| Sol | 79.02% | 82.63% | 0.8900 | 0.3827 | 0.1222 |
| Astra | 78.59% | 82.80% | 0.8899 | 0.3786 | 0.1206 |
| joint | 78.97% | 82.63% | 0.8900 | 0.3824 | 0.1221 |
| clean | 76.59% | 85.63% | 0.9077 | 0.3147 | 0.1001 |
| random | 78.62% | 82.81% | 0.8900 | 0.3787 | 0.1207 |
| grid | 78.57% | 82.83% | 0.8899 | 0.3766 | 0.1201 |

All rows use the same 16,281 held-out examples. The intact clean
reference has lower BA than damaged but better accuracy, ranking and probability
quality. Sol rescues 65 positives and regresses 102 negatives; joint rescues 59
positives and regresses 96 negatives. Balanced accuracy weights the classes equally.
The paired forest plot shows example uncertainty in one exploratory session.
Original Adult solo allowance: ten candidates each; joint: five with development
history. This is an endpoint comparison, not equal-compute evidence of synergy.

| Completed LM v2 task | n | acc_norm | Raw acc |
| --- | ---: | ---: | ---: |
| ARC-Easy | 512 | 73.44% | 77.34% |
| PIQA | 256 | 78.52% | 80.08% |

Baseline, Sol, Astra and joint all select candidate zero: **one executed state**,
not four independent observations. Sol and Astra each measured five nonempty
candidates. Joint made five attempts, including an invalid first attempt with no
score. The new v2 final pass used 2,558 choice
forwards for 768 examples in
248.00 native forward seconds. Full native
work, exact-state reuse and selection details are in the report and manifest.

The canonical numerical source is [data/manifest.json](data/manifest.json).
README tables, reader report and presentation bind manifest identity:

`8f8869a113d93000bb8fffd547258b36ab955a6bf7a7f8ddbe589fbdbd231d38`

Historical v1 appears only in method history. v2 corrects the dtype wording to
float32, with fresh source sessions on previously exposed panels; it is not an
independent replication. Exporting this snapshot makes no model calls; the
original v2 measurement completed. [Methods](docs/METHODS.md),
[scorer](docs/SCORER.md), [versions](docs/VERSIONS.md),
[exact prompts](prompts/v2), [configuration](configs).

Download the offline ZIP, unzip it, then **double-click START_PRESENTATION.html**
and click Start presentation. Space pauses/resumes; Left/Right moves between
explanatory cues. No server, installation, API key or internet is needed for
playback. The 45-minute story has 33 chapters with synchronized written
explanation, optional reduced motion and a 2D view. The 26-page reader report
and 59-state presentation PDF backup are included.

Build the landing and stage the accepted publication (Node 24+):

```sh
npm --prefix web ci
npm --prefix web run build
npm --prefix web run dev
node --test web/tests/delivery.test.mjs
```

The build verifies and copies the delivered artifacts without rerendering them.
For source generation and its local tools, see [reproduction](docs/REPRODUCE.md).
[Artifact hashes](publication/2026-11-04/artifact-manifest.json) bind every actual
delivery file, including the ZIP. Packaging checks do not replace visual acceptance.

Inspired by Takehi, Teoh, Zhang and Khattab,
[Sparks of Weight-Space Programming](https://rikiyat.github.io/blog/weight-space-programming/)
(2 November 2026). Our targets and intervention domains differ from that work.
See [research summary](docs/KNOWLEDGE_RIP.md) and [citation](CITATION.cff).
Code: [MIT](LICENSE). Original report/artwork and derived numeric data:
[CC BY 4.0](CONTENT_LICENSE). Third-party title-page imagery is attributed and
excluded from that grant. Upstream model/data and bundled dependency rights
remain with their owners.
