"""Capability-limited in-process controller: no path, test or clean inputs."""
from dataclasses import dataclass, field
import json
import copy
import time
import sys
import numpy as np
from jsonschema import Draft202012Validator, validators
from .model import probabilities
from .metrics import metrics
from .patches import InvalidPatch, integer, patch_schema
from .io import digest

StrictValidator = validators.extend(
    Draft202012Validator,
    type_checker=Draft202012Validator.TYPE_CHECKER.redefine(
        "integer", lambda checker, value: type(value) is int))


def action_schema():
    def variant(action, fields):
        props = {'action': {'const': action}, **fields}
        return {'type': 'object', 'additionalProperties': False, 'properties': props, 'required': list(props)}
    index = {'type': 'integer', 'minimum': 0, 'maximum': 255}
    tensor = {'const': 'fc2.weight'}
    return {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'oneOf': [
        variant('inspect_stats', {}),
        variant('inspect_slice', {'tensor': tensor, 'row': {'type': 'integer', 'minimum': 0, 'maximum': 15},
                                  'start': {'type': 'integer', 'minimum': 0, 'maximum': 31},
                                  'count': {'type': 'integer', 'minimum': 1, 'maximum': 32}}),
        variant('probe_summary', {'indices': {'type': 'array', 'items': index, 'minItems': 1, 'maxItems': 32, 'uniqueItems': True}}),
        variant('evaluate_candidate', {'patch': patch_schema()}),
        variant('submit_final', {'candidate': {'type': 'integer', 'minimum': 0, 'maximum': 10}})]}


@dataclass
class SharedBudget:
    turns: int = 0
    limit: int = 30
    events: list = field(default_factory=list)


