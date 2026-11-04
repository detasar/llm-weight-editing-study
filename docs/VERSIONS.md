# Frozen source and numerical environment

Publication snapshot version: 1.0.0 (4 November 2026).
Accepted execution source: `ed15068c13ffb1cb1e3222d1056c1748b1e1292a`.
This is a clean publication snapshot, without private Git history. Adaptations and
per-module original hashes are recorded in `configs/source.json`.

| Component | Accepted pin |
| --- | --- |
| Python | >=3.12 |
| NumPy | 2.5.4 |
| SciPy | 1.18.1 |
| scikit-learn | 1.9.1 |
| PyTorch | 2.15.0 |
| safetensors | 0.8.0 |
| jsonschema | 4.26.0 |
| transformers | 5.22.1 |
| datasets | 5.1.0 |
| accelerate | 1.15.0 |
| lm-evaluation-harness | d6de81643928d653435c431bae19945d41d32520 (0.4.14.dev0) |
| observed Codex CLI | 0.166.0-alpha.5.1 |
| Sol editor request | gpt-6.1-sol, medium reasoning |
| Astra editor request | gpt-6-astra, medium reasoning |

Requested model names and recorded launch settings establish the requested route;
resolved model metadata may be null. Model self-identification is not routing
proof. No live editor availability was tested for this publication build.

| Model or dataset | Revision |
| --- | --- |
| HuggingFaceTB/SmolLM2-1.7B (base) | effd688a12921b4cc83e3312b6feb579f70f9c71 |
| allenai/ai2_arc, ARC-Easy | 210d026faf9955653af8916fad021475a3f00453 |
| baber/piqa | 142f6d7367fd9877f0fb3b5734ea6a545f54cdd1 |
| UCI Adult | Original adult.data/adult.test, 32,561/16,281 rows |

The accepted scorer also binds effective native task YAML hashes:

- ARC-Easy: `96da1d9efe1df88659481cedc13985cb347dc068554a2eae561303fa39bfab3f`
- PIQA: `e874f7956ccac325b888d4a5dc600bad867b79fba2bd358fe8761ab8263270fb`

The snapshot binds its derived ordered numeric datasets through `manifest.files`,
per-Adult-array hashes and per-LM-version array hashes. The exporter checks private
Adult test order and private LM task order before replacing original IDs with
ordinals. No original dataset records or third-party model files are distributed.
Attribution and upstream terms are linked in `CONTENT_LICENSE`.

Original UCI files, as bound in the accepted Adult preparation:

- `adult.data`: `5b00264637dbfec36bdeaab5676b0b309ff9eb788d63554ca0a249491c86603d`
- `adult.test`: `a2a9044bc167a35b2361efbabec64e89d69ce82d9790d2980119aac5fd7e9c05`

## Publication interface, 4 November 2026

Davut Emre (detasar), *Editing Neural Networks with Language Models*. The main
LM version is the completed corrected-float32-prompt v2. Historical v1 is retained
for method history; the same exposed panels are not an independent replication.
The snapshot export itself performs no model calls.

Visual dependencies: Three.js 0.187.0, KaTeX 0.19.1, Vite 8.3.5, TypeScript 7.0.2,
Manrope 5.3.0, Source Serif 4 5.3.1, Playwright 1.62.1. The lockfile pins the
complete dependency tree. Runtime fonts and license texts are bundled locally.
