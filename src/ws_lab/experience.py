"""Stage1 replay only: no driver, target execution, selection or final access.

Trusted callers supply native run directories, never editor-supplied paths. Call
``audit_exposure`` with explicit exposure attestations, then ``build_experience``.
Only ``Experience.packet`` and ``read_history_patch`` are editor-facing. A future
scheduler must charge every lookup (including failures) to its auxiliary budget.
Patch schema checks here do not replace target legality checks on a new proposal.
"""
from dataclasses import dataclass, field
from pathlib import Path
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from jsonschema import ValidationError

from .controller import StrictValidator
from .io import canonical, digest, file_hash, read_json, state_hash
from .patches import patch_schema as adult_patch_schema
from .lm_patches import patch_schema as lm_patch_schema

MODELS = {'Astra': 'gpt-6-astra', 'Sol': 'gpt-6.1-sol'}
WARM = ('AS_WARM', 'AA_WARM', 'SS_WARM')
METADATA_BYTES = 32768
PATCH_BYTES = 65536
PROTOCOL = Path(__file__).resolve().parents[2] / 'PROTOCOL.md'
METRICS = {'Adult': ('balanced_accuracy', 'roc_auc', 'accuracy', 'logloss', 'brier'),
           'LM': ('acc_norm', 'acc')}
USAGE = ('input_tokens', 'output_tokens', 'cached_input_tokens', 'reasoning_output_tokens',
         'total_tokens', 'reasoning_tokens', 'cached_tokens')
WORK = ('feedback_examples', 'probe_examples', 'diagnostic_examples', 'target_calls',
        'elapsed_seconds', 'examples', 'requests', 'forwards', 'wall_seconds')
REASONS = ('ValueError', 'ValidationError', 'InvalidPatch', 'InvalidAction', 'InvalidLMPatch',
           'RuntimeError', 'MemoryError', 'InvalidResponse', 'BlockedRoute')


class ExperienceError(ValueError):
    """Source, exposure, schema or context gate refused replay; no retry implied."""


def _require(condition, reason):
    if not condition:
        raise ExperienceError(reason)


def _hash(value):
    _require(type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None,
             'invalid digest')
    return value


def _number(value, signed=False):
    if type(value) not in (int, float):
        return None
    try:
        return value if math.isfinite(value) and (signed or value >= 0) else None
    except OverflowError:
        return None


def _numbers(source, keys):
    source = source if type(source) is dict else {}
    return {k: _number(source.get(k)) for k in keys}


def _object(properties):
    return {'type': 'object', 'additionalProperties': False,
            'properties': properties, 'required': list(properties)}


def _enum(*values):
    return {'enum': list(values)}


HASH = {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}
NUM = {'type': ['number', 'null'], 'minimum': 0}
SIGNED = {'type': ['number', 'null']}
INT = {'type': 'integer', 'minimum': 0}
NULL_HASH = {'anyOf': [HASH, {'type': 'null'}]}
HISTORY_ID = {'type': ['string', 'null'], 'pattern': '^h_[0-9a-f]{64}$'}
TENSOR = {'type': 'string', 'pattern': r'^(fc2\.weight|model\.layers\.[0-9]+\.mlp\.down_proj\.weight)$'}
DESCRIPTOR = _object({'kind': _enum('scale_columns', 'sparse'), 'tensor': TENSOR,
                      'support': INT, 'factor': SIGNED})


