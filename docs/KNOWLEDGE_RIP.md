# Knowledge RIP — Editing Neural Networks with Language Models

Davut Emre (detasar) · 4 November 2026

**Research question.** Can an LLM propose a bounded weight edit that improves a
held-out decision rule, and does access to independent development experience
change the selected endpoint? Inspired by Takehi et al.’s weight-space programming
article, this is an independent exploratory test on Adult and SmolLM2.

**Intervention.** Adult is a float32 104→32→16→1 ReLU/ReLU/sigmoid network.
Only surviving fc2 weights can change; the permanent lesion stays zero. Sol and
Astra begin independently from the same damaged origin. Joint sees development
history but also starts at that origin. SmolLM2-1.7B has 24 blocks and gated MLPs
2048→8192→2048. Edits affect down_proj columns or sparse scalars only, under
post-cast count and relative-norm bounds. No gradient training occurs in editing.

**Selection.** Minimize (negative DEV primary score, L2, changed count, index).
The unchanged candidate zero is eligible. FINAL is assessed only after freezing.
Adult primary is balanced accuracy; LM primary is character-normalized accuracy.

**Findings.** Adult baseline BA is 78.585785%; Sol is
79.020686%; joint is 78.966808%.
Positive-class rescues accompany negative-class regressions and lower ordinary
accuracy. Clean has lower BA than damaged, but better accuracy/AUC/calibration:
this supports an error-balance tradeoff, not a BA-recovery claim. Random/grid
paired comparisons and all five final metrics are in the report.

Completed corrected-prompt LM v2 selects candidate zero for all four labels.
ARC-Easy acc_norm is 73.437500% on 512 examples;
PIQA acc_norm is 78.515625% on 256. The four labels share
one measured weight state and identical predictions. Five nonempty Sol and Astra
candidates were measured; joint’s first attempt was invalid and unscored.

**Interpretation and limits.** One seed101 session; paired bootstrap intervals
measure example uncertainty, not editor-session variability. Original Adult solo
allowance ten vs joint five with extra history is not equal compute. v2 corrects
v1’s dtype description but reuses previously exposed panels. MPS float32 train8
was an engineering check; no float32 train64 gate was run. Null LM selection and
Adult’s metric tradeoff remain substantive outcomes.

**Provenance.** [Frozen manifest](../data/manifest.json),
[methods](METHODS.md), [scorer](SCORER.md), [reproduction](REPRODUCE.md).
Snapshot export made no model calls; original v2 measurement completed.
Manifest: `8f8869a113d93000bb8fffd547258b36ab955a6bf7a7f8ddbe589fbdbd231d38`.
