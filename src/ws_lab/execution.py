"""Explicit fresh-public execution using the released native components.

Outputs are user-local evidence, never publication data or historical validation.
No model, task, torch, or transport is imported until an explicit execution route.
"""
import copy
import json
import os
from pathlib import Path
import uuid

from .io import canonical, digest, file_hash, read_json, state_hash, write_json

SLOTS = ('baseline', 'Sol', 'Astra', 'joint')
FRESH = 'FRESH_PUBLIC_LM_V1'
NOOP = {'ops': []}
ROOT = Path(__file__).resolve().parents[2]


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def exclusive(path, value):
    with Path(path).open('xb') as stream:
        stream.write(canonical(value) + b'\n')


def source_hashes():
    root = Path(__file__).parent
    return {str(p.relative_to(root)): file_hash(p) for p in
            sorted(list(root.glob('*.py')) + list((root/'resources').glob('*.txt')))}


def inventory(directory):
    return {str(p.relative_to(directory)): file_hash(p) for p in sorted(Path(directory).rglob('*'))
            if p.is_file()}


def panels(seed):
    # Accepted pilot panel order: one RNG, train then validation then both finals.
    import numpy as np
    rng = np.random.default_rng(seed)
    train = rng.permutation(2251).tolist()
    validation = rng.permutation(570).tolist()
    return {'diagnostic': train[:128], 'feedback': validation[:128],
            'parity': train[:64], 'smoke': train[:8], 'extra_probes': train[:32],
            'arc_final': rng.permutation(2376).tolist()[:512],
            'piqa_final': rng.permutation(1838).tolist()[:256]}


def validate_config(config, command):
    require(config.get('execution') == 'fresh-public-v1',
            'explicit execution=fresh-public-v1 required; historical DEV_HISTORY bindings are not portable')
    require(config.get('arm') in ('Adult', 'LM'), 'arm must be Adult or LM')
    require(command != 'run' or config['arm'] == 'LM', 'run supports LM only; Adult supports frozen replay')
    require(config.get('seed') in (101, 202, 303), 'fixed seed 101/202/303 required')
    if config['arm'] == 'LM':
        from .lm_runtime import validate_profile
        validate_profile(config['lm'])
        require(config['lm']['dtype'] == 'float32', 'fresh LM uses corrected float32 prompt/patches')
        require(config['lm'].get('candidate_limit') == 5, 'five candidate opportunities required')
        require(config.get('backend_acceptance') == 'declared-runtime-engineering-not-native64',
                'explicit new-run engineering runtime acceptance required')


