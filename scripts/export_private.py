"""Allowlisted, read-only transformation of completed private evidence. No scorer calls."""
import argparse
from pathlib import Path
import numpy as np
from ws_lab.io import digest, file_hash, read_json, write_json, state_hash
from ws_lab.publication import require, analyse_data, ADULT_METHODS, LM_METHODS

WORK = ('attempted_target_calls', 'attempted_examples', 'target_calls', 'examples', 'forwards',
        'requests', 'elapsed_seconds', 'wall_seconds', 'feedback_examples', 'probe_examples',
        'diagnostic_examples', 'training', 'editor_calls')
DRIVER = ('requested_model', 'resolved_model', 'reasoning', 'route', 'cli_version', 'catalog_sha256',
          'config_sha256', 'max_turns', 'timeout_seconds', 'max_wall_seconds', 'max_active_seconds',
          'accumulated_active_seconds', 'status', 'route_status')
STATS = ('count', 'norm', 'relative_norm', 'fraction', 'unique_parameters', 'relative_norms', 'applied_hashes')
BUDGET = ('candidate_limit', 'evaluations', 'editor_turns', 'combined_turns', 'probe_queries', 'probe_limit')
LM_NUMERIC = ('gold', 'preferred', 'preferred_norm', 'acc', 'acc_norm', 'choice_char_lengths',
              'continuation_token_lengths', 'loglikelihoods')


def pick(value, keys):
    return {k: value[k] for k in keys if k in value}


class Export:
    def __init__(self, output):
        self.output = output
        self.receipts = {}

    def read(self, path, role):
        data = read_json(path)
        self.receipts[role] = file_hash(path)
        return data

    def save(self, name, data):
        write_json(self.output / name, data)
        return name

    def freeze(self, directory, role, *, controls=False):
        frozen = self.read(directory / 'frozen.json', role + '_freeze')
        marker_name = 'supplement_finalized.json' if controls else 'assessment_started.json'
        marker = self.read(directory / marker_name, role + '_before_final_marker')
        require(marker['frozen_sha256'] == file_hash(directory / 'frozen.json'), 'freeze/assessment binding changed')
        if not controls:
            for row in frozen['slots'].values():
                if row['status'] == 'LOCKED':
                    require(digest(row['patch']) == row['patch_sha256'], 'frozen patch changed')
        return frozen


def adult_predictions(export, prior, controls=None):
    original = export.read(prior / 'Adult/assessment_predictions.json', 'adult_original_predictions')
    rows = dict(original)
    if controls is not None:
        extra = export.read(controls / 'predictions.json', 'adult_control_predictions')
        require(set(extra) <= {'clean', 'random', 'grid'}, 'unexpected control method')
        rows.update(extra)
    reference = original['baseline']
    require(len(set(reference['source_ids'])) == len(reference['labels']) == 16281, 'Adult panel size/order invalid')
    output = {}
    for name, row in rows.items():
        require(name in ADULT_METHODS and row['source_ids'] == reference['source_ids']
                and row['labels'] == reference['labels'], 'unpaired Adult predictions')
        numeric = {'paired_ids': list(range(len(row['labels']))), 'labels': row['labels'],
                   'probabilities': row['probabilities']}
        output[name] = {**numeric, 'array_sha256': digest(numeric)}
    export.save('adult_predictions.json', {'dtype': 'float64', 'inference_dtype': 'float32', 'methods': output})
    return reference


def safe_lm(predictions, expected_panels=None):
    result, panel_order = {}, {}
    for name in LM_METHODS:
        if name not in predictions:
            continue
        result[name] = {}
        for task, rows in predictions[name].items():
            require(task in ('arc_easy', 'piqa'), 'unknown saved LM task')
            ids = [(r['source_id'], r['source_index']) for r in rows]
            require(len(set(ids)) == len(ids) > 0, 'duplicate/empty LM panel')
            require(all(r['task'] == task and r['split'] == ('test' if task == 'arc_easy' else 'validation') for r in rows),
                    'LM split/task mismatch')
            require(task not in panel_order or panel_order[task] == ids, 'unpaired private LM rows')
            if expected_panels is not None and task in expected_panels:
                require(expected_panels[task] == ids, 'v1/v2 panel order changed')
            panel_order[task] = ids
            result[name][task] = [{**pick(row, LM_NUMERIC), 'paired_id': i} for i, row in enumerate(rows)]
    return result, panel_order


