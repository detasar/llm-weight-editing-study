"""Bounded Stage2 software API; no science CLI, group release or final access.

Prepare a fresh Controller (or LMController with turn_limit=30), its original
editor view, and two fresh restricted drivers. Persist Stage1 packet/manifest
bytes and hashes before constructing a warm Scheduler. Supply the prepared task
identity (arm, seed, origin_hash, panel_hash, protocol_hash); warm identity must
match E0. Only Experience's public, revalidating accessors are used.

Adult callers must also pass trusted_encoder from the original fit encoder and
the original view's feature_metadata output. Native orchestration must verify
encoder.json against prepared.json's encoder_sha256 before supplying it; this
in-memory component validates the mapping, not native file authenticity. Neither
this API nor its fixture tests authorize scientific execution.

Scheduler.run() is single-use and returns immutable serialized development
records and stage snapshots. The caller owns persistence and later orchestration.
The scheduler is implemented and software tested with offline fixtures. The full
extension is not yet implemented or scientifically run. Fixture tests are software
evidence only. No finalizer or reporting gate is bypassed here.
"""
import copy
from dataclasses import dataclass
import hashlib
from importlib.resources import files
import json
import math
import re
import time

from .controller import Controller, StrictValidator, action_schema as adult_actions
from .driver import MODELS, BlockedRoute, BudgetExhausted, InvalidResponse, bounded_payload
from .experience import ExperienceError, METRICS, USAGE, WORK, packet_schema
from .io import canonical, digest
from .lm_controller import LMController
from .lm_patches import action_schema as lm_actions, patch_schema as lm_patch
from .patches import patch_schema as adult_patch

CONDITIONS = ('AS_COLD', 'AS_WARM', 'AA_WARM', 'SS_WARM')
ACTORS = {'AS_COLD': ('Astra', 'Sol'), 'AS_WARM': ('Astra', 'Sol'),
          'AA_WARM': ('Astra', 'Astra'), 'SS_WARM': ('Sol', 'Sol')}
SEEDS = (101, 202, 303)
INSTRUCTIONS = files('ws_lab').joinpath('resources/cowork_editor.txt').read_text()
AUXILIARY = ('inspect_stats', 'inspect_slice', 'probe_summary', 'read_history_patch')


class CoworkError(ValueError):
    """Missing context or invalid prepared state; never a request to repair sources."""


def require(ok, reason):
    if not ok:
        raise CoworkError(reason)


def condition_order(seed):
    require(type(seed) is int and seed in SEEDS, 'unknown seed')
    i = SEEDS.index(seed)
    return CONDITIONS[i:] + CONDITIONS[:i]


def obj(properties):
    return {'type': 'object', 'additionalProperties': False,
            'properties': properties, 'required': list(properties)}


def variant(action, fields=None):
    return obj({'action': {'const': action}, **(fields or {})})


def response_schema(arm, role, *, warm=False, auxiliary=True, probe=True):
    """Strict role-specific scientific schema; canaries use canary_schema only."""
    require(arm in METRICS and role in ('proposer', 'reviewer'), 'unknown role or arm')
    patch = adult_patch() if arm == 'Adult' else lm_patch()
    short = {'type': 'string', 'minLength': 1, 'maxLength': 512}
    if role == 'proposer':
        branches = [variant('propose', {'patch': patch, 'hypothesis': short,
            'expected_observable': short, 'risk': short, 'evidence_ids': {
                'type': 'array', 'maxItems': 16, 'uniqueItems': True,
                'items': {'type': 'string', 'pattern': r'^(baseline|round:[1-9][0-9]*|h_[0-9a-f]{64})$'}}})]
    else:
        branches = [variant('accept', {'rationale': short}),
                    variant('revise', {'patch': patch, 'rationale': short}),
                    variant('reject', {'rationale': short})]
    if auxiliary:
        base = adult_actions() if arm == 'Adult' else lm_actions()
        branches += [b for b in base['oneOf'] if
                     b['properties']['action']['const'] in ('inspect_stats', 'inspect_slice')
                     or (probe and b['properties']['action']['const'] == 'probe_summary')]
        if warm:
            branches.append(variant('read_history_patch', {'history_id': {
                'type': 'string', 'pattern': '^h_[0-9a-f]{64}$'}}))
    return {'oneOf': branches}