class LMExecution:
    """Offline pinned loader and canonical scorer; no substitute model or scoring."""
    def __init__(self, config, model_dir, dataset_dir):
        from .lm_scoring import MODEL_REVISION, REVISIONS, provenance, offline
        from .lm_runtime import inference_identity, validate_profile
        self.config = config
        self.runtime = config['lm']
        validate_profile(self.runtime)
        # This is the user's datasets cache; HF offline mode forbids downloads.
        os.environ['HF_DATASETS_CACHE'] = str(dataset_dir.resolve())
        offline()
        self.model_dir = model_dir
        self.model_hashes = {p.name: file_hash(p) for p in sorted(model_dir.iterdir()) if p.is_file()}
        require(bool(self.model_hashes), 'empty checkpoint')
        require(any(n.endswith('.safetensors') for n in self.model_hashes), 'safetensors checkpoint required')
        for name in self.model_hashes:
            metadata = model_dir / '.cache/huggingface/download' / (name + '.metadata')
            require(metadata.exists() and metadata.read_text().splitlines()[0] == MODEL_REVISION,
                    'checkpoint source revision metadata missing/mismatched')
        self.identity = inference_identity(self.runtime)
        self.provenance = provenance(self.runtime)
        self.data_revisions = REVISIONS
        self.panels = panels(config['seed'])
        self.model = self.scorer = self.space = None
        self.tasks = {}

    def load(self):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from .lm_patches import LMPatchSpace
        from .lm_scoring import CanonicalScorer
        require(self.runtime['device'] != 'mps' or torch.backends.mps.is_available(), 'MPS unavailable')
        tokenizer = AutoTokenizer.from_pretrained(self.model_dir, local_files_only=True)
        self.model = AutoModelForCausalLM.from_pretrained(self.model_dir, local_files_only=True,
                dtype=torch.float32, attn_implementation='eager').eval()
        self.model.requires_grad_(False)
        self.model.to(self.runtime['device'])
        self.scorer = CanonicalScorer(self.model, tokenizer, self.identity)
        self.space = LMPatchSpace(self.model, dtype=torch.float32)
        self.scorer.bind_prediction_space(self.space)

    def task(self, name):
        from .lm_scoring import task, final_task
        if name not in self.tasks:
            current = task(name)
            final_task(current, name)
            expected = {'arc_easy': {'train': 2251, 'validation': 570, 'test': 2376},
                        'piqa': {'validation': 1838}}[name]
            require(all(len(current.dataset[s]) == n for s, n in expected.items()), 'task panel size changed')
            self.tasks[name] = current
        return self.tasks[name]

    def metadata(self):
        from .lm_scoring import MODEL_REVISION
        return {'inference_identity': self.identity, 'provenance': self.provenance,
                'model_hashes': self.model_hashes, 'model_revision': MODEL_REVISION,
                'data_revisions': self.data_revisions, 'panels': self.panels,
                'fingerprints': {split: getattr(self.task('arc_easy').dataset[split], '_fingerprint', None)
                                 for split in ('train', 'validation')}}

    def apply(self, patch):
        return self.space.apply(patch)

    def weight_key(self):
        from .lm_patches import prediction_binding
        return prediction_binding(self.scorer).key()

    def work(self):
        return dict(self.scorer.work) if self.scorer else {}

    def close(self):
        try:
            if self.space is not None:
                self.space.rollback()
        finally:
            if self.scorer is not None:
                self.scorer.close()


def lm_factory(config, model_dir, dataset_dir):
    return LMExecution(config, model_dir, dataset_dir)


def driver_factory(editor, directory, instructions, schema, cli):
    from .driver import NativeDriver
    return NativeDriver(editor, directory, instructions=instructions, schema=schema, codex_cli=cli)


def prompt_hashes():
    return {str(p.relative_to(ROOT)): file_hash(p) for p in sorted((ROOT/'prompts/v2').glob('*.txt'))}


def corrected_instructions():
    instructions = (ROOT/'prompts/v2/lm_editor.txt').read_text()
    require(instructions.count('float32 before application.') == 1
            and 'float16 before application.' not in instructions, 'corrected float32 prompt required')
    return instructions


def editor(controller, driver, view, trace_path):
    """Accepted lm_experiment.editor loop, with explicit fresh trace ownership."""
    from .driver import bounded_payload, BudgetExhausted, InvalidResponse, BlockedRoute
    from .lm_patches import action_schema
    transcript = [{'role': 'user', 'content': {'initial_view': view, 'action_schema': action_schema()}}]
    status, reason = 'BLOCKED', None
    try:
        bounded_payload(transcript)
        driver.preflight()
        for _ in range(15):
            if controller.shared.turns >= controller.shared.limit or controller.evaluations >= controller.limit:
                break
            response = driver.turn(transcript)
            action = response['action']
            result = controller.handle(action)
            transcript += [{'role': 'assistant', 'content': action}, {'role': 'user', 'content': result}]
            bounded_payload(transcript)
            if controller.locked is not None:
                break
        controller.lock_best()
        status = 'LOCKED'
    except BudgetExhausted:
        controller.lock_best()
        status, reason = 'LOCKED', 'budget exhausted; best valid candidate locked'
    except InvalidResponse:
        status, reason = 'INVALID', 'invalid editor response'
    except BlockedRoute:
        reason = 'route failure; no retry'
    finally:
        write_json(trace_path, transcript)
    return {'status': status, 'reason': reason, 'driver': driver.metadata,
            'usage_events': driver.events, 'controller': controller.record()}


