# Scope and interpretation

This snapshot describes one exploratory seed101 comparison. It is not the
completed original multi-seed confirmation or independent evidence of general
editor ability. Outcomes can be positive, null or negative. Intervals describe
paired example uncertainty, not variability between editor sessions.

The original Adult Sol and Astra searches started independently from the same
damaged model, with no access to one another's attempts. The joint development
session could see their development feedback and used the same immutable origin.
Final feedback was unavailable to the editors. Original Adult solo searches had
an allowance of ten candidates; cooperation had five shared rounds. That unequal
allowance is retained. Candidate zero is always eligible. The held-out Adult
panel contains 16,281 original test examples. Clean/random/grid are separately
frozen supplements; their final predictions and paired comparisons are complete in the frozen manifest.

The original intact LM searches likewise started independently. Their joint stage
used fresh source development history. v1 selected the unchanged origin in all
four conditions: they are one executed-weight group, not four independently
scored weight states. Original ARC final evaluation completed, while original PIQA
failed before scoring any PIQA rows. The later PIQA-only supplement measured the
same selected state once and reused those predictions for the other three names.
The supplement remains historical v1 evidence, separately identified.

The corrected-prompt publication v2 has fresh independent source sessions and joint
development. The analyst already saw v1 final scores. v2 uses the same panels,
not an independent replication. Main LM results are the completed v2 measurement: all four conditions selected
candidate zero, with newly measured ARC and PIQA final predictions. Sol and Astra
each measured five nonempty candidates. Joint made five attempts: attempt 1 was
INVALID without a score; valid indices are 0, 2, 3, 4 and 5. v1 scores are never relabeled as v2. Original v2 measurement DID complete. Exporting and building this publication
snapshot itself made no model inference or editor request.

# Native numerical semantics

Canonical implementations are ported from accepted source `ed15068`; exact source
hashes and narrow portability adaptations are in `configs/source.json`.
`model.py`, `patches.py`, `controller.py`, `lm_patches.py`, `lm_controller.py`,
`lm_runtime.py`, `lm_scoring.py`, `metrics.py` and `io.py` retain the accepted
numerical rules. `saved_lm.py` contains the unchanged saved-row aggregate and
paired bootstrap functions without importing inference dependencies. The complete
historical orchestration is blocked as explained in `REPRODUCE.md`.

Adult is a float32 MLP: encoded inputs -> 32 ReLU -> 16 ReLU -> one sigmoid
probability. Sex/race are excluded from the encoded predictors. Training uses the
original stratified train split, fit-only encoding and Adam. The calibration
lesion procedure permanently zeros columns in `fc2.weight`. Its damage criterion
was not met: `insufficient_damage=true` remains visible, so conventional recovery
ratios would be misleading. Only surviving `fc2.weight` entries can be edited.
The exported graph includes exact learned tensors and the permanent mask, but no
training/test feature rows. Patches are complete interventions relative to the
immutable damaged origin. Scalar bounds count actual unequal post-cast values;
Frobenius/L2 norms are measured after casting, using the accepted double-precision
norm calculation. Masked entries stay zero. Sparse delta and selected-column
scaling schemas are bundled in `configs/*_action.schema.json`.

Adult selection is lexicographic: development balanced accuracy descending, delta
L2 ascending, changed scalar count ascending, then earliest candidate index.
Accuracy, ROC-AUC, log-loss and Brier are secondary. Final probabilities were serialized from float32 inference to JSON lists; canonical
final metrics call NumPy on those lists as float64. Analysis preserves that exact
boundary rather than recasting the lists to inference precision. Paired class-stratified bootstrap uses seed101 and
2,000 draws. Rescues/regressions are raw correctness counts by class; they are not
balanced-accuracy points or mechanistic proof.

SmolLM2-1.7B base uses pinned canonical ARC-Easy and PIQA multiple-choice tasks.
Only `model.layers.<index>.mlp.down_proj.weight` can change, using selected-column
scaling or sparse scalar deltas. Every candidate is relative to the original
weights. Actual changed scalars / unique model parameters cannot exceed .001;
per-tensor relative Frobenius change cannot exceed .05. The declared runtime is
MPS float32 eager. The MPS float32 train8 run was an engineering sensitivity check only. No
float32 train64 gate was run; the train8 check does not establish numerical
equivalence over the full benchmark.

Raw `acc` chooses the greatest continuation log-likelihood. `acc_norm` divides
each likelihood by **choice text character length**, not token length, before
argmax. Ties use the native first-argmax behavior. The saved choice likelihoods,
character/token lengths, gold choices and decisions allow these metrics to be
recomputed without model weights or question text. Development selection uses
`acc_norm` descending, then delta norm, changed count and earliest index. ARC
train128/development128 precede final ARC512 and PIQA256; PIQA is final-only.
Paired LM bootstrap uses the unchanged native algorithm, seed101, 2,000 draws.

Verified identical executed weights reuse predictions only when origin, panel
order, task/prompt settings, device/dtype and scorer identity agree. No-op and
post-cast-identical candidates consume candidate slots but not fictional target
forwards. Real editor active time is budgeted separately from target/peer waiting.
The snapshot records measured target work separately from editor calls and reuse.
No run-level work estimate is manufactured from candidate count.

# Prompts and visual evidence

`prompts/v1` preserves the original resources exactly. The v1 LM prompt said
float16 despite the engineering float32 runtime; that discrepancy is disclosed.
`prompts/v2/lm_editor.txt` is the exact accepted
`v2_instructions('float32')`: one guarded replacement of
`float16 before application.` with `float32 before application.`. It is not an
editorial paraphrase. Other resource texts are preserved, including historical
software-only limitations. All prompt resources are hash-bound by the manifest.

Adult visuals can use exact full scalar weights, mask and selected patch changes.
All selected main v2 LM patches are no-ops, so selected changed columns are
exactly empty; v1 remains method history. Nonselected LM candidate operations, actual changed counts/norms and
executed tensor hashes are retained. Their raw before/after scalar samples were
not retained in the approved evidence and are explicitly unavailable. No model
binary is accessed and no plausible-looking LM scalar value is invented.

The clean Adult final reference has lower BA than damaged, while accuracy,
ROC-AUC, log-loss and Brier are better. Sol and joint shift the error balance;
this is not restored BA. Exact task/scorer conventions: [SCORER.md](SCORER.md).