def packet_schema(arm):
    """Closed packet schema; every controlled object rejects additional fields."""
    _require(arm in METRICS, 'unknown arm')
    metrics = _object({k: NUM for k in METRICS[arm]})
    attempt = _object({'attempt': INT, 'event': {'type': ['integer', 'null'], 'minimum': 1},
        'status': _enum('VALID', 'INVALID', 'BLOCKED', 'RECORDED'),
        'reason': _enum(None, *REASONS), 'request_hash': NULL_HASH,
        'patch_hash': NULL_HASH, 'history_id': HISTORY_ID,
        'ops': {'type': 'array', 'items': DESCRIPTOR}, 'metrics': metrics,
        'difference': _object({k: SIGNED for k in METRICS[arm]}),
        'stats': _object({k: NUM for k in ('count', 'norm', 'relative_norm', 'fraction')}),
        'relative_norms': {'type': 'array', 'items': _object({'tensor': TENSOR, 'value': NUM})}})
    source = _object({'editor': _enum(*MODELS), 'run_id': HASH, 'selection_hash': HASH,
        'prepared_hash': HASH, 'candidate_file_hash': HASH, 'evaluations': INT,
        'baseline': metrics, 'work': _object({k: NUM for k in WORK}),
        'usage': {'type': 'array', 'items': _object({
            'status': _enum('COMPLETE', 'FAILED', 'INVALID', 'UNKNOWN'),
            'elapsed_seconds': NUM, 'cost': NUM,
            'tokens': _object({k: NUM for k in USAGE})})},
        'attempts': {'type': 'array', 'items': attempt, 'minItems': 1}})
    return _object({'version': {'const': 1}, 'feedback_mode': _enum('DEV_HISTORY', 'FINAL_EXPOSED_EXPLORATORY'),
        'arm': {'const': arm}, 'seed': _enum(101, 202, 303), 'origin_hash': HASH,
        'panel_hash': HASH, 'protocol_hash': HASH, 'source_manifest_hash': HASH,
        'audit_hash': HASH, 'bounds': _object({'metadata_bytes': {'const': METADATA_BYTES},
            'patch_bytes': {'const': PATCH_BYTES}, 'initialization': {'const': 'IMMUTABLE_ORIGIN'}}),
        'sources': {'type': 'array', 'items': source, 'minItems': 2, 'maxItems': 2}})


@dataclass(frozen=True)
class SourceRun:
    """Trusted native source location and exact independent editor identity."""
    run: Path = field(repr=False)
    arm: str
    editor: str


@dataclass(frozen=True)
class _Native:
    identity: bytes
    source: bytes
    bindings: tuple = field(repr=False)
    catalog: tuple = field(repr=False)
    embedded_final_feedback: bool
    run: Path = field(repr=False)
    runtime_inventory: tuple = field(repr=False)


def _patch(patch, arm):
    schema = adult_patch_schema() if arm == 'Adult' else lm_patch_schema()
    try:
        body = canonical(patch)
        _require(len(body) <= PATCH_BYTES, 'patch byte bound')
        StrictValidator(schema).validate(patch)
    except (ValueError, TypeError, OverflowError, ValidationError) as exc:
        raise ExperienceError('invalid history patch') from None
    # Also enforce the existing noncompact action bound before exposing a body.
    _require(len(json.dumps({'action': 'evaluate_candidate', 'patch': patch},
                            allow_nan=False).encode()) <= PATCH_BYTES, 'patch action byte bound')
    return body


