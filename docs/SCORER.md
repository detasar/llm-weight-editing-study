# Canonical scoring conventions

Editing Neural Networks with Language Models · Davut Emre Taşar (detasar) · 4 November 2026.

The source of truth is `src/ws_lab/lm_scoring.py`, with saved-row aggregation in
`src/ws_lab/saved_lm.py`. Task YAML identities and model/data revisions are in
[VERSIONS.md](VERSIONS.md) and `configs/source.json`.

## Language model

The pinned harness commit is `d6de81643928d653435c431bae19945d41d32520`.
The scorer loads the native ARC-Easy and PIQA YAMLs, resolves their native helpers,
and replaces only the dataset revision with its pinned revision. It uses
`task.doc_to_text(doc)` for context, `task.construct_requests(doc, context)` for
multiple-choice likelihood requests, and `task.doc_to_choice(doc)` for choices.
The native task therefore determines the exact question template, delimiter,
choice order and continuation. This publication does not substitute a chat
prompt, answer letter or simplified question template. Exact request arguments
are hash-bound in native evidence; saved public rows retain derived numeric
likelihoods and lengths rather than third-party question text.

For each continuation, L is the sum of its token log probabilities. Raw `acc`
chooses `argmax(L)`. `acc_norm` chooses `argmax(L / len(choice_text))`, where
`len` is Python character length, **not token count** and not the context length.
Ties choose the first maximum in native choice order. Gold labels and choice
ordering come from the native task; correctness is aggregated as a mean over rows.
`task.process_results` supplies the native `acc` and `acc_norm` for each request.

Execution uses HFLM batch size 1, `logits_cache=False`, eager attention, MPS
float32 and float32 softmax. Continuation token lengths come from HFLM's native
`_encode_pair`; they are recorded for audit, not used as the normalization divisor.
Nonfinite likelihoods or empty character/token continuations are rejected.
The final-task guard authenticates effective task fields and native method
implementations, including prompt/target/choice functions, delimiters, few-shot
settings, revision, output type and result metrics.

Development uses ARC train128 for diagnostics and validation128 for feedback;
final uses ARC512 and PIQA256. PIQA is final-only. Candidate selection minimizes
`(-dev_acc_norm, delta_L2, changed_scalar_count, index)`. Candidate zero remains
eligible. Final feedback cannot select or stop search. v2 is the main completed
measurement; the historical dtype-description mismatch and panel exposure are
recorded once in [METHODS.md](METHODS.md).

Exact-state prediction reuse requires matching actual weights, origin, ordered
panel, canonical requests, task/scorer implementation and device/dtype. Four labels
for one selected state are one executed observation. Paired LM uncertainty uses
seed101, 2,000 native row-bootstrap draws; identical predictions produce exactly
zero differences and zero rescues/regressions.

## Adult

The float32 104→32→16→1 network uses ReLU, ReLU and sigmoid. Classification uses
`p >= .5`. Final JSON probabilities enter canonical NumPy metrics as float64.
Positive income >50K has 3,846 rows; negative ≤50K has 12,435. Balanced accuracy is
the mean of class recalls; ordinary accuracy is total correct / 16,281. ROC-AUC
uses probability ranks. Log-loss and Brier assess probability quality (lower is
better). The native `metrics.py` retains the scikit-learn numerical conventions.

Paired BA intervals resample with replacement independently within each label
class, preserve class sizes and share the sampled indices across both conditions.
Seed101, 2,000 draws, percentile 2.5/97.5%. A rescue changes wrong to correct; a
regression changes correct to wrong. These are raw counts, not BA points.