def canary_schema():
    return variant('inspect_stats')


def number(value):
    try:
        return value if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None
    except OverflowError:
        return None


def numbers(value, keys):
    value = value if type(value) is dict else {}
    return {k: number(value.get(k)) for k in keys}


def stats(value):
    result = numbers(value, ('count', 'norm', 'relative_norm', 'fraction', 'unique_parameters'))
    result['relative_norms'] = {k: number(v) for k, v in value.get('relative_norms', {}).items()
                              if re.fullmatch(r'model\.layers\.[0-9]+\.mlp\.down_proj\.weight', k)}
    result['applied_hashes'] = {k: v for k, v in value.get('applied_hashes', {}).items()
                              if re.fullmatch(r'model\.layers\.[0-9]+\.mlp\.down_proj\.weight', k)
                              and type(v) is str and re.fullmatch('[0-9a-f]{64}', v)}
    return result


def candidate(item, arm):
    return {'index': item['index'], 'patch_hash': digest(item['patch']),
            'stats': stats(item['stats']), 'metrics': numbers(item['metrics'], METRICS[arm])}


def actor_record(index, editor, driver):
    meta = driver.metadata
    version = meta.get('cli_version')
    return {'actor': index, 'requested_model': MODELS[editor],
        'resolved_model': meta.get('resolved_model') if meta.get('resolved_model') == MODELS[editor] else None,
        'reasoning': meta.get('reasoning') if meta.get('reasoning') in ('medium', None) else 'UNKNOWN',
        'route': 'native Codex CLI',
        'cli_version': version if type(version) is str and re.fullmatch(r'[A-Za-z0-9 ._+\-]{1,200}', version) else None,
        **{k: meta.get(k) if type(meta.get(k)) is str and re.fullmatch('[0-9a-f]{64}', meta[k]) else None
           for k in ('catalog_sha256', 'config_sha256')}}


def prediction(row):
    """Train diagnostic fields only; no arbitrary nested provider/document payload."""
    require(row.get('task') == 'arc_easy' and row.get('split') == 'train', 'non-diagnostic row')
    keys = ('source_id', 'source_index', 'split', 'task', 'choice_count', 'choice_char_lengths',
            'continuation_token_lengths', 'loglikelihoods', 'greedy', 'preferred', 'preferred_norm',
            'gold', 'acc', 'acc_norm')
    result = {k: copy.deepcopy(row[k]) for k in keys if k in row}
    properties = {
        **{k: {'type': 'string'} for k in ('source_id', 'split', 'task')},
        **{k: {'type': 'integer', 'minimum': 0} for k in
           ('source_index', 'choice_count', 'preferred', 'preferred_norm')},
        **{k: {'type': 'array', 'items': {'type': 'integer', 'minimum': 1}}
           for k in ('choice_char_lengths', 'continuation_token_lengths')},
        'loglikelihoods': {'type': 'array', 'items': {'type': 'number'}},
        'greedy': {'type': 'array', 'items': {'type': 'boolean'}},
        'gold': {'type': ['string', 'integer']},
        'acc': {'type': 'number'}, 'acc_norm': {'type': 'number'}}
    StrictValidator({'type': 'object', 'additionalProperties': False,
                     'properties': properties}).validate(result)
    return result


def adult_features(encoder, supplied, width):
    """Validate the trusted fit-encoder shape before reusing original descriptions."""
    from .data import NUMERIC, CATEGORICAL
    from .experiment import feature_metadata
    require(type(encoder) is dict, 'trusted fit encoder required')
    require(type(width) is int and 1 <= width <= 2048, 'feature width bound')
    for key, expected in (('numeric', NUMERIC), ('categorical', CATEGORICAL)):
        value = encoder.get(key)
        require(type(value) is list and all(type(i) is int for i in value)
                and value == expected, 'original encoder column order required')
    require(encoder.get('excluded') == ['sex', 'race']
            and encoder.get('unknown_category') == 'all_zero', 'original feature exclusions required')
    for key in ('mean', 'std'):
        values = encoder.get(key)
        require(type(values) is list and len(values) == len(NUMERIC)
                and all(type(v) in (int, float) and number(abs(v)) is not None
                        and (key != 'std' or v > 0) for v in values), 'invalid encoder normalization')
    categories = encoder.get('categories')
    require(type(categories) is dict and set(categories) == {str(i) for i in CATEGORICAL},
            'original categorical columns required')
    for values in categories.values():
        require(type(values) is list and 1 <= len(values) <= 2048
                and all(type(v) is str and 1 <= len(v) <= 80
                        and v.isprintable() and '/' not in v and '\\' not in v for v in values),
                'invalid encoder categories')
        require(values == sorted(set(values)) and '__MISSING__' in values,
                'original fit category order required')
    require(len(NUMERIC) + sum(map(len, categories.values())) == width,
            'encoder feature width mismatch')
    features = feature_metadata(encoder)
    require(type(supplied) is list and supplied == features, 'original feature mapping mismatch')
    return features