def _native(spec):
    _require(spec.arm in METRICS and spec.editor in MODELS, 'unsupported source')
    if (Path(spec.run) / 'fresh-public.json').exists():
        from .execution import native_source
        return native_source(spec)
    run = Path(spec.run)
    bindings = {}
    runtime_inventory = ()

    def bind(path):
        path = Path(path)
        value = file_hash(path)
        if path in bindings:
            _require(bindings[path] == value, 'source changed during read')
        bindings[path] = value
        return value

    def load(name):
        path = run / name
        before = bind(path)
        value = read_json(path)
        _require(bind(path) == before, 'source changed during read')
        return value

    def matches(name, expected):
        _require(bind(run / name) == _hash(expected), 'source hash mismatch')

    try:
        prepared, selection = load('prepared.json'), load('selection.json')
        _require(prepared['phase'] == 'PREPARED' and type(prepared['seed']) is int
                 and prepared['seed'] in (101, 202, 303), 'invalid prepared identity')
        conditions = selection['conditions']
        _require(all(conditions.get(e, {}).get('status') == 'LOCKED' for e in MODELS),
                 'Astra and Sol must both lock')
        chosen = conditions[spec.editor]
        record = load(f'{spec.editor}_candidates.json')
        _require(record.get('status') == 'LOCKED', 'source record not locked')
        driver = record['driver']
        _require(driver['requested_model'] == MODELS[spec.editor]
                 and chosen['driver'] == driver and driver.get('route') == 'native Codex CLI',
                 'source route mismatch')
        resolved = driver.get('resolved_model')
        _require(resolved is None or resolved == MODELS[spec.editor], 'source model substitution')
        protocol_file_hash = bind(PROTOCOL)
        if spec.arm == 'Adult':
            check = dict(selection)
            supplied = check.pop('selection_hash')
            _require(selection['phase'] == 'SELECTION_LOCKED' and digest(check) == _hash(supplied),
                     'invalid Adult selection lock')
            matches('prepared.json', selection['prepared_manifest_sha256'])
            matches('trained.json', selection['trained_manifest_sha256'])
            trained = load('trained.json')
            _require(trained['phase'] == 'TRAINED' and trained['seed'] == prepared['seed'],
                     'trained identity mismatch')
            origin = _hash(selection['origin_hash'])
            _require(origin == trained['damaged_hash'], 'origin mismatch')
            from safetensors.torch import load_file
            damaged = run / 'damaged.safetensors'
            bind(damaged)
            _require(state_hash(load_file(str(damaged))) == origin, 'damaged origin mismatch')
            bind(damaged)
            bind(run / 'mask.safetensors')
            matches('encoder.json', prepared['encoder_sha256'])
            # Final examples and clean/calibration tensors are never opened.
            matches('development.npz', prepared['splits']['development']['file_sha256'])
            for name in ('diagnostic', 'feedback'):
                matches(name + '.npz', selection[name + '_sha256'])
            import numpy as np
            with np.load(run / 'feedback.npz', allow_pickle=False) as panel:
                feedback_ids = panel['ids'].tolist()
            with np.load(run / 'diagnostic.npz', allow_pickle=False) as panel:
                diagnostic_ids = panel['ids'].tolist()
            with np.load(run / 'development.npz', allow_pickle=False) as panel:
                development_ids = panel['ids'].tolist()
            _require(digest(feedback_ids) == selection['panels']['feedback_ids_hash']
                     and digest(development_ids) == prepared['splits']['development']['source_ids_sha256']
                     and set(feedback_ids) <= set(development_ids)
                     and set(diagnostic_ids) <= set(development_ids)
                     and not set(feedback_ids).intersection(diagnostic_ids),
                     'feedback identity mismatch')
            panel_hash = digest({'prepared_development': prepared['splits']['development'],
                                 'feedback_file': selection['feedback_sha256'],
                                 'feedback_ids': selection['panels']['feedback_ids_hash']})
            config = selection['config']
            protocol_hash = digest({'protocol_file': protocol_file_hash, 'config': config})
            matches(f'{spec.editor}_candidates.json', chosen['candidate_record_sha256'])
            controller = record
        else:
            _require(selection['status'] == 'LOCKED', 'invalid LM selection lock')
            matches('search.json', selection['search_hash'])
            search = load('search.json')
            _require(conditions == {'clean': {'status': 'LOCKED', 'patch': {'ops': []}},
                                   **search['conditions']}, 'LM conditions mismatch')
            matches('prepared.json', search['prepared_hash'])
            if prepared['config'].get('exploratory_scope') == 'PUBLICATION_LM_V2_20261104':
                from .publication_run import verified_v2_gate
                matches('exploratory_preflight.json', search['exploratory_preflight_hash'])
                for path, expected in verified_v2_gate(run).items():
                    _require(bind(path) == expected, 'publication v2 source changed')
            elif prepared['config'].get('exploratory_scope') == 'EXPLORATORY_SMALL_SEED101_ONLY':
                from .practical_loop import verified_exploratory_gate
                matches('exploratory_preflight.json', search['exploratory_preflight_hash'])
                for path, expected in verified_exploratory_gate(run).items():
                    _require(bind(path) == expected, 'exploratory source changed')
            else:
                matches('preflight.json', search['preflight_hash'])
                preflight = load('preflight.json')
                matches('parity.json', preflight['parity_hash'])
                parity = load('parity.json')
                _require(preflight['status'] == parity['status'] == 'PASS'
                         and all(parity.get(k, {}).get('status') == 'PASS' for k in ('baseline', 'patched')),
                         'LM preparation gate missing')
                matches('prepared.json', parity['prepared_hash'])
            _require(prepared['model_hashes'] and prepared['source_hashes'], 'missing LM source inventory')
            for value in prepared['model_hashes'].values():
                _hash(value)
            from . import lm_experiment
            _require(lm_experiment.source_hashes() == prepared['source_hashes'],
                     'source inventory mismatch')
            runtime_inventory = tuple(sorted(prepared['source_hashes'].items()))
            for name, value in prepared['source_hashes'].items():
                # Bind contents as well as the complete native inventory. Never rewrite preparation.
                _require(type(name) is str and not Path(name).is_absolute()
                         and '..' not in Path(name).parts, 'invalid source inventory')
                _require(bind(Path(lm_experiment.__file__).parent / name) == _hash(value),
                         'source inventory mismatch')
            origin = digest({'revision': prepared['model_revision'], 'files': prepared['model_hashes']})
            panel_hash = digest({'feedback': prepared['panels']['feedback'],
                                 'fingerprint': prepared['fingerprints']['validation'],
                                 'revision': prepared['data_revisions']['arc_easy']})
            config = prepared['config']
            protocol_hash = digest({'protocol_file': protocol_file_hash, 'config': config,
                                    'runtime': prepared['source_hashes'], 'scorer': prepared['provenance']})
            matches(f'{spec.editor}_candidates.json', chosen['record_hash'])
            controller = record['controller']
        _require(config['candidates_per_search'] in (5, 10), 'invalid source budget')
        _require(controller['candidate_limit'] == config['candidates_per_search'], 'source budget mismatch')
        candidates = controller['candidates']
        _require(candidates and candidates[0]['index'] == 0 and candidates[0]['patch'] == {'ops': []},
                 'missing original baseline')
        _require(controller['locked'] in candidates, 'missing locked candidate')
        primary = METRICS[spec.arm][0]
        for c in candidates:
            _require(type(c['index']) is int and c['index'] >= 0
                     and _number(c['metrics'].get(primary)) is not None
                     and _number(c['stats'].get('norm')) is not None
                     and type(c['stats'].get('count')) is int and c['stats']['count'] >= 0,
                     'invalid candidate selection fields')
        best = min(candidates, key=lambda c: (-c['metrics'][primary], c['stats']['norm'],
                                              c['stats']['count'], c['index']))
        _require(controller['locked'] == best, 'source selection mismatch')
        saved = load(f'patches/{spec.editor}/patch.json')
        selected_patch = best['patch']
        _require(saved['patch'] == selected_patch, 'selected patch mismatch')
        if spec.arm == 'Adult':
            check = dict(saved)
            _require(check.pop('patch_hash') == chosen['patch_hash'] == digest(check), 'saved patch mismatch')
            _require(saved['origin'] == origin, 'saved origin mismatch')
            matches(f'patches/{spec.editor}/patch.safetensors', saved['tensor_sha256'])
        else:
            _require(digest(saved) == chosen['patch_hash'], 'saved patch mismatch')
            matches(f'patches/{spec.editor}/weights.safetensors', saved['weights_sha256'])
        identity = {'arm': spec.arm, 'seed': prepared['seed'], 'origin_hash': origin,
                    'panel_hash': panel_hash, 'protocol_hash': protocol_hash}
        source, catalog = _ledger(spec, controller, record, bindings[run / 'selection.json'],
                                  bindings[run / 'prepared.json'],
                                  bindings[run / f'{spec.editor}_candidates.json'])
        for path, value in bindings.items():
            _require(file_hash(path) == value, 'source mutation')
        if runtime_inventory:
            _require(lm_experiment.source_hashes() == dict(runtime_inventory), 'source inventory mismatch')
        return _Native(canonical(identity), canonical(source), tuple(bindings.items()), tuple(catalog),
                       _has_final_feedback(record), run, runtime_inventory)
    except ExperienceError:
        raise
    except Exception as exc:
        # Raw source strings, JSON schema errors and paths never enter output.
        raise ExperienceError('missing or malformed native source') from None