def candidate_record(value):
    controller = value.get('controller', value)
    rows = []
    for row in controller['candidates']:
        clean = pick(row, ('index', 'patch', 'patch_digest', 'metrics', 'prediction_reuse'))
        clean['stats'] = pick(row['stats'], STATS)
        rows.append(clean)
    locked = controller.get('locked')
    result = {**pick(controller, BUDGET), 'phase': 'development', 'candidates': rows,
        'selected_index': locked['index'] if locked else None,
        'target_work': pick(controller.get('target_work', {}), WORK)}
    # Native events do not always identify actions or evaluation slots. Retain
    # their order and available associations without inferring them from turns.
    if 'events' in controller:
        events = []
        for event in controller['events']:
            clean = {k: event[k] for k in ('turn', 'index', 'candidate_index', 'evaluation_index', 'slot')
                     if type(event.get(k)) is int}
            if event.get('status') in ('OK', 'INVALID', 'BLOCKED'):
                clean['status'] = event['status']
            if event.get('action') in ('inspect_stats', 'inspect_slice', 'probe_summary',
                                       'evaluate_candidate', 'submit'):
                clean['action'] = event['action']
            if event.get('status') in ('INVALID', 'BLOCKED'):
                clean['metrics'] = None
            events.append(clean)
        result['events'] = events
    if 'driver' in value:
        result['editor'] = pick(value['driver'], DRIVER)
    if 'usage_events' in value:
        # Counts are observed calls, not target work and not provider session identities.
        events = value['usage_events']
        result['editor_calls'] = {'recorded': len(events),
            'submitted_true': sum(e.get('submitted') is True for e in events),
            'submitted_unknown': sum(e.get('submitted') is None for e in events),
            'by_purpose': {p: sum(e.get('purpose') == p for e in events)
                           for p in ('capability_canary', 'scientific_controller_call')}}
    return result


def candidates(export, run, arm_dir, role):
    result = {}
    for name in ('Sol', 'Astra', 'joint'):
        path = arm_dir / 'joint_controller.json' if name == 'joint' else run / f'{name}_candidates.json'
        if path.exists():
            result[name] = candidate_record(export.read(path, role + '_' + name + '_candidates'))
    if role == 'adult':
        for name in ('random', 'grid'):
            result[name] = candidate_record(export.read(run / f'{name}_candidates.json', role + '_' + name + '_candidates'))
    joint_path = arm_dir / 'joint.json'
    if joint_path.exists():
        joint = export.read(joint_path, role + '_joint_scheduler')
        if 'joint' in result:
            result['joint']['actors'] = [pick(r, ('actor', *DRIVER)) for r in joint.get('actors', [])]
            result['joint']['actor_counts'] = joint.get('actor_counts', [])
            result['joint']['editor_calls'] = {'recorded': len(joint.get('calls', [])),
                'submitted_true': sum(c.get('submitted') is True for c in joint.get('calls', [])),
                'submitted_unknown': sum(c.get('submitted') is None for c in joint.get('calls', []))}
    return result