def develop(out, backend, prepared, cli):
    from .controller import SharedBudget
    from .lm_controller import LMController
    from .lm_scoring import aggregate
    from .lm_patches import action_schema
    from .experience import SourceRun, audit_exposure, build_experience
    from .cowork import Scheduler
    source = out/'sources'
    source.mkdir()
    # Dedicated source directory stays free of all later joint/final markers.
    exclusive(source/'fresh-public.json', {'scope': FRESH, 'run_id': prepared['run_id']})
    exclusive(source/'prepared.json', prepared)
    arc = backend.task('arc_easy')
    scorer, space = backend.scorer, backend.space
    baseline = {'index': 0, 'patch': NOOP, 'stats': space.apply(NOOP)}
    rows = scorer.score(arc, 'validation', backend.panels['feedback'])
    baseline.update(predictions=rows, metrics=aggregate(rows))
    diagnostic = scorer.score(arc, 'train', backend.panels['diagnostic'])
    view = {'architecture': backend.model.config.to_dict(), 'stats': space.stats(),
            'diagnostic': [{'document': arc.dataset['train'][i], 'prediction': row}
                for i, row in zip(backend.panels['diagnostic'], diagnostic, strict=True)],
            'baseline': {k: baseline[k] for k in ('index', 'metrics', 'stats')},
            'candidate_limit': 5, 'probe_limit': 5, 'inference': backend.runtime,
            'selection': 'acc_norm desc, norm/count/index asc'}
    view['architecture'].pop('_name_or_path', None)
    exclusive(source/'baseline.json', baseline)
    exclusive(source/'editor_initial_view.json', view)
    slots = {'baseline': copy.deepcopy(NOOP)}
    paired = SharedBudget(limit=30)
    conditions = {}
    instructions = corrected_instructions()
    for name in ('Sol', 'Astra'):
        space.rollback()
        controller = LMController(space, scorer, arc, backend.panels, baseline, 5, paired)
        driver = driver_factory(name, out/'editor_runtime'/name, instructions, action_schema(), cli)
        compact = {k: v for k, v in view.items() if k != 'diagnostic'}
        compact['diagnostic_summary'] = {'n': len(diagnostic), 'metrics': aggregate(diagnostic)}
        record = editor(controller, driver, compact, source/f'{name}_transcript.json')
        exclusive(source/f'{name}_candidates.json', record)
        require(record['status'] == 'LOCKED' and controller.evaluations == 5,
                'independent source did not finish five candidate opportunities')
        slots[name] = copy.deepcopy(controller.locked['patch'])
        saved = space.save(source/'patches'/name, slots[name])
        conditions[name] = {'status': 'LOCKED', 'driver': driver.metadata,
            'record_hash': file_hash(source/f'{name}_candidates.json'), 'patch_hash': saved}
    exclusive(source/'search.json', {'conditions': conditions,
        'prepared_hash': file_hash(source/'prepared.json'), 'total_target_work': backend.work()})
    exclusive(source/'selection.json', {'status': 'LOCKED',
        'search_hash': file_hash(source/'search.json'),
        'conditions': {'clean': {'status': 'LOCKED', 'patch': NOOP}, **conditions}})
    # Freeze source closure before any joint editor call. No copied private audits.
    exclusive(source/'source-freeze.json', inventory(source))
    specs = [SourceRun(source, 'LM', name) for name in ('Sol', 'Astra')]
    audit = out/'source-audit'
    audit_exposure(specs, audit, human_exposed=False, agent_exposed=False,
                   final_dependent_advice=False, piqa_exposed=False)
    experience = build_experience(specs, audit)
    exclusive(out/'history.canonical.json', json.loads(experience.packet('AS_WARM')))
    exclusive(out/'history_sources.json', json.loads(experience.source_manifest('AS_WARM')))
    identity = {k: json.loads(experience.packet('AS_WARM'))[k] for k in
                ('arm', 'seed', 'origin_hash', 'panel_hash', 'protocol_hash')}
    space.rollback()
    controller = LMController(space, scorer, arc, backend.panels, baseline, 5,
                              SharedBudget(limit=30), turn_limit=30)
    drivers = [driver_factory(name, out/'editor_runtime'/'joint'/name,
               instructions, action_schema(), cli) for name in ('Astra', 'Sol')]
    scheduler = Scheduler(controller, view, drivers, condition='AS_WARM', identity=identity,
        feedback_mode='DEV_HISTORY', experience=experience, context_policy=FRESH)
    # Native scheduler has its own role prompt. Precision is in its validated view.
    scheduler.instructions = (ROOT/'src/ws_lab/resources/cowork_editor.txt').read_text()
    require(scheduler.adapter.view['inference']['dtype'] == backend.runtime['dtype'], 'joint precision mismatch')
    result = scheduler.run()
    exclusive(out/'joint.json', json.loads(result.record))
    exclusive(out/'joint_controller.json', controller.record())
    exclusive(out/'joint_transcripts.json', scheduler.transcripts)
    record = json.loads(result.record)
    require(record['status'] == 'COMPLETE' and record['completed_slots'] == 5, 'joint development incomplete')
    slots['joint'] = json.loads(next(s.data for s in result.snapshots if s.slot == 5))['patch']
    space.save(out/'patches/joint', slots['joint'])
    space.rollback()
    return slots