def _ledger(spec, controller, record, selection_hash, prepared_hash, candidate_hash):
    candidates, events = controller['candidates'], controller['events']
    evaluations = controller['evaluations']
    _require(type(evaluations) is int and 0 <= evaluations <= controller['candidate_limit'],
             'invalid source evaluation count')
    indices = [c['index'] for c in candidates]
    _require(indices == sorted(set(indices)) and max(indices) <= evaluations, 'invalid candidate indices')
    _require(type(events) is list and len(events) >= evaluations, 'missing attempt evidence')
    baseline = _numbers(candidates[0]['metrics'], METRICS[spec.arm])
    catalog, attempts, matched = [], [], set()
    run_id = digest({'selection': selection_hash, 'editor': spec.editor})

    def entry(candidate, event, event_index, attempt):
        patch_hash, history_id, descriptors, ratios = None, None, [], []
        if candidate is not None:
            body = _patch(candidate['patch'], spec.arm)
            patch_hash = digest(candidate['patch'])
            if 'patch_digest' in candidate:
                _require(candidate['patch_digest'] == patch_hash, 'candidate patch digest mismatch')
            history_id = 'h_' + digest([run_id, candidate['index'], patch_hash])
            catalog.append((history_id, patch_hash, body))
            for op in candidate['patch']['ops']:
                descriptors.append({'kind': op['kind'], 'tensor': op['tensor'],
                    'support': len(op.get('columns', op.get('entries', []))),
                    'factor': op.get('factor')})
            for tensor, value in candidate['stats'].get('relative_norms', {}).items():
                if re.fullmatch(r'model\.layers\.[0-9]+\.mlp\.down_proj\.weight', tensor):
                    ratios.append({'tensor': tensor, 'value': _number(value)})
        metrics = _numbers(candidate['metrics'] if candidate else {}, METRICS[spec.arm])
        request_hash = event.get('request_digest', event.get('request_sha256')) if event else None
        if request_hash is not None:
            _hash(request_hash)
        event_status = event.get('status') if event else None
        status = ('VALID' if candidate else 'INVALID' if event_status == 'INVALID'
                  else 'BLOCKED' if event_status == 'BLOCKED' else 'RECORDED')
        attempts.append({'attempt': attempt, 'event': event_index, 'status': status,
            'reason': (event.get('reason', event.get('error_type')) if event and
                       event.get('reason', event.get('error_type')) in REASONS else None),
            'request_hash': request_hash, 'patch_hash': patch_hash, 'history_id': history_id,
            'ops': descriptors, 'metrics': metrics,
            'difference': {k: metrics[k] - baseline[k] if metrics[k] is not None and baseline[k] is not None
                           else None for k in baseline},
            'stats': _numbers(candidate['stats'] if candidate else {}, ('count', 'norm', 'relative_norm', 'fraction')),
            'relative_norms': sorted(ratios, key=lambda x: x['tensor'])})

    entry(candidates[0], None, None, 0)
    evaluation_requests = {digest({'action': 'evaluate_candidate', 'patch': c['patch']})
                           for c in candidates[1:]}
    minimum_evaluations = maximum_evaluations = last_candidate_index = 0
    # Native invalid events often lack an action name/body. Keep every event,
    # including auxiliaries, without pretending its request digest is a patch.
    for i, event in enumerate(events, 1):
        _require(type(event) is dict, 'invalid event')
        request = event.get('request_digest', event.get('request_sha256'))
        known_evaluation = (event.get('action') == 'evaluate_candidate'
                            or request in evaluation_requests)
        if known_evaluation:
            minimum_evaluations += 1
            maximum_evaluations += 1
        elif event.get('status') in ('INVALID', 'BLOCKED') and 'action' not in event:
            # Native failures may omit the action/body. They could be failed
            # evaluations or auxiliaries; never invent which one occurred.
            maximum_evaluations += 1
        candidate = None
        for c in candidates[1:]:
            if (event.get('status') == 'OK' and c['index'] not in matched
                    and request == digest({'action': 'evaluate_candidate', 'patch': c['patch']})):
                _require(last_candidate_index < c['index']
                         and minimum_evaluations <= c['index'] <= maximum_evaluations,
                         'candidate evaluation chronology mismatch')
                candidate = c
                matched.add(c['index'])
                minimum_evaluations = maximum_evaluations = last_candidate_index = c['index']
                break
        _require(not (known_evaluation and event.get('status') == 'OK' and candidate is None),
                 'missing successful candidate')
        entry(candidate, event, i, i)
    _require(len(matched) == len(candidates) - 1, 'missing candidate event evidence')
    _require(minimum_evaluations <= evaluations <= maximum_evaluations,
             'source evaluation chronology mismatch')
    usage = []
    for event in record.get('usage_events', []):
        _require(type(event) is dict, 'invalid usage event')
        usage.append({'status': event.get('status') if event.get('status') in ('COMPLETE', 'FAILED', 'INVALID') else 'UNKNOWN',
            'elapsed_seconds': _number(event.get('elapsed_seconds')), 'cost': _number(event.get('cost')),
            'tokens': _numbers(event.get('usage'), USAGE)})
    return {'editor': spec.editor, 'run_id': run_id, 'selection_hash': selection_hash,
        'prepared_hash': prepared_hash, 'candidate_file_hash': candidate_hash, 'evaluations': evaluations,
        'baseline': baseline, 'work': _numbers(controller.get('target_work'), WORK),
        'usage': usage, 'attempts': attempts}, catalog