def lm_architecture(model, supplied):
    """Pinned Llama task facts only; no config serialization or nested passthrough."""
    from transformers import LlamaConfig, LlamaForCausalLM
    require(isinstance(model, LlamaForCausalLM) and isinstance(model.config, LlamaConfig),
            'trusted Llama target required')
    require(type(supplied) is dict, 'original architecture view required')
    config = model.config
    result = {'model_type': 'llama', 'architectures': ['LlamaForCausalLM']}
    require(config.model_type == 'llama' and config.architectures in (None, result['architectures']),
            'model family mismatch')
    bounds = {'vocab_size': 1000000, 'hidden_size': 65536, 'intermediate_size': 262144,
              'num_hidden_layers': 1024, 'num_attention_heads': 1024,
              'num_key_value_heads': 1024, 'head_dim': 65536,
              'max_position_embeddings': 10000000, 'pretraining_tp': 1024}
    for key, maximum in bounds.items():
        value = getattr(config, key, None)
        require(type(value) is int and 1 <= value <= maximum, 'invalid architecture dimension')
        result[key] = value
    require(result['hidden_size'] == result['num_attention_heads'] * result['head_dim']
            and result['num_attention_heads'] % result['num_key_value_heads'] == 0,
            'inconsistent attention dimensions')
    require(config.hidden_act in ('silu', 'gelu', 'relu'), 'unsupported activation')
    result['hidden_act'] = config.hidden_act
    for key in ('attention_bias', 'mlp_bias', 'tie_word_embeddings', 'use_cache'):
        value = getattr(config, key, None)
        require(type(value) is bool, 'invalid architecture boolean')
        result[key] = value
    for key in ('rms_norm_eps', 'initializer_range', 'attention_dropout'):
        value = getattr(config, key, None)
        require(type(value) in (int, float) and 0 <= value <= 1
                and math.isfinite(value) and (key != 'rms_norm_eps' or value > 0),
                'invalid architecture scalar')
        result[key] = value
    for key in ('bos_token_id', 'eos_token_id'):
        value = getattr(config, key, None)
        require(type(value) is int and 0 <= value < result['vocab_size'], 'invalid special token')
        result[key] = value
    # The installed config normalizes the public checkpoint's rope_theta and
    # rope_scaling=None into rope_parameters. Only unscaled RoPE is in scope.
    rope = config.rope_parameters
    require(type(rope) is dict and rope.get('rope_type') == 'default', 'unsupported RoPE')
    theta = rope.get('rope_theta')
    require(type(theta) in (int, float) and 0 < theta <= 1e9 and math.isfinite(theta),
            'invalid RoPE theta')
    partial = rope.get('partial_rotary_factor', 1.0)
    require(type(partial) in (int, float) and partial == 1 and math.isfinite(partial),
            'unsupported partial RoPE')
    result.update(rope_theta=theta, rope_scaling=None)
    for key, value in result.items():
        if key in supplied and not (key == 'architectures' and supplied[key] is None):
            require(type(supplied[key]) is type(value) and supplied[key] == value
                    or type(value) in (int, float) and type(supplied[key]) in (int, float)
                    and supplied[key] == value, 'original architecture mismatch')
    if 'rope_parameters' in supplied:
        original = supplied['rope_parameters']
        require(type(original) is dict and original.get('rope_type') == 'default'
                and type(original.get('rope_theta')) in (int, float)
                and original['rope_theta'] == theta, 'original RoPE mismatch')
    for original in (supplied, supplied.get('rope_parameters', {})):
        if 'partial_rotary_factor' in original:
            value = original['partial_rotary_factor']
            require(type(value) in (int, float) and value == partial and math.isfinite(value),
                    'original partial RoPE mismatch')
    require(config._attn_implementation == 'eager', 'original eager attention required')
    return result


