# Sources and visual interpretation

## Completed exploratory study

Pinned publication:
https://github.com/detasar/llm-weight-editing-study/tree/d78bd5edbb84adb429f95f4c06ca4b70d1277d86

Numerical source: data/manifest.json in that repository.
Method: docs/METHODS.md; evaluation convention: docs/SCORER.md.
Exact prompt resources: prompts/v2/adult_editor.txt, prompts/v2/lm_editor.txt,
prompts/v2/cowork_editor.txt. These are bundled in data/prompts.json.

The presentation's compact evidence payload, data/evidence.json, was retained from
this conversation's preceding source-backed presentation package. It includes
selected learned tensors, mask, patch changes, recorded examples, metrics and
candidate trajectories. The repository README and exact prompts were rechecked
through the connected GitHub tool during this revision.

## Motivating research

Sparks of Weight-Space Programming — Rikiya Takehi, Jayden Teoh, Alex Zhang,
Omar Khattab (2 November 2026):
https://rikiyat.github.io/blog/weight-space-programming/

Car experiment and records:
https://github.com/RikiyaT/lm_understand-logs/tree/main/exp4_fix_car

Math experiment:
https://github.com/RikiyaT/lm_understand-logs/tree/main/exp8_math
https://github.com/RikiyaT/lm_understand-logs/blob/main/exp8_math/runs/p50c/work_notes/final_report.md

The selected source edit is W' = W - 6 outer(u, mask64 * (u @ W)). It targets
64 MLP output columns each in layers 15 and 19. The multiplier is the selected
strength in the recorded source search. The slide deliberately does not invent
per-dose benchmark scores. The targeted value count is 131,072; the source's
post-rounding changed count is separately 130,188.

Source MATH-500: 7.9% → 48.1%; fraction reaching token limit: 93.0% → 33.1%.
Source car: 6,073 changed actor parameters out of 171,664; 1,024/1,024 test successes.
These are source authors' measurements, separate from the local exploratory study.

## Interpretive scope

- One seed and one selected endpoint per method. Paired intervals quantify example
  uncertainty in that setting.
- Adult calibration retained the insufficient-damage flag. The clean reference has
  lower balanced accuracy but better ordinary accuracy and probability metrics.
- Adult solo allowance is ten candidates; joint is five new rounds with development
  history. The comparison describes the actual selected endpoints.
- The publication's LM v2 uses panels previously exposed in v1. It is a continuation
  with corrected prompt precision wording, not an independent replication.
- All final LM conditions select the same original weight state.
- The shared prompt resource contains a historical scheduler implementation sentence;
  its source text is preserved. Completed run evidence is in the numerical manifest.

## Illustrations versus measurements

- Vehicle motion and source loop graphics are explanatory reconstructions, not a replay
  of the original simulator or exact generated answer text.
- “Worked numerical example” uses explicitly chosen small values to explain multiplication,
  activation and scoring. Its output probabilities are locally computed.
- The tabular display uses illustrative feature rows. Dataset sizes and split counts
  come from the study sources.
- The displayed Adult coefficient and two decision-crossing examples are saved values.
- LM candidate operations/counts are saved. Raw LM before/after individual coefficients
  were not retained; this presentation displays the operation instead of inventing them.
- The surrounding landscape is decorative, not an empirically measured loss surface.

## Design and software

Three.js local r169 and its MIT license are bundled. Reference imagery and the earlier
teaser supplied in the conversation informed motion and color direction. Original
article title imagery is credited above. The model-provider mark comes from:
https://github.com/openai/openai-realtime-console/blob/ab8b8f5852b47ec1b9ef73bf566851d0eeafddbb/client/assets/openai-logomark.svg
Official brand guidance: https://openai.com/brand/