def _sources(sources):
    specs = list(sources)
    _require(len(specs) == 2 and {s.editor for s in specs} == set(MODELS), 'exactly Astra and Sol required')
    natives = tuple(_native(s) for s in sorted(specs, key=lambda s: list(MODELS).index(s.editor)))
    _require(natives[0].identity == natives[1].identity, 'cross-source identity mismatch')
    return natives


FINAL_MARKERS = ('finalized.json', 'final_result.json', 'final_failure.json', 'final',
                 'final.json', 'final_scores.json', 'final_metrics.json',
                 'results.json', 'probabilities.json', 'predictions.json', 'assessment-consumed.json')


def _has_final_feedback(value):
    # Native development traces have no final/PIQA feedback capability. Such
    # fields in an existing trace are exposure evidence, even when not exported.
    if type(value) is dict:
        for key, child in value.items():
            name = key.lower()
            if name in ('final', 'piqa', 'test', 'heldout') or name.startswith(
                    ('final_', 'piqa_', 'test_', 'heldout_')):
                return True
            if _has_final_feedback(child):
                return True
    elif type(value) is list:
        return any(_has_final_feedback(child) for child in value)
    return False


def _manifest(natives):
    return [{'editor': json.loads(n.source)['editor'],
             'files': [h for _, h in n.bindings]} for n in natives]