def graph(export, run, frozen):
    # Tensor arithmetic/validation only. Never import a model or call probabilities.
    import torch
    from safetensors.torch import load_file
    from ws_lab.patches import PatchSpace
    clean = load_file(str(run / 'clean.safetensors'))
    origin = load_file(str(run / 'damaged.safetensors'))
    mask = load_file(str(run / 'mask.safetensors'))['mask']
    trained = export.read(run / 'trained.json', 'adult_training_metadata')
    require(state_hash(clean) == trained['clean_hash'] and state_hash(origin) == trained['damaged_hash'],
            'Adult tensor identity changed')
    for name in ('clean', 'damaged', 'mask'):
        export.receipts['adult_' + name + '_tensor'] = file_hash(run / f'{name}.safetensors')
    space = PatchSpace(origin, mask)
    variants = {}
    for name in ('baseline', 'Sol', 'Astra', 'joint', 'random', 'grid'):
        if name in frozen['slots']:
            slot = frozen['slots'][name]
            if slot['status'] != 'LOCKED':
                continue
            patch = slot['patch']
        else:
            meta = export.read(run / 'patches' / name / 'patch.json', 'adult_' + name + '_patch')
            # Native loader verifies serialized weights and exact patch definition.
            state, _ = space.load(run / 'patches' / name)
            patch = meta['patch']
        state, stats = space.apply(patch)
        if name in frozen['slots']:
            require(state_hash(state) == frozen['slots'][name]['executed_weight_sha256'], 'Adult executed weights changed')
        before, after = origin['fc2.weight'], state['fc2.weight']
        ix = torch.nonzero(after != before).tolist()
        variants[name] = {'patch': patch, 'stats': stats, 'executed_weight_sha256': state_hash(state),
            'changes': [{'row': r, 'column': c, 'before': float(before[r,c]), 'after': float(after[r,c])} for r,c in ix]}
    return {'architecture': {'layers': [origin['fc1.weight'].shape[1], 32, 16, 1],
            'activations': ['relu', 'relu', 'sigmoid'], 'dtype': 'float32', 'editable_tensor': 'fc2.weight'},
        'clean_state_sha256': trained['clean_hash'], 'root_state_sha256': trained['damaged_hash'],
        'clean': {k: v.tolist() for k,v in clean.items()}, 'root': {k:v.tolist() for k,v in origin.items()},
        'permanent_mask': mask.tolist(), 'variants': variants,
        'insufficient_damage': trained['insufficient_damage'], 'lesion_trials': trained['lesion_trials']}


def slots(frozen):
    return {name: pick(row, ('status', 'patch', 'patch_sha256', 'executed_weight_sha256', 'original_candidate_limit'))
            for name, row in frozen['slots'].items()}


def lm_metadata(export, directory, role, frozen, numeric, candidates_data):
    states = {}
    for name in LM_METHODS:
        row = frozen['slots'][name]
        if row['status'] == 'LOCKED':
            states.setdefault(row['executed_weight_sha256'], []).append(name)
    groups = list(states.values())
    for task in ('arc_easy', 'piqa'):
        for group in groups:
            values = [numeric[name][task] for name in group if task in numeric.get(name, {})]
            require(not values or all(v == values[0] for v in values), 'identical-weight predictions disagree')
    workpath = directory / 'assessment_work.json'
    devpath = directory / 'development_work.json'
    return {'status': 'MEASURED' if all(t in numeric.get(n,{}) for n in LM_METHODS for t in ('arc_easy','piqa')) else 'PARTIAL',
        'slots': slots(frozen), 'unique_executed_weight_groups': groups,
        'candidates': candidates_data,
        'development_work_total': pick(export.read(devpath, role + '_development_work').get('target_work', {}), WORK) if devpath.exists() else None,
        'assessment_work': pick(export.read(workpath, role + '_assessment_work'), WORK) if workpath.exists() else None,
        'scene': {'selected_operations': {n: r['patch']['ops'] for n,r in frozen['slots'].items() if r['status']=='LOCKED'},
            'scalar_samples': None,
            'scalar_sample_status': 'UNAVAILABLE: nonselected candidate tensors were not retained in the approved evidence; no model binary is read or invented',
            'selected_changes': [] if all(not r.get('patch',{}).get('ops',[]) for r in frozen['slots'].values()) else None}}