class Controller:
    def __init__(self, space, diagnostic, feedback, shared=None, candidate_limit=5, baseline=None):
        if candidate_limit not in (5, 10):
            raise ValueError('candidate budget must be pilot or confirmation')
        self.space = space
        self.diagnostic = {k: np.array(diagnostic[k], copy=True) for k in ['x', 'y', 'ids']}
        self._feedback = {k: np.array(feedback[k], copy=True) for k in ['x', 'y', 'ids']}
        if len(self.diagnostic['y']) > 256 or len(set(self.diagnostic['ids']) & set(self._feedback['ids'])):
            raise ValueError('panels overlap or diagnostic oversized')
        self.shared = shared if shared is not None else SharedBudget()
        self.limit, self.evaluations, self.probes = candidate_limit, 0, 0
        self.events, self.locked = [], None
        self.turns = 0
        self._view = None
        self._probe_probabilities = None
        self.candidates = []
        self.target_work = {'feedback_examples': 0, 'probe_examples': 0, 'diagnostic_examples': 0,
                            'target_calls': 0, 'elapsed_seconds': 0.0, 'forwards': 0,
                            'attempted_target_calls': 0, 'attempted_examples': 0}
        self._target_failed = False
        if baseline is None:
            self._add_candidate({'ops': []}, 0)
        else:
            self.candidates.append(copy.deepcopy(baseline))

    def _score_call(self, function, x, scope):
        n = len(x)
        self.target_work['attempted_target_calls'] += 1
        self.target_work['attempted_examples'] += n
        started = time.perf_counter()
        try:
            result = function()
        except BaseException as exc:
            self._target_failed = True
            self.target_work['forwards'] = None
            exc.adult_controller_record = self.record()
            raise
        else:
            self.target_work['target_calls'] += 1
            self.target_work[scope + '_examples'] += n
            if self.target_work['forwards'] is not None:
                self.target_work['forwards'] += 1
            return result
        finally:
            self.target_work['elapsed_seconds'] += time.perf_counter() - started
            if sys.exception() is not None:
                sys.exception().adult_controller_record = self.record()

    def _add_candidate(self, patch, index):
        state, stats = self.space.apply(patch)
        p = self._score_call(lambda: probabilities(state, self._feedback['x']),
                             self._feedback['x'], 'feedback')
        try:
            score = metrics(self._feedback['y'], p)
        except Exception as exc:
            self._target_failed = True
            exc.adult_controller_record = self.record()
            raise
        item = {'index': index, 'patch': patch, 'stats': stats, 'metrics': score,
                'patch_digest': digest(patch)}
        self.candidates.append(item)
        return {'candidate': index, 'metrics': score, 'stats': stats}

    def best(self):
        return min(self.candidates, key=lambda x: (-x['metrics']['balanced_accuracy'], x['stats']['norm'], x['stats']['count'], x['index']))

    def lock_best(self):
        self.locked = self.best()
        return {'status': 'LOCKED', 'candidate': self.locked['index'],
                'patch_digest': self.locked['patch_digest']}

    def initial_view(self):
        if self._view is not None:
            return copy.deepcopy(self._view)
        state = self.space.origin()
        import torch
        from .model import AdultMLP
        model = AdultMLP(self.diagnostic['x'].shape[1])
        model.load_state_dict(state)
        def activation():
            with torch.inference_mode():
                return torch.relu(model.fc1(torch.from_numpy(self.diagnostic['x']).float()))
        hidden = self._score_call(activation, self.diagnostic['x'], 'diagnostic')
        p = self._score_call(lambda: probabilities(state, self.diagnostic['x']),
                             self.diagnostic['x'], 'diagnostic')
        self._probe_probabilities = p
        self._view = {'stats': self.space.stats(), 'diagnostic': {'source_ids': self.diagnostic['ids'].tolist(),
                'features': self.diagnostic['x'].tolist(), 'labels': self.diagnostic['y'].tolist(),
                'damaged_probabilities': p.tolist(),
                'activation_mean': hidden.mean(0).tolist(), 'activation_std': hidden.std(0, unbiased=False).tolist()},
                'candidate_limit': self.limit, 'turn_limit_shared': self.shared.limit,
                'selection': 'balanced_accuracy desc, norm asc, count asc, index asc'}
        return copy.deepcopy(self._view)

    def handle(self, action):
        self.shared.turns += 1
        self.turns += 1
        event = {'turn': self.shared.turns, 'status': 'INVALID'}
        attempted_evaluation = type(action) is dict and action.get('action') == 'evaluate_candidate'
        if attempted_evaluation:
            self.evaluations += 1
        if type(action) is dict and action.get('action') == 'probe_summary':
            self.probes += 1
        try:
            if self.shared.turns > self.shared.limit:
                raise ValueError('combined turn budget exhausted')
            if self.locked is not None:
                raise ValueError('editor already locked')
            request_bytes = json.dumps(action, allow_nan=False).encode()
            if len(request_bytes) > 65536:
                raise ValueError('action payload too large')
            event['request_digest'] = digest(action)
            # bool is not an integer in the protocol, despite Python subclassing.
            def no_bool_indices(value, key=''):
                if type(value) is dict:
                    for k, v in value.items():
                        no_bool_indices(v, k)
                elif type(value) is list:
                    for v in value:
                        no_bool_indices(v, key)
                elif type(value) is bool:
                    raise ValueError('boolean not allowed')
            no_bool_indices(action)
            StrictValidator(action_schema()).validate(action)
            kind = action['action']
            event['action'] = kind
            if kind == 'inspect_stats':
                result = self.space.stats()
            elif kind == 'inspect_slice':
                start, count = action['start'], action['count']
                if start + count > 32:
                    raise ValueError('slice outside tensor')
                result = {'values': self.space.origin()['fc2.weight'][action['row'], start:start+count].tolist()}
            elif kind == 'probe_summary':
                if self.probes > 10:
                    raise ValueError('probe budget exhausted')
                ix = [integer(i, len(self.diagnostic['y'])) for i in action['indices']]
                if self._probe_probabilities is None:
                    self.initial_view()
                p = self._probe_probabilities[ix]
                result = {'n': len(ix), 'mean_probability': float(p.mean()), 'metrics': metrics(self.diagnostic['y'][ix], p)}
            elif kind == 'evaluate_candidate':
                if self.evaluations > self.limit:
                    raise ValueError('candidate budget exhausted')
                result = self._add_candidate(action['patch'], self.evaluations)
            else:
                selected = self.best()
                if action['candidate'] != selected['index']:
                    raise ValueError('must submit best eligible candidate including baseline')
                self.locked = selected
                result = {'status': 'LOCKED', 'candidate': selected['index'], 'patch_digest': selected['patch_digest']}
            event['status'] = 'OK'
            event['request_digest'] = digest(action)
            return result
        except Exception as exc:
            if self._target_failed:
                event.update(status='BLOCKED', error_type=type(exc).__name__)
                exc.adult_controller_record = self.record()
                raise
            # Never echo arbitrary input or raw exception text into the editor channel.
            event['reason'] = type(exc).__name__
            return {'status': 'INVALID', 'reason': event['reason'], 'evaluations_used': self.evaluations}
        finally:
            self.events.append(event)
            self.shared.events.append(dict(event))

    def record(self):
        return {'evaluations': self.evaluations, 'candidate_limit': self.limit, 'probe_queries': self.probes,
                'combined_turns': self.shared.turns, 'editor_turns': self.turns, 'events': self.events, 'candidates': self.candidates,
                'locked': self.locked, 'target_work': dict(self.target_work)}