def _observed(natives):
    # Presence only: never deserialize or open final examples or aggregate values.
    return [{'run_id': json.loads(n.source)['run_id'],
             'selection_hash': json.loads(n.source)['selection_hash'],
             'source_manifest_hash': digest(_manifest((n,))),
             'embedded_final_feedback': n.embedded_final_feedback,
             'markers': [name for name in FINAL_MARKERS if (n.run / name).exists()
                 or (name == 'assessment-consumed.json' and (n.run / 'fresh-public.json').exists()
                     and (n.run.parent / name).exists())]}
            for n in natives]


def _audit_schema():
    return _object({'version': {'const': 1}, 'sequence': INT, 'previous_hash': NULL_HASH,
        'identity': _object({'arm': _enum(*METRICS), 'seed': _enum(101, 202, 303),
            'origin_hash': HASH, 'panel_hash': HASH, 'protocol_hash': HASH}),
        'recorded_at': {'type': 'string', 'format': 'date-time'},
        'feedback_mode': _enum('DEV_HISTORY', 'FINAL_EXPOSED_EXPLORATORY', 'UNKNOWN'),
        'sources': {'type': 'array', 'minItems': 2, 'maxItems': 2, 'items': _object({
            'run_id': HASH, 'selection_hash': HASH, 'source_manifest_hash': HASH,
            'embedded_final_feedback': {'type': 'boolean'}, 'markers': {'type': 'array',
                'items': _enum(*FINAL_MARKERS), 'uniqueItems': True}})},
        'attestations': _object({k: {'type': ['boolean', 'null']} for k in
            ('human_exposed', 'agent_exposed', 'final_dependent_advice', 'piqa_exposed')}),
        'pretraining_contamination': {'const': 'UNKNOWN'}})