def native_source(spec):
    """Fresh-only admission into unchanged native ledger/audit/packet validation.

    Legacy _native guards remain in experience.py. This branch accepts only our
    own complete, independently frozen native source closure and new-run gate.
    """
    from .experience import _Native, _ledger, _has_final_feedback, MODELS
    run = Path(spec.run)
    require(spec.arm == 'LM', 'fresh source is LM only')
    frozen = read_json(run/'source-freeze.json')
    require(inventory(run) == {**frozen, 'source-freeze.json': file_hash(run/'source-freeze.json')},
            'source freeze changed')
    p = read_json(run/'prepared.json')
    marker = read_json(run/'fresh-public.json')
    require(marker == {'scope': FRESH, 'run_id': p['run_id']} and p['scope'] == FRESH, 'fresh source identity')
    require(p['source_hashes'] == source_hashes() and p['prompt_hashes'] == prompt_hashes(), 'source code/prompt changed')
    require(p['backend_gate']['status'] == 'DECLARED_RUNTIME_VERIFIED_NOT_NATIVE64'
            and p['backend_gate']['run_id'] == p['run_id'], 'new-run runtime gate required')
    selection, search = read_json(run/'selection.json'), read_json(run/'search.json')
    require(selection['status'] == 'LOCKED' and selection['search_hash'] == file_hash(run/'search.json')
            and search['prepared_hash'] == file_hash(run/'prepared.json'), 'source selection binding')
    require(selection['conditions'] == {'clean': {'status': 'LOCKED', 'patch': NOOP}, **search['conditions']},
            'source conditions changed')
    for name in ('Sol', 'Astra'):
        chosen = selection['conditions'][name]
        require(chosen['status'] == 'LOCKED' and chosen['record_hash'] == file_hash(run/f'{name}_candidates.json'),
                'both independent sources must lock')
    record = read_json(run/f'{spec.editor}_candidates.json')
    chosen = selection['conditions'][spec.editor]
    driver = record['driver']
    require(record['status'] == 'LOCKED' and driver == chosen['driver']
        and driver['requested_model'] == MODELS[spec.editor]
        and driver.get('resolved_model') in (None, MODELS[spec.editor])
        and driver['route'] == 'native Codex CLI', 'native source route mismatch')
    c = record['controller']
    require(c['candidate_limit'] == c['evaluations'] == 5 and c['candidates'][0]['patch'] == NOOP,
            'five independent native candidate opportunities required')
    best = min(c['candidates'], key=lambda r: (-r['metrics']['acc_norm'], r['stats']['norm'], r['stats']['count'], r['index']))
    require(c['locked'] == best, 'source selection changed')
    saved = read_json(run/'patches'/spec.editor/'patch.json')
    require(saved['patch'] == best['patch'] and digest(saved) == chosen['patch_hash']
            and file_hash(run/'patches'/spec.editor/'weights.safetensors') == saved['weights_sha256'],
            'source saved patch changed')
    require(not _has_final_feedback(record), 'final feedback denied')
    source, catalog = _ledger(spec, c, record, file_hash(run/'selection.json'),
                             file_hash(run/'prepared.json'), chosen['record_hash'])
    identity = {'arm': 'LM', 'seed': p['seed'], 'origin_hash': p['origin_hash'],
                'panel_hash': p['panel_hash'], 'protocol_hash': p['protocol_hash']}
    bindings = tuple((run/n, h) for n, h in sorted(frozen.items())) + ((run/'source-freeze.json', file_hash(run/'source-freeze.json')),)
    return _Native(canonical(identity), canonical(source), bindings, tuple(catalog), False, run,
                   tuple(sorted(p['source_hashes'].items())))