class TaskAdapter:
    """Trusted existing controller actions with explicit outbound allowlists."""
    def __init__(self, controller, view, *, trusted_encoder=None, compact_context=False):
        require(isinstance(controller, (Controller, LMController)), 'unsupported controller')
        self.controller = controller
        self.compact_context = compact_context
        self.arm = 'LM' if isinstance(controller, LMController) else 'Adult'
        require(controller.locked is None and controller.evaluations == controller.turns == 0
                and controller.shared.turns == 0 and not controller.shared.events
                and not controller.events and len(controller.candidates) == 1,
                'fresh unconsumed controller required')
        baseline = controller.candidates[0]
        require(baseline['index'] == 0 and baseline['patch'] == {'ops': []}
                and baseline['stats']['count'] == baseline['stats']['norm'] == 0,
                'original no-op baseline required')
        require(number(baseline['metrics'].get(METRICS[self.arm][0])) is not None,
                'missing development baseline')
        require(controller.shared.limit == 30, 'team broker budget must be 30')
        if self.arm == 'LM':
            require(controller.turn_limit == 30 and controller.current == {'ops': []}
                    and not controller.space.touched, 'fresh team LM broker required')
            require(set(controller.panels['extra_probes']) <= set(controller.panels['diagnostic'])
                    and len(controller.panels['extra_probes']) <= 32,
                    'probes must use original diagnostic examples')
        self.view = self._view(view, trusted_encoder)

    def _stats(self):
        raw = self.controller.space.stats()
        if self.arm == 'Adult':
            return {k: copy.deepcopy(raw[k]) for k in ('tensor', 'shape', 'norm', 'eligible_scalars',
                    'max_changed', 'relative_limit', 'families')}
        return {**numbers(raw, ('unique_parameters', 'max_changed_scalars')),
                'operations': ['scale_columns', 'sparse'], 'tensors': {
                    k: {p: copy.deepcopy(v[p]) for p in ('shape', 'dtype', 'norm')}
                    for k, v in raw['tensors'].items()
                    if re.fullmatch(r'model\.layers\.[0-9]+\.mlp\.down_proj\.weight', k)}}

    def _view(self, view, trusted_encoder):
        result = {'stats': self._stats(), 'baseline': candidate(self.controller.candidates[0], self.arm),
                  'candidate_limit': self.controller.limit,
                  'selection': f'{METRICS[self.arm][0]} desc, norm/count/index asc'}
        if self.arm == 'Adult':
            width = self.controller.diagnostic['x'].shape[1]
            require(self.controller.space.origin()['fc1.weight'].shape[1] == width,
                    'model feature width mismatch')
            result['features'] = adult_features(trusted_encoder, view.get('features'), width)
            # Reuse the controller's own cached original diagnostic, not arbitrary caller additions.
            original = self.controller.initial_view()['diagnostic']
            require(view.get('diagnostic') == original, 'original diagnostic view required')
            result['diagnostic'] = {k: copy.deepcopy(original[k]) for k in (
                'source_ids', 'features', 'labels', 'damaged_probabilities', 'activation_mean', 'activation_std')}
        else:
            result['architecture'] = lm_architecture(self.controller.space.model, view.get('architecture'))
            # CanonicalScorer fixes these settings independently of config dtype metadata.
            result['inference'] = {'dtype': 'float16', 'attention': 'eager',
                'batch_size': 1, 'softmax_dtype': 'float32', 'logits_cache': False,
                'task': 'arc_easy', 'num_fewshot': 0, 'chat_template': False}
            if self.compact_context:
                identity = self.controller.scorer.runtime['inference_identity']
                result['inference'].update(dtype=identity['dtype'], device=identity['device'])
            rows = view['diagnostic']
            require(len(rows) == len(self.controller.panels['diagnostic']) <= 128,
                    'original diagnostic view required')
            diagnostics = []
            for index, row in zip(self.controller.panels['diagnostic'], rows, strict=True):
                require(row['prediction']['source_index'] == index, 'diagnostic identity mismatch')
                doc = row['document']
                require(doc == self.controller.task.dataset['train'][index],
                        'diagnostic document differs from original task')
                choices = doc['choices']
                document = {k: copy.deepcopy(doc[k]) for k in ('id', 'question', 'answerKey') if k in doc}
                document['choices'] = {k: copy.deepcopy(choices[k]) for k in ('text', 'label')}
                StrictValidator({'type': 'object', 'additionalProperties': False,
                    'properties': {**{k: {'type': 'string'} for k in ('id', 'question', 'answerKey')},
                        'choices': obj({k: {'type': 'array', 'items': {'type': 'string'}}
                                        for k in ('text', 'label')})},
                    'required': ['question', 'choices', 'answerKey']}).validate(document)
                diagnostics.append({'document': document,
                    'prediction': prediction(row['prediction'])})
            result['diagnostic'] = diagnostics
        bounded_payload(result)
        return result

    def auxiliary(self, action):
        kind = action['action']
        result = self.controller.handle(action)
        if result.get('status') is not None:
            require(result['status'] == 'INVALID', 'unknown controller status')
            return {'status': 'INVALID'}
        if kind == 'inspect_stats':
            return self._stats()
        if kind == 'inspect_slice':
            return {'values': result['values']}
        if self.arm == 'Adult':
            return {'kind': 'CACHED_DAMAGED_DIAGNOSTIC', 'new_target_forward': False,
                    'patch_hash': digest({'ops': []}), 'n': result['n'],
                    'mean_probability': result['mean_probability'],
                    'metrics': numbers(result['metrics'], METRICS['Adult'])}
        from .lm_scoring import aggregate
        # Public feedback is aggregate only, even for approved train probes.
        return {'kind': 'LATEST_VALID_PATCH_TRAIN_PROBE',
                'patch_hash': digest(self.controller.current), 'n': len(result['predictions']),
                'metrics': numbers(aggregate(result['predictions']), METRICS['LM'])}

    def evaluate(self, patch):
        result = self.controller.handle({'action': 'evaluate_candidate', 'patch': patch})
        if 'status' in result:
            require(result['status'] == 'INVALID', 'unknown controller status')
            return {'status': 'INVALID'}
        return {'status': 'VALID', **candidate(self.controller.candidates[-1], self.arm)}

    def snapshot(self, slot):
        best = self.controller.best()
        return Snapshot(slot, canonical({**candidate(best, self.arm), 'patch': best['patch']}))

    def rollback(self):
        self.controller.space.rollback()