def _read_audits(directory):
    paths = sorted(Path(directory).glob('*.json'))
    records, previous = [], None
    for i, path in enumerate(paths):
        _require(path.name == f'{i:08d}.json', 'audit history gap')
        value = read_json(path)
        StrictValidator(_audit_schema()).validate(value)
        _require(value['sequence'] == i and value['previous_hash'] == previous, 'audit chain mismatch')
        if records:
            old = records[-1]
            _require([(s['run_id'], s['selection_hash'], s['source_manifest_hash']) for s in old['sources']] ==
                     [(s['run_id'], s['selection_hash'], s['source_manifest_hash']) for s in value['sources']], 'audit sources changed')
            _require(old['identity'] == value['identity'], 'audit identity changed')
            _require(old['feedback_mode'] != 'FINAL_EXPOSED_EXPLORATORY'
                     or value['feedback_mode'] == old['feedback_mode'], 'exposure downgrade')
            for before, after in zip(old['sources'], value['sources']):
                _require(set(before['markers']) <= set(after['markers']), 'final evidence removed')
            for key, exposed in old['attestations'].items():
                _require(exposed is not True or value['attestations'][key] is True, 'exposure attestation removed')
        known_exposure = any(s['markers'] or s['embedded_final_feedback'] for s in value['sources']) or any(
            v is True for v in value['attestations'].values())
        expected_mode = ('FINAL_EXPOSED_EXPLORATORY' if known_exposure or (records and
            records[-1]['feedback_mode'] == 'FINAL_EXPOSED_EXPLORATORY') else
            'DEV_HISTORY' if all(v is False for v in value['attestations'].values()) else 'UNKNOWN')
        _require(value['feedback_mode'] == expected_mode, 'audit mode contradicts evidence')
        records.append(value)
        previous = digest(value)
    return records


def audit_exposure(sources, directory, *, human_exposed, agent_exposed,
                   final_dependent_advice, piqa_exposed):
    """Append an exclusive, chained audit; never overwrite or reset native markers.

    All four attestations must be explicitly false for DEV_HISTORY. Unknown
    attestations produce UNKNOWN, which cannot build a packet. Observed final
    artifacts or any true attestation irreversibly produce exploratory status.
    Retain this trusted audit directory; no local file API can prevent an owner
    deleting the entire directory externally.
    """
    natives = _sources(sources)
    observed = _observed(natives)
    attestations = dict(human_exposed=human_exposed, agent_exposed=agent_exposed,
                        final_dependent_advice=final_dependent_advice, piqa_exposed=piqa_exposed)
    _require(all(type(v) is bool or v is None for v in attestations.values()), 'invalid exposure attestation')
    records = _read_audits(directory)
    if records:
        old = records[-1]
        _require([(s['run_id'], s['selection_hash'], s['source_manifest_hash']) for s in old['sources']] ==
                 [(s['run_id'], s['selection_hash'], s['source_manifest_hash']) for s in observed], 'audit source mismatch')
        for before, now in zip(old['sources'], observed):
            _require(set(before['markers']) <= set(now['markers']), 'final evidence removed')
        for key, value in old['attestations'].items():
            if value is True:
                attestations[key] = True
    exposed = (any(s['markers'] or s['embedded_final_feedback'] for s in observed) or any(v is True for v in attestations.values())
               or bool(records and records[-1]['feedback_mode'] == 'FINAL_EXPOSED_EXPLORATORY'))
    mode = ('FINAL_EXPOSED_EXPLORATORY' if exposed else
            'DEV_HISTORY' if all(v is False for v in attestations.values()) else 'UNKNOWN')
    value = {'version': 1, 'sequence': len(records), 'previous_hash': digest(records[-1]) if records else None,
             'identity': json.loads(natives[0].identity),
             'recorded_at': datetime.now(timezone.utc).isoformat(), 'feedback_mode': mode,
             'sources': observed, 'attestations': attestations, 'pretraining_contamination': 'UNKNOWN'}
    StrictValidator(_audit_schema()).validate(value)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / f'{len(records):08d}.json').open('xb') as stream:
        stream.write(canonical(value) + b'\n')
    return value