def freeze(out, slots, backend, prepared):
    require(set(slots) == set(SLOTS), 'all four endpoints must freeze before final scoring')
    endpoints = {}
    for name in SLOTS:
        stats = backend.apply(slots[name])
        endpoints[name] = {'patch': copy.deepcopy(slots[name]), 'patch_sha256': digest(slots[name]),
                           'stats': stats, 'executed_weight_key': backend.weight_key()}
    frozen = {'run_id': prepared['run_id'], 'prepared_sha256': file_hash(out/'prepared.json'), 'slots': endpoints}
    exclusive(out/'frozen.json', frozen)
    return frozen


def assess_lm(out, backend, frozen):
    from .lm_scoring import aggregate
    require(read_json(out/'frozen.json') == frozen and set(frozen['slots']) == set(SLOTS), 'final before freeze denied')
    exclusive(out/'assessment-consumed.json', {'run_id': frozen['run_id'], 'frozen_sha256': digest(frozen)})
    cache, predictions, results, groups = {}, {}, {}, {}
    try:
        for name, split, panel in (('arc_easy', 'test', 'arc_final'), ('piqa', 'validation', 'piqa_final')):
            task = backend.task(name)
            indices = backend.panels[panel]
            groups[name] = {}
            for method in SLOTS:
                endpoint = frozen['slots'][method]
                backend.apply(endpoint['patch'])
                require(backend.weight_key() == endpoint['executed_weight_key'], 'frozen executed state changed')
                key = backend.scorer.prediction_key(task, split, indices)
                reused = key in cache
                if not reused:
                    backend.scorer.partial_rows = []
                    cache[key] = backend.scorer.score(task, split, indices, final=True)
                    require(backend.scorer.prediction_key(task, split, indices) == key, 'scoring context changed')
                    require([r['source_index'] for r in cache[key]] == indices
                        and all(r['task'] == name and r['split'] == split for r in cache[key]), 'scored panel changed')
                groups[name].setdefault(key, []).append(method)
                predictions.setdefault(method, {})[name] = cache[key]
                results.setdefault(method, {})[name] = {'status': 'COMPLETE', 'metrics': aggregate(cache[key]), 'reused': reused}
                write_json(out/'assessment_predictions.json', predictions)
                write_json(out/'assessment_results.json', results)
                write_json(out/'assessment_groups.json', {n: list(g.values()) for n,g in groups.items()})
                write_json(out/'assessment_work.json', backend.work())
    except BaseException as exc:
        write_json(out/'assessment_failure.json', {'status': 'FAILED_CONSUMED_NO_RETRY',
            'error_type': type(exc).__name__, 'partial_results': results,
            'partial_rows': getattr(backend.scorer, 'partial_rows', [])})
        raise
    finally:
        write_json(out/'assessment_work.json', backend.work())
    return results