@dataclass(frozen=True)
class Snapshot:
    slot: int
    data: bytes


@dataclass(frozen=True)
class RunResult:
    record: bytes
    snapshots: tuple[Snapshot, ...]


class Scheduler:
    """Single condition, fresh actors, origin baseline; no cross-condition state.

    ``identity`` is trusted prepared task provenance, never source run bindings.
    AS_COLD requires experience=None and receives no source history or identifiers.
    Warm callers must persist Experience.packet/source_manifest before run(); this
    class rechecks the public accessors at construction and every warm use.
    """
    def __init__(self, controller, view, drivers, *, condition, identity,
                 feedback_mode, repeat_index=0, experience=None, trusted_encoder=None,
                 context_policy=None):
        require(context_policy in (None, 'EXPLORATORY_SMALL_SEED101_ONLY', 'FRESH_PUBLIC_LM_V1'), 'unknown context policy')
        require(context_policy != 'EXPLORATORY_SMALL_SEED101_ONLY' or identity['seed'] == 101, 'compact scope seed')
        self.compact_context = context_policy is not None
        self.context_policy = context_policy
        self.instructions = INSTRUCTIONS
        require(condition in CONDITIONS, 'unknown condition')
        require(feedback_mode in ('DEV_HISTORY', 'FINAL_EXPOSED_EXPLORATORY'), 'unknown feedback mode')
        require(type(repeat_index) is int and repeat_index >= 0, 'invalid repeat')
        require(set(identity) == {'arm', 'seed', 'origin_hash', 'panel_hash', 'protocol_hash'},
                'prepared task identity required')
        require(type(identity['seed']) is int and identity['seed'] in SEEDS, 'unknown seed')
        require(all(type(identity[k]) is str and re.fullmatch('[0-9a-f]{64}', identity[k])
                    for k in ('origin_hash', 'panel_hash', 'protocol_hash')), 'invalid provenance')
        require((condition == 'AS_COLD') == (experience is None), 'cold/history boundary')
        require(len(drivers) == 2 and drivers[0] is not drivers[1], 'two distinct actors required')
        self.drivers = tuple(drivers)
        for driver, editor in zip(drivers, ACTORS[condition], strict=True):
            require(driver.editor == editor and driver.calls == 0 and not driver.preflight_done
                    and not driver.events, 'fresh actor required')
            self._route(driver, editor, fresh=True)
        self.adapter = TaskAdapter(controller, view, trusted_encoder=trusted_encoder,
                                   compact_context=self.compact_context)
        require(identity['arm'] == self.adapter.arm, 'arm mismatch')
        if self.adapter.arm == 'Adult':
            require(identity['origin_hash'] == controller.space.origin_hash, 'origin mismatch')
        self.identity = copy.deepcopy(identity)
        self.feedback_mode = feedback_mode
        self.condition, self.repeat_index, self.experience = condition, repeat_index, experience
        self.limit = controller.limit
        self.per_actor = self.limit + 5
        self.first = (SEEDS.index(identity['seed']) + repeat_index) % 2
        self.stages = (0, 2, 5) if self.limit == 5 else (0, 5, 10)
        self.packet_hash = self.manifest_hash = None
        self._history()
        self.used = False
        self.transcripts = [[], []]
        self.ledger, self.calls, self.snapshots = [], [], []
        self.counts = [dict(total=0, canary=0, auxiliary=0, probes=0, substantive=0) for _ in drivers]
        self.session_owners = {}
        self.completed = self.slots = 0

    @staticmethod
    def _route(driver, editor, fresh=False):
        meta = driver.metadata
        require(meta.get('requested_model') == MODELS[editor]
                and meta.get('resolved_model') in (None, MODELS[editor])
                and meta.get('route') == 'native Codex CLI'
                and meta.get('timeout_seconds') == 120 and meta.get('max_wall_seconds') == 900
                and meta.get('max_turns') == 15
                and meta.get('status') in (('NOT_RUN',) if fresh else ('READY',)),
                'invalid actor route or status')

    def _history(self):
        if self.experience is None:
            return None
        body = self.experience.packet(self.condition)
        manifest = self.experience.source_manifest(self.condition)
        require(type(body) is bytes and type(manifest) is bytes, 'immutable history required')
        packet = json.loads(body)
        StrictValidator(packet_schema(self.identity['arm'])).validate(packet)
        require(all(packet[k] == v for k, v in self.identity.items()), 'history/task mismatch')
        require(packet['feedback_mode'] == self.feedback_mode, 'feedback mode mismatch')
        packet_hash = hashlib.sha256(body).hexdigest()
        manifest_hash = hashlib.sha256(manifest).hexdigest()
        require(packet_hash == self.experience.sha256 and manifest_hash == self.experience.source_manifest_sha256
                and packet['source_manifest_hash'] == manifest_hash, 'history digest mismatch')
        require(self.packet_hash in (None, packet_hash) and self.manifest_hash in (None, manifest_hash),
                'history changed')
        self.packet_hash, self.manifest_hash = packet_hash, manifest_hash
        return body.decode('utf-8')

    def _account(self, event, result):
        event.update(returned=True, submitted=True, status='RETURNED')
        event['usage'] = numbers(result.get('usage'), USAGE) if type(result.get('usage')) is dict else None
        event['cost'] = number(result.get('cost'))

    def _call(self, actor, role, proposal=None, canary=False):
        driver = self.drivers[actor]
        count = self.counts[actor]
        count['total'] += 1
        if canary:
            count['canary'] += 1
        event = {'actor': actor, 'role': 'canary' if canary else role, 'attempted': True,
                 'submitted': False, 'returned': False, 'usage': None, 'cost': None,
                 'status': 'LOCAL_REFUSED', 'context_bytes': None, 'elapsed_seconds': None}
        self.calls.append(event)
        before = len(driver.events)
        started = time.monotonic()
        try:
            if count['total'] > self.per_actor or len(self.calls) > 2 * self.per_actor:
                raise BudgetExhausted('team call budget')
            schema = canary_schema() if canary else response_schema(
                self.adapter.arm, role, warm=self.experience is not None,
                auxiliary=count['auxiliary'] < 4, probe=count['probes'] < 2)
            driver.schema, driver.instructions = schema, self.instructions
            if not canary:
                history = self._history()
                context = {'role': role, 'actor': actor, 'round': self.slots,
                    'initial_view': self.adapter.view, 'ledger': self.ledger,
                    'incumbent': candidate(self.adapter.controller.best(), self.adapter.arm),
                    'proposal': proposal, 'response_schema': schema,
                    'remaining_auxiliary': max(0, 4-count['auxiliary']),
                    'remaining_probes': max(0, 2-count['probes'])}
                if history is not None:
                    context['experience_packet_utf8'] = history
                if self.compact_context:
                    context['ledger'] = self.ledger[-1:]
                    context['current_patch'] = copy.deepcopy(self.adapter.controller.best()['patch'])
                    if self.transcripts[actor]:
                        context.pop('initial_view')
                        context.pop('experience_packet_utf8', None)
                    else:
                        context['initial_view'] = {k: v for k, v in self.adapter.view.items()
                                                   if k != 'diagnostic'}
                        diagnostic = self.adapter.view['diagnostic']
                        if self.adapter.arm == 'Adult':
                            context['initial_view']['diagnostic_summary'] = {
                                'n': len(diagnostic['labels']),
                                'activation_mean': diagnostic['activation_mean'],
                                'activation_std': diagnostic['activation_std'],
                                'mean_damaged_probability': sum(diagnostic['damaged_probabilities']) /
                                    len(diagnostic['damaged_probabilities'])}
                        else:
                            from .lm_scoring import aggregate
                            context['initial_view']['diagnostic_summary'] = {
                                'n': len(diagnostic),
                                'metrics': aggregate([row['prediction'] for row in diagnostic])}
                self.transcripts[actor].append({'role': 'user', 'content': copy.deepcopy(context)})
                event['context_bytes'] = len(bounded_payload(self.transcripts[actor]).encode())
            self._route(driver, ACTORS[self.condition][actor], fresh=canary)
            # Existing transports cannot always prove submission or returned inference
            # after failure. Null preserves that uncertainty instead of inventing zeros.
            event['submitted'] = event['returned'] = None
            result = driver.preflight() if canary else driver.turn(copy.deepcopy(self.transcripts[actor]))
            require(type(result) is dict, 'invalid driver response')
            self._account(event, result)
            require(result.get('status') == 'COMPLETE', 'unknown inference status')
            self._route(driver, ACTORS[self.condition][actor])
            session = result.get('session_id')
            require(type(session) is str and bool(session), 'missing actor session evidence')
            session_hash = digest(session)
            require(self.session_owners.get(session_hash, actor) == actor, 'shared actor session')
            self.session_owners[session_hash] = actor
            event['session_hash'] = session_hash
            action = result.get('action')
            kind = action.get('action') if type(action) is dict else None
            if not canary:
                if kind in AUXILIARY:
                    count['auxiliary'] += 1
                    if kind == 'probe_summary':
                        count['probes'] += 1
                    event['kind'] = kind
                else:
                    count['substantive'] += 1
            require(len(json.dumps(action, allow_nan=False).encode()) <= 65536, 'action byte budget')
            StrictValidator(schema).validate(action)
            event['response_hash'] = digest(action)
            event['response'] = copy.deepcopy(action)
            if not canary:
                self.transcripts[actor].append({'role': 'assistant', 'content': copy.deepcopy(action)})
            event['status'] = 'COMPLETE'
            return action
        except Exception:
            # Preserve available failed-transport numeric usage, never raw output or exceptions.
            if not event['returned'] and len(driver.events) > before:
                last = driver.events[-1]
                event['usage'] = numbers(last.get('usage'), USAGE) if type(last.get('usage')) is dict else None
                event['cost'] = number(last.get('cost'))
            if event['status'] != 'LOCAL_REFUSED' or event['submitted'] is not False:
                event['status'] = 'FAILED'
            raise
        finally:
            event['elapsed_seconds'] = time.monotonic() - started

    def _response(self, actor, role, proposal=None):
        while True:
            action = self._call(actor, role, proposal)
            if action['action'] not in AUXILIARY:
                return action
            if action['action'] == 'read_history_patch':
                # Access always revalidates E0 and the catalog. Failure is charged and blocks.
                self._history()
                patch = self.experience.read_history_patch(self.condition, action['history_id'])
                require(len(json.dumps(patch, allow_nan=False).encode()) <= 65536, 'history patch bound')
                StrictValidator(adult_patch() if self.adapter.arm == 'Adult' else lm_patch()).validate(patch)
                observation = {'history_id': action['history_id'], 'patch_hash': digest(patch), 'patch': patch}
            else:
                observation = self.adapter.auxiliary(action)
            self.ledger.append({'kind': 'auxiliary', 'actor': actor, 'request': action, 'observation': observation})

    def run(self):
        require(not self.used, 'scheduler is single-use')
        self.used = True
        status, reason = 'BLOCKED', None
        try:
            self.adapter.rollback()
            self.snapshots.append(self.adapter.snapshot(0))
            for actor in range(2):
                self._call(actor, 'canary', canary=True)
            for slot in range(1, self.limit + 1):
                self.slots = slot  # An invalid/failed proposal opportunity is never refunded.
                proposer = (self.first + slot - 1) % 2
                proposal = self._response(proposer, 'proposer')
                review = self._response(1-proposer, 'reviewer', proposal)
                patch = (proposal['patch'] if review['action'] == 'accept' else
                         review['patch'] if review['action'] == 'revise' else {'ops': []})
                self._history()
                result = self.adapter.evaluate(copy.deepcopy(patch))
                self.completed = slot
                self.ledger.append({'kind': 'round', 'slot': slot, 'proposer': proposer,
                    'proposal': proposal, 'proposal_hash': digest(proposal), 'review': review,
                    'review_hash': digest(review), 'submitted_patch': patch,
                    'result': result, 'incumbent': candidate(self.adapter.controller.best(), self.adapter.arm)})
                if slot in self.stages:
                    self.snapshots.append(self.adapter.snapshot(slot))
            self.adapter.controller.lock_best()
            status = 'COMPLETE'
        except BudgetExhausted:
            status, reason = 'BLOCKED', 'CONTEXT_OR_RESOURCE_BUDGET'
        except InvalidResponse:
            status, reason = 'INVALID', 'MALFORMED_OR_UNEXPECTED_NATIVE_RESPONSE'
        except BlockedRoute:
            status, reason = 'BLOCKED', 'TRANSPORT_OR_ROUTE'
        except ExperienceError:
            status, reason = 'BLOCKED', 'HISTORY_REVALIDATION'
        except Exception:
            status, reason = 'INVALID', 'SCHEMA_ROUTE_OR_CONTROLLER_FAILURE'
        finally:
            try:
                self.adapter.rollback()
                if self.adapter.controller.locked is None:
                    self.adapter.controller.lock_best()
            except Exception:
                status, reason = 'BLOCKED', 'ROLLBACK_FAILURE'
        record = {'version': 1, 'scope': 'SCHEDULER_SOFTWARE_ONLY', 'status': status, 'reason': reason,
            'context_policy': self.context_policy,
            'condition': self.condition, 'identity': self.identity, 'repeat_index': self.repeat_index,
            'feedback_mode': self.feedback_mode,
            'first_proposer': self.first, 'candidate_limit': self.limit, 'slots_used': self.slots,
            'completed_slots': self.completed, 'experience_sha256': self.packet_hash,
            'source_manifest_sha256': self.manifest_hash, 'actor_counts': self.counts,
            'actors': [actor_record(i, e, d)
                       for i, (e, d) in enumerate(zip(ACTORS[self.condition], self.drivers))],
            'calls': self.calls, 'ledger': self.ledger,
            'selection': candidate(self.adapter.controller.best(), self.adapter.arm),
            'stage_status': {str(s): 'LOCKED' if s in {v.slot for v in self.snapshots} else 'NOT_RUN'
                             for s in self.stages},
            'target_work': numbers(self.adapter.controller.record()['target_work'], WORK),
            'final_evaluation': 'NOT_RUN', 'full_extension': 'NOT_IMPLEMENTED'}
        return RunResult(canonical(record), tuple(self.snapshots))