@dataclass(frozen=True)
class Experience:
    """Immutable bytes/catalog with source and exposure revalidation on access."""
    sha256: str
    source_manifest_sha256: str
    _metadata: bytes = field(repr=False)
    _source_manifest: bytes = field(repr=False)
    _catalog: tuple = field(repr=False)
    _bindings: tuple = field(repr=False)
    _natives: tuple = field(repr=False)
    _audit_directory: Path = field(repr=False)
    _audit_hash: str = field(repr=False)

    def _check(self, condition):
        _require(condition in WARM, 'history denied to cold or unknown condition')
        for native in self._natives:
            if native.runtime_inventory:
                from .execution import source_hashes
                _require(source_hashes() == dict(native.runtime_inventory), 'source inventory mismatch')
        for path, expected in self._bindings:
            _require(path.exists() and file_hash(path) == expected, 'source mutation')
        audits = _read_audits(self._audit_directory)
        _require(audits and digest(audits[-1]) == self._audit_hash, 'exposure audit changed')
        _require(_observed(self._natives) == audits[-1]['sources'], 'final exposure changed; audit again')
        _require(hashlib.sha256(self._metadata).hexdigest() == self.sha256, 'packet digest mismatch')

    def packet(self, condition):
        """Return identical canonical metadata for each warm role; deny cold."""
        self._check(condition)
        return self._metadata

    def source_manifest(self, condition):
        """Return the bounded, path-free source hash inventory for warm runs."""
        self._check(condition)
        _require(hashlib.sha256(self._source_manifest).hexdigest() == self.source_manifest_sha256,
                 'source manifest digest mismatch')
        return self._source_manifest

    def read_history_patch(self, condition, history_id):
        """Return fresh original JSON after warm/source/digest/schema/bound gates.

        No path is accepted or returned. Caller charges one auxiliary attempt even
        when this method raises. No model initialization or evaluation occurs.
        """
        self._check(condition)
        _require(type(history_id) is str and re.fullmatch('h_[0-9a-f]{64}', history_id) is not None,
                 'invalid history ID')
        for opaque_id, patch_hash, body in self._catalog:
            if opaque_id == history_id:
                patch = json.loads(body)
                arm = json.loads(self._metadata)['arm']
                _require(_patch(patch, arm) == body and digest(patch) == patch_hash, 'catalog digest mismatch')
                return patch
        raise ExperienceError('unknown history ID')


def build_experience(sources, audit_directory):
    """Build bounded E0 from actual native locks; never attach final aggregates.

    An exploratory packet carries the exposure label only. Final attachments are
    deliberately unsupported at this stage. Caller persists returned bytes and
    hashes before any future search; original source files remain untouched.
    """
    natives = _sources(sources)
    audits = _read_audits(audit_directory)
    _require(audits and audits[-1]['sources'] == _observed(natives)
             and audits[-1]['identity'] == json.loads(natives[0].identity),
             'missing or stale exposure audit')
    audit = audits[-1]
    _require(audit['feedback_mode'] != 'UNKNOWN', 'unknown exposure blocks replay')
    source_records = [json.loads(n.source) for n in natives]
    bindings = tuple(sorted({p: h for n in natives for p, h in n.bindings}.items(), key=lambda x: str(x[0])))
    # Hash the complete native chain without exposing any filenames to editors.
    manifest = _manifest(natives)
    manifest_hash = digest(manifest)
    packet = {'version': 1, 'feedback_mode': audit['feedback_mode'], **json.loads(natives[0].identity),
        'source_manifest_hash': manifest_hash, 'audit_hash': digest(audit),
        'bounds': {'metadata_bytes': METADATA_BYTES, 'patch_bytes': PATCH_BYTES,
                   'initialization': 'IMMUTABLE_ORIGIN'}, 'sources': source_records}
    StrictValidator(packet_schema(packet['arm'])).validate(packet)
    body = canonical(packet)
    _require(len(body) <= METADATA_BYTES, 'context budget: metadata overflow; no truncation')
    return Experience(hashlib.sha256(body).hexdigest(), manifest_hash, body, canonical(manifest),
                      tuple(item for n in natives for item in n.catalog), bindings, natives,
                      Path(audit_directory), digest(audit))