def adult_replay(out, config, model_dir, dataset_dir, prepared):
    import numpy as np
    import torch
    from .model import probabilities
    from .patches import PatchSpace
    from .metrics import metrics
    graph = read_json(model_dir/'adult_graph.json')
    root = {k: torch.tensor(v, dtype=torch.float32) for k,v in graph['root'].items()}
    clean = {k: torch.tensor(v, dtype=torch.float32) for k,v in graph['clean'].items()}
    mask = torch.tensor(graph['permanent_mask'], dtype=torch.bool)
    space = PatchSpace(root, mask)
    require(state_hash(root) == graph['root_state_sha256'] and state_hash(clean) == graph['clean_state_sha256'],
            'Adult released tensors changed')
    reconstructed = {k: v.clone() for k,v in clean.items()}
    reconstructed['fc2.weight'][mask] = 0
    require(state_hash(reconstructed) == state_hash(root), 'Adult clean/mask reconstruction failed')
    states = {'clean': clean}
    endpoints = {}
    require(set(SLOTS) <= set(graph['variants']), 'all four Adult endpoints required')
    for name, row in graph['variants'].items():
        state, stats = space.apply(row['patch'])
        require(stats == row['stats'] and state_hash(state) == row['executed_weight_sha256'], 'Adult patch graph mismatch')
        states[name] = state
        endpoints[name] = {'patch': row['patch'], 'executed_weight_sha256': state_hash(state)}
    exclusive(out/'frozen.json', {'run_id': prepared['run_id'], 'slots': endpoints, 'clean_state_sha256': state_hash(clean)})
    exclusive(out/'assessment-consumed.json', {'run_id': prepared['run_id'],
        'frozen_sha256': file_hash(out/'frozen.json')})
    # Features remain in the user-provided local npz, never copied to output.
    with np.load(dataset_dir/'test.npz', allow_pickle=False) as panel:
        x, y = panel['x'], panel['y']
        require(x.ndim == 2 and x.shape == (len(y), root['fc1.weight'].shape[1])
                and len(y) > 0 and np.isfinite(x).all() and set(np.unique(y)) <= {0,1}, 'invalid Adult offline panel')
        panel_hash = digest({'file': file_hash(dataset_dir/'test.npz'), 'n': len(y)})
        cache, predictions, results, groups = {}, {}, {}, {}
        forwards = 0
        try:
            for name, state in states.items():
                key = digest([state_hash(state), panel_hash, 'CPU-float32-probabilities'])
                reused = key in cache
                if not reused:
                    forwards += 1
                    write_json(out/'assessment_work.json', {'forwards': forwards, 'examples': len(y)*forwards})
                    cache[key] = probabilities(state, x).tolist()
                groups.setdefault(key, []).append(name)
                predictions[name] = {'probabilities': cache[key], 'labels': y.tolist(), 'paired_ids': list(range(len(y)))}
                results[name] = {'status': 'COMPLETE', 'metrics': metrics(y, cache[key]), 'reused': reused}
                write_json(out/'assessment_predictions.json', predictions)
                write_json(out/'assessment_results.json', results)
                write_json(out/'assessment_groups.json', list(groups.values()))
                write_json(out/'assessment_work.json', {'forwards': forwards, 'examples': len(y)*forwards})
        except BaseException as exc:
            write_json(out/'assessment_failure.json', {'status': 'FAILED_CONSUMED_NO_RETRY',
                'error_type': type(exc).__name__, 'partial_results': results, 'partial_rows': []})
            raise
    return results