def export_all(args):
    output = args.output.resolve()
    inputs = [args.prior_scope.resolve(), args.adult_run.resolve(), args.piqa_supplement.resolve()]
    if args.publication_scope:
        require(args.publication_terminal, 'v2 export requires explicit --publication-terminal after science terminates')
        inputs.append(args.publication_scope.resolve())
    for path in inputs:
        require(not output.is_relative_to(path) and not path.is_relative_to(output), 'output overlaps private input')
    require(not output.exists() or not any(output.iterdir()), 'new empty output directory required')
    output.mkdir(parents=True, exist_ok=True)
    e = Export(output)
    prior, run = args.prior_scope, args.adult_run
    adult_frozen = e.freeze(prior / 'Adult', 'adult_original')
    lm_frozen = e.freeze(prior / 'LM', 'lm_v1')
    for native, arm, role in ((run, 'Adult', 'adult'), (prior/'lm_native', 'LM', 'lm_v1')):
        consumed=e.read(native/'finalized.json', role+'_canonical_consumption')
        require(consumed['frozen_sha256']==file_hash(prior/arm/'frozen.json'), 'canonical consumption/freeze mismatch')
    # Inspect no live scope unless the caller explicitly asserts terminal execution.
    v2numeric, v2panels = {}, None
    v2meta = {'status': 'PENDING', 'reason': 'publication v2 not imported before terminal execution'}
    control_dir, control_meta = None, {'status': 'PENDING'}
    v2frozen = None
    v2results = None
    control_results = None
    if args.publication_scope:
        new = args.publication_scope
        lm_dir = new / 'LM'
        terminal = (lm_dir / 'assessment_results.json').exists() or (lm_dir / 'assessment_failure.json').exists()
        if terminal:
            if (lm_dir / 'assessment_results.json').exists():
                res = e.read(lm_dir / 'assessment_results.json', 'lm_v2_results')
                v2results = res
                require(all(r['status'] in ('COMPLETE','MISSING') for r in res.values()), 'v2 results not terminal')
            v2frozen = e.freeze(lm_dir, 'lm_v2')
            consumed=e.read(new/'lm_native/finalized.json', 'lm_v2_canonical_consumption')
            require(consumed['frozen_sha256']==file_hash(lm_dir/'frozen.json'), 'v2 canonical consumption/freeze mismatch')
        controls = new / 'adult-controls'
        if (controls / 'results.json').exists():
            res = e.read(controls / 'results.json', 'adult_control_results')
            control_results = res
            require(set(res) == {'clean','random','grid'} and all(r['status']=='COMPLETE' for r in res.values()),
                    'controls not complete')
            cf = e.freeze(controls, 'adult_controls', controls=True)
            control_dir = controls
            control_meta = {'status': 'MEASURED', 'frozen_states': cf['states'],
                'work': pick(e.read(controls / 'work.json', 'adult_control_work'), WORK)}
    reference = adult_predictions(e, prior, control_dir)
    # Verify original saved panel binding, without exporting any feature rows or IDs.
    with np.load(run / 'test.npz', allow_pickle=False) as test:
        require(reference['labels'] == test['y'].tolist() and reference['source_ids'] == test['ids'].tolist(),
                'original Adult panel does not match saved predictions')
    adult_graph = graph(e, run, adult_frozen)
    if control_dir is not None:
        for name, expected in control_meta['frozen_states'].items():
            actual = adult_graph['clean_state_sha256'] if name=='clean' else adult_graph['variants'][name]['executed_weight_sha256']
            require(actual == expected, 'control graph/freeze identity mismatch')
    e.save('adult_graph.json', adult_graph)
    adult_candidates = candidates(e, run, prior/'Adult', 'adult')
    v1raw = e.read(prior/'LM/assessment_predictions.json', 'lm_v1_original_predictions')
    v1numeric, v1panels = safe_lm(v1raw)
    supplement = e.read(args.piqa_supplement/'predictions.json', 'lm_v1_piqa_supplement_predictions')
    presult = e.read(args.piqa_supplement/'result.json', 'lm_v1_piqa_supplement_result')
    require(presult['predictions_sha256'] == file_hash(args.piqa_supplement/'predictions.json'), 'PIQA supplement hash changed')
    require(all(s['executed_weight_sha256']==presult['executed_weight_sha256'] for s in lm_frozen['slots'].values()),
            'PIQA supplement belongs to different weights')
    joined = {n: {**v1raw[n], 'piqa': supplement} for n in LM_METHODS}
    v1numeric, v1panels = safe_lm(joined)
    v1meta = lm_metadata(e, prior/'LM', 'lm_v1', lm_frozen, v1numeric,
        candidates(e, prior/'lm_native', prior/'LM', 'lm_v1'))
    failure = e.read(prior/'LM/assessment_failure.json', 'lm_v1_original_assessment_failure')
    v1meta['actual_prediction_reuse'] = {n: r.get('reused_identical_weights', {}) for n,r in failure['partial_results'].items()}
    v1meta['original_assessment_status'] = failure['status']
    v1meta['piqa_supplement'] = {'status': presult['status'], 'work': pick(presult['work'], WORK),
        'unique_weight_groups': presult['unique_weight_groups'], 'separate_from_original_assessment': True}
    if v2frozen is not None:
        path = args.publication_scope/'LM/assessment_predictions.json'
        raw = e.read(path, 'lm_v2_predictions') if path.exists() else {}
        v2numeric, v2panels = safe_lm(raw, expected_panels=v1panels)
        v2meta = lm_metadata(e, args.publication_scope/'LM', 'lm_v2', v2frozen, v2numeric,
            candidates(e, args.publication_scope/'lm_native', args.publication_scope/'LM', 'lm_v2'))
    for version, numeric, status in [('v1',v1numeric,'MISSING'), ('v2',v2numeric,'PENDING' if v2frozen is None else 'MISSING')]:
        e.save(f'lm_{version}_predictions.json', {'methods': numeric, 'arrays_sha256': digest(numeric), 'missing_status': status})
    if args.amendment:
        amendment=e.read(args.amendment, 'prospective_publication_amendment')
        require(amendment['lm']['same_panels_as_v1'] is True and amendment['lm']['prior_final_exposure'] is True,
                'v2 exposure amendment differs')
    summary = analyse_data(output)
    original_results = e.read(prior/'Adult/assessment_results.json', 'adult_original_results')['slots']
    for name, row in original_results.items():
        if row['metrics'] is not None:
            require(summary['adult']['methods'][name]['metrics'] == row['metrics'], 'Adult saved metrics differ from actual evidence')
    for name, row in failure['partial_results'].items():
        for task, measured in row.get('metrics', {}).items():
            require(summary['lm']['versions']['v1']['tasks'][task][name]['metrics'] == measured, 'v1 LM actual metrics mismatch')
    for name in LM_METHODS:
        require(summary['lm']['versions']['v1']['tasks']['piqa'][name]['metrics'] == presult['method_metrics'][name], 'PIQA actual metrics mismatch')
    if control_results is not None:
        for name, row in control_results.items():
            require(summary['adult']['methods'][name]['metrics']==row['metrics'], 'Adult control actual metrics mismatch')
    if v2results is not None:
        for name, row in v2results.items():
            for task, measured in row.get('metrics', {}).items():
                require(summary['lm']['versions']['v2']['tasks'][task][name]['metrics']==measured, 'v2 LM actual metrics mismatch')
        v2meta['actual_prediction_reuse'] = {n:r.get('reused',{}) for n,r in v2results.items()}
    v1meta['tasks'] = summary['lm']['versions']['v1']['tasks']
    v2meta['tasks'] = summary['lm']['versions']['v2']['tasks']
    prepared = e.read(prior/'lm_native/prepared.json', 'lm_v1_prepared')
    runtime_keys = ('device', 'dtype', 'attention', 'runtime_profile')
    v1meta['runtime'] = pick(prepared['config'], runtime_keys)
    if v2frozen is not None:
        v2prepared = e.read(args.publication_scope/'lm_native/prepared.json', 'lm_v2_prepared')
        v2meta['runtime'] = pick(v2prepared['config'], runtime_keys)
        v2meta['frozen_patches'] = e.save('lm_v2_frozen_patches.json', slots(v2frozen))
    adult_prepared = e.read(run/'prepared.json', 'adult_prepared')
    project = Path(__file__).resolve().parents[1]
    prompts={str(p.relative_to(project)):file_hash(p) for base in ('prompts', 'src/ws_lab/resources')
             for p in sorted((project/base).rglob('*.txt'))}
    expected_v1='78cf1255146182c739127dcc0534ab446b05d6fe5435d8f155e41bde5d7dbcb3'
    require(prompts['prompts/v1/lm_editor.txt']==expected_v1, 'accepted v1 prompt changed')
    old=(project/'prompts/v1/lm_editor.txt').read_text()
    require((project/'prompts/v2/lm_editor.txt').read_text()==old.replace('float16 before application.','float32 before application.'),
            'accepted v2_instructions(float32) prompt changed')
    meta = {'schema_version': 1, 'units': {'scores':'fraction', 'chart_deltas':'percentage points = 100 * fraction difference',
        'norms':'L2 after execution dtype', 'changed_counts':'actual unequal executed scalars'},
        'seed':101, 'bootstrap':{'seed':101, 'draws':2000, 'adult':'paired class-stratified', 'lm':'paired examples'},
        'adult': {'primary_metric':'balanced_accuracy', 'methods':summary['adult']['methods'],
            'contrasts':summary['adult']['contrasts'],
            'predictions':'adult_predictions.json', 'graph':'adult_graph.json', 'candidates':adult_candidates,
            'slots':slots(adult_frozen), 'controls':control_meta,
            'assessment_work':pick(e.read(prior/'Adult/assessment_work.json','adult_assessment_work'),WORK),
            'insufficient_damage':adult_graph['insufficient_damage'], 'solo_candidate_allowance':10,'joint_candidate_allowance':5,'source_dataset_sha256':adult_prepared['source']},
        'lm': {'main_version':'v2', 'versions':{'v1':v1meta,'v2':v2meta},
            'predictions':{'v1':'lm_v1_predictions.json','v2':'lm_v2_predictions.json'},
            'model_revision':prepared['model_revision'], 'dataset_revisions':prepared['data_revisions'],
            'runtime':pick(prepared['config'],('device','dtype','attention','runtime_profile'))},
        'provenance': {'accepted_execution_commit':'ed15068c13ffb1cb1e3222d1056c1748b1e1292a',
            'source_receipts_sha256':e.receipts, 'original_slots_bound_before_finals':True,
            'new_slots_bound_before_new_finals':True if v2frozen is not None else None,
            'v2_analyst_exposed_to_v1_finals':True, 'v2_same_panels_not_independent_replication':True,
            'sources_independent_at_origin':True, 'joint_has_development_history_only':True,
            'prompt_v1_float16_wording_with_float32_runtime':True},
        'execution':{'status':'AVAILABLE_EXPLICIT_FUTURE_EXECUTION', 'details':'configs/source.json',
            'portable_verification':'OFFLINE_SYNTHETIC_ONLY',
            'portable_real_execution':'NOT_RUN',
            'recorded_measurements':{'adult':'MEASURED', 'adult_controls':control_meta['status'],
                                     'lm_v1':v1meta['status'], 'lm_v2':v2meta['status']}},
        'files':{p.name:file_hash(p) for p in sorted(output.glob('*.json'))}, 'prompts':prompts,
        'summary':summary, 'summary_sha256':digest(summary)}
    meta['manifest_sha256']=digest(meta)
    e.save('manifest.json',meta)
    return {'status':'EXPORTED', 'manifest_sha256':meta['manifest_sha256'],
            'lm_main_status':v2meta['status'], 'model_or_provider_calls':0}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('prior-scope','adult-run','piqa-supplement','output'):
        p.add_argument('--'+name, required=True, type=Path)
    p.add_argument('--publication-scope', type=Path)
    p.add_argument('--publication-terminal', action='store_true')
    p.add_argument('--amendment', type=Path)
    args=p.parse_args(argv)
    print(__import__('json').dumps(export_all(args)))


if __name__=='__main__':
    main()
