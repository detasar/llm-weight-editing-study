# Reproduce the saved numerical results

Use Python 3.12 or newer. The commands below run from a clean checkout, with
no personal paths, model download, provider, API key or editor session.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m ws_lab.reproduce verify --data-dir data
python -m ws_lab.reproduce analyse --data-dir data --output analysis.json
python -m ws_lab.reproduce doctor
```

`analysis.json` must be a new file. `analyse` validates all input, prompt and
summary hashes and recomputes canonical metrics and intervals from saved numeric
arrays. `verify` does the same checks and prints a compact receipt. `doctor`
inspects installed package metadata and executable availability only; it makes
no provider/canary request, loads no model and cannot establish model availability.
The checked-in main v2 panel and all three Adult controls are measured. v1 remains
explicit history; both LM versions used MPS float32 eager execution. These saved
measurements do not establish real execution of the portable commands below.

For the focused offline tests and private-data transformation, install native
numeric dependencies as well. Tests use saved arrays and a tiny synthetic tensor,
never a target model or provider:

```sh
python -m pip install -e '.[native,test]'
python -m pytest -q tests/test_reproduce.py
```

# Explicit new execution

`run` and `replay` now execute **new public experiments**, with fresh identities.
They do not validate or consume historical private runs. Historical sealed
DEV_HISTORY, backend and consumption guards remain in the accepted source; no
private audit, account, journal or consumption identity is reused. Saved-data
commands above still load no target model, GPU, editor or provider.

Install the optional LM dependencies into your own environment, and authenticate
your own Codex CLI before choosing `run`:

```sh
python -m pip install -e '.[native,lm,test]'
python -m pytest -q tests/test_reproduce.py tests/test_execution.py
```

Supply your own offline SmolLM2-1.7B checkpoint at revision
`effd688a12921b4cc83e3312b6feb579f70f9c71`, including the Hugging Face local download
metadata for each root file (`.cache/huggingface/download/<name>.metadata`).
The first metadata line must match that revision. Supply a fully populated local
Hugging Face **datasets cache directory**, containing the pinned ARC-Easy and PIQA
tasks; the runner sets `HF_DATASETS_CACHE` to `--dataset-dir` and forces offline
mode. It never downloads missing inputs. Harness source commit, YAML hashes and
dataset revisions are enforced by `lm_scoring.py`. Install the pinned harness
from the LM extra beforehand. A missing dependency, cache, model or runtime fails
with no substitution. Model and task files are third-party inputs and stay local.

## LM fresh run

```sh
python -m ws_lab.reproduce run --config configs/fresh-lm.json \
  --model-dir "$MODEL_DIRECTORY" --dataset-dir "$DATASETS_CACHE" \
  --output "$NEW_RUN_DIRECTORY" --codex-cli codex
```

This explicit command can invoke editors and evaluate your model. It uses the
native driver, LMController, TaskAdapter and Scheduler in this order: baseline,
five Sol candidate opportunities, five independent Astra opportunities from the
same original weights, five joint proposal/review opportunities using **only
these newly frozen source histories**, freeze all four endpoints, ARC test and
PIQA validation. It requires all five independent candidate opportunities for
each source before joint work; an early stop is terminal failure, not five
invented evaluations. The native lexicographic selection still includes baseline.
Sol and Astra never receive each other's independent transcript. The joint
actors receive a newly created native ledger, source freeze and DEV_HISTORY
exposure audit; no historical private audit is a prerequisite.

`configs/fresh-lm.json` declares seed 101 and an MPS float32 eager engineering
runtime. For CPU, copy it to a local file and set `lm.device` to `cpu` and
`lm.runtime_profile` to `cpu-fp32-eager-engineering-v1`; retain float32/eager and
candidate limit 5. Seeds 101, 202 and 303 are supported. The accepted pilot RNG
order fixes diagnostic 128, feedback 128, extra probes 32, ARC final 512 and PIQA
final 256. Task revisions and original split sizes are checked. The actual
float32 prompt reaches the solo native drivers; the joint role prompt receives
float32 in the validated TaskAdapter view. Editors are exactly `gpt-6.1-sol` and
`gpt-6-astra`, medium reasoning, through your own subscription CLI. Resolution is
`--codex-cli`, then `WS_LAB_CODEX_CLI`, then `codex` on PATH. There is no silent
model/backend fallback. Canary/editor calls occur only in explicit `run`.

The required `backend_acceptance` declares acceptance of a **new-run engineering
runtime**, not native64 or whole-benchmark CPU parity. The runner verifies actual
model dtype/device/eager settings and pinned scorer provenance, then records its
own runtime identity and gate under the fresh run ID. It performs neither the
old train8 nor the native64 comparison. Hardware, model/backend availability and
scientific outcomes remain unverified until an actual user execution. Tiny
synthetic tests establish software behavior only.

## Frozen replay, no editors

```sh
python -m ws_lab.reproduce replay --config configs/replay-lm.json \
  --model-dir "$MODEL_DIRECTORY" --dataset-dir "$DATASETS_CACHE" \
  --output "$NEW_REPLAY_DIRECTORY"