def execute(args):
    """Claim once before any forward/editor; failure is terminal, never resumed."""
    out = args.output
    require(not out.exists(), 'new output path required; existing runs may never be consumed')
    config = read_json(args.config)
    validate_config(config, args.command)
    require(args.model_dir.is_dir() and args.dataset_dir.is_dir(), 'user-owned offline input directories required')
    require(all(not out.resolve().is_relative_to(p.resolve()) and not p.resolve().is_relative_to(out.resolve())
                for p in (args.model_dir, args.dataset_dir)), 'output must be separate from offline inputs')
    # Freeze every input, without copying original features or third-party files.
    inputs = {'config': file_hash(args.config), 'model': inventory(args.model_dir), 'dataset': inventory(args.dataset_dir)}
    require(inputs['model'] and inputs['dataset'], 'empty offline input directory')
    if args.command == 'replay' and config['arm'] == 'LM':
        require('patches' in config, 'frozen patch descriptor file required')
        patch_path = args.config.parent/config['patches']
        inputs['patches'] = file_hash(patch_path)
        slots = read_json(patch_path)
        # Accept the exact exported slots mapping, or a fresh frozen receipt.
        slots = slots.get('slots', slots)
        slots = {n: row.get('patch', row) for n,row in slots.items()}
        require(set(slots) == set(SLOTS), 'four frozen LM patches required')
    run_id = uuid.uuid4().hex
    backend = None
    out.mkdir(parents=True, exist_ok=False)
    exclusive(out/'consumed.json', {'run_id': run_id, 'single_use': True, 'command': args.command})
    prepared = {'scope': FRESH, 'run_id': run_id, 'seed': config['seed'], 'command': args.command,
        'arm': config['arm'], 'config': config, 'inputs': inputs, 'source_hashes': source_hashes(),
        'prompt_hashes': prompt_hashes(),
        'historical_exact_validation': False, 'status': 'PREPARED'}
    try:
        exclusive(out/'input-bindings.json', prepared)
        if config['arm'] == 'Adult':
            exclusive(out/'prepared.json', prepared)
            results = adult_replay(out, config, args.model_dir, args.dataset_dir, prepared)
        else:
            backend = lm_factory(config, args.model_dir, args.dataset_dir)
            backend.load()
            prepared.update(backend.metadata())
            prepared['origin_hash'] = digest([prepared['model_revision'], prepared['model_hashes']])
            prepared['panel_hash'] = digest([backend.panels, prepared['data_revisions']])
            prepared['protocol_hash'] = digest([config, prepared['source_hashes'], prepared['provenance']])
            prepared['backend_gate'] = {'status': 'DECLARED_RUNTIME_VERIFIED_NOT_NATIVE64', 'run_id': run_id,
                'runtime': backend.identity, 'acceptance': config['backend_acceptance'],
                'scope': 'actual model dtype/device/eager and pinned harness verified; no CPU parity claim'}
            exclusive(out/'prepared.json', prepared)
            if args.command == 'run':
                slots = develop(out, backend, prepared, args.codex_cli)
            frozen = freeze(out, slots, backend, prepared)
            results = assess_lm(out, backend, frozen)
        # Input drift invalidates completion, while retaining all partial outputs.
        require(inputs['config'] == file_hash(args.config)
            and inputs['model'] == inventory(args.model_dir) and inputs['dataset'] == inventory(args.dataset_dir)
            and prepared['source_hashes'] == source_hashes() and prepared['prompt_hashes'] == prompt_hashes(),
            'execution inputs/code/prompt changed')
        if 'patches' in inputs:
            require(file_hash(patch_path) == inputs['patches'], 'patch descriptors changed')
        value = {'status': 'COMPLETE', 'run_id': run_id, 'historical_exact_validation': False,
                 'results_sha256': digest(results)}
    except BaseException as exc:
        value = {'status': 'FAILED_CONSUMED_NO_RETRY', 'run_id': run_id, 'error_type': type(exc).__name__}
        write_json(out/'terminal.json', value)
        raise
    finally:
        if backend is not None:
            write_json(out/'work.json', backend.work())
            try:
                backend.close()
            except BaseException as exc:
                write_json(out/'terminal.json', {'status': 'FAILED_CONSUMED_NO_RETRY',
                    'run_id': run_id, 'error_type': type(exc).__name__, 'phase': 'cleanup'})
                raise
    exclusive(out/'terminal.json', value)
    return value