```

The LM replay config references `data/lm_v2_frozen_patches.json`, bound by the
manifest and copied exactly from the main v2 frozen slot descriptors (all four
are no-ops). Historical `configs/lm-v1-frozen-patches.json` stays separate. It uses the same
pinned model, canonical scorer and panels, with the declared fresh float32
runtime. Historical v1 also ran MPS float32 eager despite its float16 prompt
wording. Replay does not establish exact historical validation. For your own frozen endpoint set, copy the config and change `patches`
to a JSON file relative to that config, mapping baseline/Sol/Astra/joint to exact
`{"ops": [...]}` patches, exported slot records or a fresh `frozen.json` receipt.
No editor, canary or training calls occur in replay.

Adult replay reconstructs the released clean/root tensors, checks the permanent
mask reconstruction and every executed patch hash/statistic, then calls the
existing CPU float32 `probabilities` and canonical metrics. It evaluates clean
and all released graph variants, including random/grid controls when present.
Use `data` as the model directory; features stay in your own prepared `test.npz`
(`x`: finite encoded feature matrix, `y`: binary labels). The columns must follow
the original fit-only encoder; the runner cannot infer an encoder from width.
For original UCI records, the bundled `data.prepare(source, local_run, seed=101)`
reconstructs the canonical 70/10/20 split and fit-only encoding from your own
`adult.data` and `adult.test`, without a download:

```sh
python -c 'import os; from ws_lab.data import prepare; prepare(os.environ["ADULT_SOURCE"], os.environ["NEW_ADULT_PREPARED"], seed=101)'
python -m ws_lab.reproduce replay --config configs/replay-adult.json \
  --model-dir data --dataset-dir "$NEW_ADULT_PREPARED" \
  --output "$NEW_ADULT_REPLAY"
```

Adult **run is not supported** by this CLI. The existing fresh training recipe is
`data.prepare` above followed by the bundled fixed CPU training implementation:

```sh
python -c 'import os; from ws_lab.model import train; train(os.environ["NEW_ADULT_PREPARED"], seed=101)'
```

That creates your own clean/damaged/mask artifacts and training metadata locally;
it does not run Adult editors or turn a newly trained model into a historical
replay. Never publish prepared feature files, raw rows or third-party inputs.

## Execution receipts and failure

Every output directory must be new and separate from input directories. An
existing output refuses before loading a model or any forward. A newly claimed
scope gets a random run ID and exclusive single-use `consumed.json`; it is never
resumed or retried. Config, input files, model revision, source code, prompts,
panels, exact patches and executed states are bound in local receipts. The
independent source closure freezes before joint use; all four endpoints freeze
before final scoring. A separate exclusive `assessment-consumed.json` marks final
access in the parent scope and invalidates further DEV_HISTORY access to those
sources without a new exposure audit. Assessment groups equal **executed** weight/request states
once per task, including postcast-equivalent descriptors. Prediction reuse is
recorded separately from actual examples/requests/forward work.

`assessment_predictions.json`, `assessment_results.json`, `assessment_groups.json`
and work counters are saved incrementally. If PIQA fails, earlier ARC output stays
present. Failure records include available partial rows, actual counters and a
terminal `FAILED_CONSUMED_NO_RETRY`; failure never becomes a zero or invented
score. `terminal.json` marks completion only after scoring and input/code binding
revalidation. Output directories contain user-local native evidence, including
source transcripts and canonical scorer IDs; they are **not public exports**.
Do not copy them into publication data. Only the numeric exporter below is a
publication boundary. No execution performed by this code-editing task is claimed.

# Coordinator re-export after terminal execution

The exporter transforms saved evidence only. It does not train, load a target
checkpoint, score examples, contact editors or follow arbitrary journal paths.
It validates the owned Adult trained tensors and uses tensor arithmetic to expose
actual patch values. No Adult feature rows, questions, original IDs, conversations,
provider sessions, financial records or third-party model binaries are exported.
All private input paths are explicit and have no defaults.

Initial v1-only export (all shell variables must be set to the supplied private
artifacts by the coordinator):

```sh
PYTHONPATH=src python scripts/export_private.py \
  --prior-scope "$PRIOR_SCOPE" --adult-run "$ADULT_RUN" \
  --piqa-supplement "$PIQA_SUPPLEMENT" --amendment "$AMENDMENT" \
  --output "$NEW_EXPORT_DIRECTORY"
```

After the publication science has terminated, export into another **new empty**
directory; do not overwrite the current data or a private run:

```sh
PYTHONPATH=src python scripts/export_private.py \
  --prior-scope "$PRIOR_SCOPE" --adult-run "$ADULT_RUN" \
  --piqa-supplement "$PIQA_SUPPLEMENT" --amendment "$AMENDMENT" \
  --publication-scope "$PUBLICATION_SCOPE" --publication-terminal \
  --output "$NEW_EXPORT_DIRECTORY"
PYTHONPATH=src python -m ws_lab.reproduce verify --data-dir "$NEW_EXPORT_DIRECTORY"
PYTHONPATH=src python -m ws_lab.reproduce analyse --data-dir "$NEW_EXPORT_DIRECTORY" --output next-analysis.json
```

`--publication-terminal` is an explicit coordinator assertion, not a process
monitor. The exporter also requires complete or failed LM results and complete
control receipts before importing measured data. Absent endpoints remain missing;
absent v2 remains pending. It never waits for a live job. v1 stays history, the main
LM version always stays v2, and no result-based version selection occurs. The
coordinator can replace the assigned `data/*.json` with the verified new export
after reviewing the concrete candidate.

# Data API

`data/manifest.json` is the sole entry point. Scores are fractions; plotting a
score difference in percentage points requires multiplying by 100. Missing
measurements are `null`, with explicit per-task status.

- `adult.methods`: canonical balanced accuracy, accuracy, ROC-AUC, log-loss
  (`logloss`), Brier, n, paired class-stratified intervals and class rescues/regressions.
- `adult.contrasts`: every condition versus baseline, Sol/Astra/joint versus
  random/grid, and joint versus Sol, using canonical seed 101 and 2000 draws.
  An unavailable comparison has an explicit reason and null difference/interval.
- `adult.candidates`, `adult.slots`: ordered development candidates, lexicographic
  selection, exact patch operations, budgets, actual norms/counts, editor metadata
  and target work. Solo allowance 10 and joint allowance 5 remain visible.
  Candidate records retain sanitized native `events`, including invalid/blocked
  opportunities with null metrics. Candidate indices are never renumbered. Events
  retain slot/index associations only when natively present; a turn alone does not
  establish an evaluation slot. Free-text reasons and request hashes are omitted.
- `adult.graph`: exact architecture, clean/root scalar tensors, permanent mask,
  and selected legal patches with every actually changed before/after scalar.
- `lm.main_version`: always `v2`. `lm.versions.v1` is historical original ARC plus
  a separately identified PIQA supplement; `v2` is the completed main assessment.
- `lm.versions.<version>.tasks`: separate ARC/PIQA raw `acc` and character-normalized
  `acc_norm`, n and paired intervals. Candidates and final tasks are distinct.
- `unique_executed_weight_groups`, `actual_prediction_reuse`, `assessment_work`,
  `piqa_supplement.work`, candidate `target_work` and `editor_calls` distinguish
  target computation, reused outputs and editor requests. They must not be added
  together as equivalent forwards. Historical v1 PIQA incurred one distinct pass.
- `execution`: portable future commands are available with offline synthetic
  verification only; real portable execution is NOT_RUN. Recorded source
  measurements have separate statuses. Main v2 assessed ARC 512 and PIQA 256
  in one executed-weight group: 2558 forwards, 247.99987179087475 wall seconds.
- `files`, `prompts`, `summary_sha256`, `manifest_sha256`: content bindings.
  `source_receipts_sha256` retains logical evidence roles, without private paths.

Ordinal paired IDs retain private panel order; original IDs are omitted. Every
Adult condition is checked against the original saved label/ID ordering before
export. Every LM task is paired by original ID/index privately and by ordinal,
label and choice-length arrays publicly. v2 must use the same ordered panels as
v1 when imported. Hashes protect the snapshot against corruption; they are not
signatures or a substitute for the original private records.
